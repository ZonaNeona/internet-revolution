from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.generic_cluster import build_observed_clusters

from backend.marketplaces import ACTIVE, run_config
MARKETS = tuple(ACTIVE)

ARCHETYPE_LABELS = {
    "vacuum": {
        "bendable_led": "Складная труба + LED-подсветка",
        "pet_hair": "Пылесос для шерсти животных",
        "wet_dry": "Wet & Dry / самоочистка",
        "auto_empty": "Док-станция с автоочисткой",
        "self_standing": "Self-standing / съёмный аккумулятор",
        "basic_cordless": "Базовый беспроводной вертикальный",
        "generic_vacuum": "Другой вертикальный пылесос",
    },
    "bath": {
        "stone_diatomite": "Каменный / диатомитовый коврик",
        "quick_dry": "Многослойный быстросохнущий коврик",
        "drainage": "Ребристый / дренажный коврик",
        "memory_foam": "Memory Foam коврик",
        "eva_modular": "Модульный EVA-коврик",
        "generic_bath": "Другой коврик для ванной",
    },
    "led": {
        "matter": "RGBIC + Matter / Thread",
        "tv_camera": "TV backlight с камерой",
        "desktop": "Desktop / monitor ambient kit",
        "neon": "Neon rope RGBIC",
        "outdoor": "Outdoor smart strip",
        "generic_rgbic": "Базовая RGBIC-лента",
        "generic_led": "Другая LED-лента",
    },
}
def _text(row: dict[str, Any]) -> str:
    parts = [
        row.get("title") or "",
        row.get("brand") or "",
        row.get("feature_summary") or "",
    ]
    return " ".join(str(part) for part in parts).casefold()


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in patterns)


def _ontology_for_run(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            "SELECT ontology FROM research_runs WHERE id=%s",
            (run_id,),
        ).fetchone()
    return dict((row or {}).get("ontology") or {})


def _query_for_run(run_id: str) -> str:
    with connect() as conn:
        row = conn.execute(
            "SELECT query FROM research_runs WHERE id=%s",
            (run_id,),
        ).fetchone()
    return str((row or {}).get("query") or "")


def _term_hit(text: str, term: str) -> bool:
    value = str(term or "").casefold().strip()
    return bool(value and value in text)


def _generic_relevance(text: str, ontology: dict[str, Any]) -> float:
    negatives = ontology.get("negative_keywords") or []
    if any(_term_hit(text, term) for term in negatives):
        return 0.20

    positives = list(ontology.get("positive_keywords") or [])
    positives.extend([
        ontology.get("category_label_ru") or "",
        ontology.get("category_label_en") or "",
        ontology.get("product_family") or "",
    ])
    hits = sum(1 for term in positives if _term_hit(text, term))
    if hits >= 2:
        return 1.0
    if hits == 1:
        return 0.85

    # Domain-scoped search already provides a useful prior. Keep uncertain
    # products for clustering, but with lower membership confidence.
    return 0.0


def _relevance(
    text: str,
    dataset_key: str,
    ontology: dict[str, Any] | None = None,
) -> float:
    if dataset_key == "generic":
        return _generic_relevance(text, ontology or {})
    if dataset_key == "vacuum":
        positive = _has(text, r"пылесос", r"vacuum", r"cordless", r"stick")
        negative = _has(text, r"vacuum bag", r"мешок для", r"filter only")
    elif dataset_key == "bath":
        positive = _has(text, r"коврик", r"bath mat", r"diatom", r"memory foam", r"eva")
        negative = _has(text, r"table mat", r"car mat", r"mouse pad")
    else:
        positive = _has(text, r"светодиод", r"led strip", r"lightstrip", r"rgbic", r"backlight", r"neon")
        negative = _has(text, r"датчик", r"sensor", r"bi.?led", r"линз", r"headlight")
    if not positive:
        return 0.0
    if negative:
        return 0.25
    return 1.0


def _generic_classify(
    text: str,
    ontology: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    features: dict[str, Any] = {}
    for feature in ontology.get("features") or []:
        key = str(feature.get("key") or "").strip()
        if not key:
            continue
        aliases = feature.get("aliases") or []
        features[key] = any(_term_hit(text, alias) for alias in aliases)

    best_key = "generic_dynamic"
    best_score = 0
    for archetype in ontology.get("archetypes") or []:
        excludes = archetype.get("exclude_keywords") or []
        if any(_term_hit(text, term) for term in excludes):
            continue
        keywords = archetype.get("keywords") or []
        score = sum(
            1 + (1 if " " in str(term).strip() else 0)
            for term in keywords
            if _term_hit(text, term)
        )
        if score > best_score:
            best_score = score
            best_key = str(archetype.get("key") or "generic_dynamic").strip() or "generic_dynamic"

    return best_key, features


def _archetype_label(
    dataset_key: str,
    archetype_key: str,
    ontology: dict[str, Any] | None = None,
) -> str:
    if dataset_key != "generic":
        return ARCHETYPE_LABELS[dataset_key][archetype_key]

    for archetype in [*((ontology or {}).get("observed_clusters") or {}).get("archetypes", []), *((ontology or {}).get("archetypes") or [])]:
        if str(archetype.get("key") or "") == archetype_key:
            return str(archetype.get("label") or archetype_key)
    category = str((ontology or {}).get("category_label_ru") or "товар")
    return "Другой вариант: " + category


def _classify(
    text: str,
    dataset_key: str,
    ontology: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    if dataset_key == "generic":
        return _generic_classify(text, ontology or {})

    features: dict[str, Any] = {}
    if dataset_key == "vacuum":
        features = {
            "foldable": _has(text, r"bendable", r"foldable", r"flexible", r"складн", r"гибк"),
            "led": _has(text, r"led", r"green light", r"подсвет"),
            "pet": _has(text, r"pet", r"anti.?tangle", r"hair", r"шерст", r"волос"),
            "wet_dry": _has(text, r"wet.?dry", r"моющ", r"влажн", r"dual tank", r"self.?clean"),
            "auto_empty": _has(text, r"auto.?empty", r"self.?empty", r"dust station", r"док.?станц"),
            "self_standing": _has(text, r"self.?standing", r"removable battery", r"съ[её]мн.*аккумулятор"),
            "cordless": _has(text, r"cordless", r"беспровод"),
        }
        if features["auto_empty"]:
            key = "auto_empty"
        elif features["wet_dry"]:
            key = "wet_dry"
        elif features["foldable"] and features["led"]:
            key = "bendable_led"
        elif features["pet"]:
            key = "pet_hair"
        elif features["self_standing"]:
            key = "self_standing"
        elif features["cordless"]:
            key = "basic_cordless"
        else:
            key = "generic_vacuum"
        return key, features
    if dataset_key == "bath":
        features = {
            "stone": _has(text, r"diatom", r"stone", r"камен", r"диатом"),
            "quick_dry": _has(text, r"quick.?dry", r"fast.?dry", r"быстросох"),
            "drainage": _has(text, r"drain", r"ribbed", r"ребрист", r"дренаж"),
            "memory_foam": _has(text, r"memory foam", r"мемори", r"памят"),
            "eva": _has(text, r"eva", r"модульн", r"interlocking"),
        }
        if features["stone"]:
            key = "stone_diatomite"
        elif features["memory_foam"]:
            key = "memory_foam"
        elif features["eva"]:
            key = "eva_modular"
        elif features["drainage"]:
            key = "drainage"
        elif features["quick_dry"]:
            key = "quick_dry"
        else:
            key = "generic_bath"
        return key, features

    features = {
        "matter": _has(text, r"matter", r"thread"),
        "rgbic": _has(text, r"rgbic", r"rgb[+]ic"),
        "camera": _has(text, r"camera", r"камера", r"screen sync", r"color pickup"),
        "tv": _has(text, r"tv", r"телевиз"),
        "desktop": _has(text, r"monitor", r"desktop", r"монитор", r"настоль"),
        "neon": _has(text, r"neon", r"неон"),
        "outdoor": _has(text, r"outdoor", r"ip67", r"улич"),
    }
    if features["matter"]:
        key = "matter"
    elif features["camera"] and features["tv"]:
        key = "tv_camera"
    elif features["desktop"]:
        key = "desktop"
    elif features["neon"]:
        key = "neon"
    elif features["outdoor"]:
        key = "outdoor"
    elif features["rgbic"]:
        key = "generic_rgbic"
    else:
        key = "generic_led"
    return key, features
def normalize_run(run_id: str, dataset_key: str) -> dict[str, int]:
    ontology = _ontology_for_run(run_id) if dataset_key == "generic" else {}
    assignments = None
    if dataset_key == 'generic':
        try:
            observed, _ = build_observed_clusters(run_id, _query_for_run(run_id), ontology)
            from backend.generic_cluster import validate_explicit_specs, _load_products
            mode=run_config(run_id)['analysis_mode']
            observed=validate_explicit_specs(observed,_load_products(run_id),mode,_query_for_run(run_id))
            ontology['observed_clusters'] = observed
            assignments = {a['raw_product_id']:a for a in observed['assignments']}
        except Exception as exc:
            from backend.budget import warning
            warning(run_id, 'Группировка недоступна: использована консервативная проверка признаков ('+type(exc).__name__+')')
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id,market,title,brand,feature_summary
            FROM raw_products
            WHERE run_id=%s
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
        conn.execute("DELETE FROM normalized_products WHERE run_id=%s", (run_id,))

        relevant = 0
        rejected = 0
        for row in rows:
            text = _text(row)
            assignment = assignments.get(int(row['id'])) if assignments is not None else None
            relevance = (float(assignment['confidence']) if assignment and assignment['relevant'] else 0) if assignments is not None else _relevance(text, dataset_key, ontology)
            if relevance < 0.65:
                rejected += 1
                continue
            archetype_key, features = _classify(text, dataset_key, ontology)
            if assignment:
                archetype_key = assignment['archetype_key']
                features['_match_reason'] = assignment.get('reason','')
                features['_classification_method']='observed'
            elif dataset_key == 'generic' and run_config(run_id)['analysis_mode']=='product':
                # Rules fallback cannot verify exact product identity.
                archetype_key = 'unverified_alternative'
            if dataset_key=='generic' and assignments is None:
                features['_classification_method']='conservative_rules'
            label = _archetype_label(dataset_key, archetype_key, ontology)
            canonical_title = " ".join((row["title"] or "").split())
            canonical_brand = (row["brand"] or "").strip() or None
            conn.execute(
                """
                INSERT INTO normalized_products(
                    run_id,raw_product_id,market,canonical_title,canonical_brand,
                    archetype_key,archetype_label,relevance_score,features
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (run_id,raw_product_id) DO UPDATE SET
                    canonical_title=EXCLUDED.canonical_title,
                    canonical_brand=EXCLUDED.canonical_brand,
                    archetype_key=EXCLUDED.archetype_key,
                    archetype_label=EXCLUDED.archetype_label,
                    relevance_score=EXCLUDED.relevance_score,
                    features=EXCLUDED.features
                """,
                (
                    run_id, row["id"], row["market"], canonical_title,
                    canonical_brand, archetype_key, label, relevance, Jsonb(features),
                ),
            )
            relevant += 1
    return {"raw": len(rows), "relevant": relevant, "rejected": rejected}
def build_archetypes(run_id: str, dataset_key: str) -> dict[str, int]:
    config = run_config(run_id)
    markets = config['selected_markets']
    covered = [m for m in markets if (config.get('scouts') or {}).get(m,{}).get('status')=='done']
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT np.*,rp.rating,rp.review_count,rp.source_url
            FROM normalized_products np
            JOIN raw_products rp ON rp.id=np.raw_product_id
            WHERE np.run_id=%s
            ORDER BY np.id
            """,
            (run_id,),
        ).fetchall()

        conn.execute("DELETE FROM product_archetypes WHERE run_id=%s", (run_id,))

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        market_totals = Counter()
        for row in rows:
            grouped[row["archetype_key"]].append(row)
            market_totals[row["market"]] += 1

        max_member_count = max((len(items) for items in grouped.values()), default=1)
        market_max: dict[str, int] = {}
        for market in markets:
            market_max[market] = max(
                (
                    sum(1 for item in items if item["market"] == market)
                    for items in grouped.values()
                ),
                default=1,
            )

        archetype_ids: dict[str, int] = {}
        signal_cache: dict[str, dict[str, dict[str, float]]] = {}
        review_totals: dict[str, int] = {}
        for key, items in grouped.items():
            label = str(items[0].get("archetype_label") or key)
            group_markets = sorted({item["market"] for item in items})
            feature_counts = Counter()
            for item in items:
                for feature, value in (item["features"] or {}).items():
                    if value is True:
                        feature_counts[feature] += 1
            features = {
                feature: round(count / len(items), 3)
                for feature, count in feature_counts.items()
            }
            if config['analysis_mode']=='product' and key!='target_product':
                observed=(config.get('ontology') or {}).get('observed_clusters') or {}
                descriptor=next((a.get('description') for a in observed.get('archetypes',[]) if a.get('key')==key),'')
                features['_differences']=descriptor or 'Сопоставьте обязательные характеристики с исходным запросом'
            archetype = conn.execute(
                """
                INSERT INTO product_archetypes(
                    run_id,dataset_key,archetype_key,label,member_count,market_count,features
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (run_id,dataset_key,key,label,len(items),len(group_markets),Jsonb(features)),
            ).fetchone()
            archetype_id = int(archetype["id"])
            archetype_ids[key] = archetype_id

            for item in items:
                conn.execute(
                    """
                    INSERT INTO archetype_members(
                        archetype_id,normalized_product_id,membership_score
                    ) VALUES (%s,%s,%s)
                    """,
                    (archetype_id,item["id"],item["relevance_score"]),
                )

            signal_cache[key] = {}
            total_reviews = 0
            for market in markets:
                market_items = [item for item in items if item["market"] == market]
                count = len(market_items)
                review_mass = sum(int(item["review_count"] or 0) for item in market_items)
                ratings = [float(item["rating"]) for item in market_items if item["rating"] is not None]
                avg_rating = sum(ratings) / len(ratings) if ratings else None
                presence = round(100 * count / max(market_max[market], 1), 2)
                total_reviews += review_mass
                conn.execute(
                    """
                    INSERT INTO market_signals(
                        run_id,archetype_id,market,offer_count,presence_score,
                        review_mass,avg_rating,details
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        run_id,archetype_id,market,count,presence,
                        review_mass,avg_rating,
                        Jsonb({"market_sample": market_totals[market]}),
                    ),
                )
                signal_cache[key][market] = {
                    "offer_count": count,
                    "presence_score": presence,
                    "review_mass": review_mass,
                }
            review_totals[key] = total_reviews
        max_review = max(review_totals.values(), default=0)
        max_review_log = math.log1p(max_review) if max_review else 1.0

        for key, items in grouped.items():
            signals = signal_cache[key]
            rule_fallback=any((item.get('features') or {}).get('_classification_method')=='conservative_rules' for item in items)
            classification_confidence=sum(float(item['relevance_score']) for item in items)/len(items)
            foreign_markets = [m for m in covered if ACTIVE[m]['country']!='RU']
            ru_markets = [m for m in covered if ACTIVE[m]['country']=='RU']
            foreign = round(sum(signals[m]['presence_score'] for m in foreign_markets)/len(foreign_markets),2) if foreign_markets else 0
            russia = round(sum(signals[m]['presence_score'] for m in ru_markets)/len(ru_markets),2) if ru_markets else 0
            market_count = sum(1 for m in covered if signals[m]['offer_count']>0)
            cross = round(100*market_count/max(len(covered),1),2)
            gap_available = bool(foreign_markets and ru_markets)
            gap = round(max(0,min(100,50+foreign-russia)),2) if gap_available else 0
            review_score = round(
                100 * math.log1p(review_totals[key]) / max_review_log
                if review_totals[key] > 0 else 0,
                2,
            )
            recurrence = round(100 * len(items) / max_member_count, 2)
            score = round(
                0.30 * (foreign if foreign_markets else russia)
                + 0.25 * (gap if gap_available else cross)
                + 0.20 * cross
                + 0.15 * review_score
                + 0.10 * recurrence,
                2,
            )
            conn.execute(
                """
                INSERT INTO opportunity_scores(
                    run_id,archetype_id,foreign_signal,russia_signal,
                    cross_market_presence,russia_gap,review_mass_score,
                    feature_recurrence,opportunity_score,explanation
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    run_id,archetype_ids[key],foreign,russia,cross,gap,
                    review_score,recurrence,score,
                    Jsonb({
                        "formula_version": "signals_v2",
                        "gap_available": gap_available, "covered_markets": covered,
                        "coverage": round(len(covered)/max(len(markets),1),2),
                        "confidence": round(len(covered)/max(len(markets),1)*classification_confidence*(0.5 if rule_fallback else 1),2),
                        "classification": 'conservative_rules' if rule_fallback else 'confirmed',
                        "weights": {
                            "foreign_signal": 0.30,
                            "russia_gap": 0.25,
                            "cross_market_presence": 0.20,
                            "review_mass": 0.15,
                            "feature_recurrence": 0.10,
                        },
                    }),
                ),
            )

    if config['analysis_mode']=='product':
        with connect() as conn:
            target=conn.execute("INSERT INTO product_archetypes(run_id,dataset_key,archetype_key,label) VALUES (%s,%s,'target_product',%s) ON CONFLICT (run_id,archetype_key) DO UPDATE SET label=EXCLUDED.label RETURNING id",(run_id,dataset_key,config['query'])).fetchone()
            conn.execute("INSERT INTO opportunity_scores(run_id,archetype_id,decision,explanation) VALUES (%s,%s,'NEEDS_DATA',%s) ON CONFLICT (run_id,archetype_id) DO NOTHING",(run_id,target['id'],Jsonb({'formula_version':'signals_v2','gap_available':False,'confidence':0})))
    return {"archetypes": len(grouped), "normalized": len(rows)}
def get_live_opportunities(run_id: str, limit: int = 5) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT pa.id,pa.archetype_key,pa.label,pa.member_count,pa.market_count,
                   pa.features,os.foreign_signal,os.russia_signal,
                   os.cross_market_presence,os.russia_gap,os.review_mass_score,
                   os.feature_recurrence,os.opportunity_score,
                   os.market_score,os.supplier_availability_score,
                   os.economics_score,os.final_score,os.decision,
                   os.final_explanation,os.explanation
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s
            ORDER BY (pa.archetype_key='target_product') DESC, COALESCE(os.final_score,os.opportunity_score) DESC,
                     os.opportunity_score DESC,
                     pa.member_count DESC
            LIMIT %s
            """,
            (run_id, limit),
        ).fetchall()

        result = []
        for row in rows:
            signals = conn.execute(
                """
                SELECT market,offer_count,presence_score,review_mass,avg_rating
                FROM market_signals
                WHERE run_id=%s AND archetype_id=%s
                ORDER BY market
                """,
                (run_id,row["id"]),
            ).fetchall()
            evidence = conn.execute(
                """
                SELECT np.market,np.canonical_title,rp.source_url,rp.price_text,
                       rp.rating,rp.review_count,rp.created_at,rp.raw_data,np.features->>'_match_reason' AS match_reason
                FROM archetype_members am
                JOIN normalized_products np ON np.id=am.normalized_product_id
                JOIN raw_products rp ON rp.id=np.raw_product_id
                WHERE am.archetype_id=%s
                ORDER BY np.market,np.id
                LIMIT 12
                """,
                (row["id"],),
            ).fetchall()
            result.append({
                **dict(row),
                "market_signals": {item["market"]: dict(item) for item in signals},
                "evidence": [dict(item) for item in evidence],
                "live_derived": True,
                "score_version": (row.get("explanation") or {}).get("formula_version","signals_v1"),
            })
    return result
