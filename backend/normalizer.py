from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect

MARKETS = ("wb", "ozon", "amazon", "lazada")

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


def _relevance(text: str, dataset_key: str) -> float:
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


def _classify(text: str, dataset_key: str) -> tuple[str, dict[str, Any]]:
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
            relevance = _relevance(text, dataset_key)
            if relevance < 0.5:
                rejected += 1
                continue
            archetype_key, features = _classify(text, dataset_key)
            label = ARCHETYPE_LABELS[dataset_key][archetype_key]
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
        for market in MARKETS:
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
            label = ARCHETYPE_LABELS[dataset_key][key]
            markets = sorted({item["market"] for item in items})
            feature_counts = Counter()
            for item in items:
                for feature, value in (item["features"] or {}).items():
                    if value:
                        feature_counts[feature] += 1
            features = {
                feature: round(count / len(items), 3)
                for feature, count in feature_counts.items()
            }
            archetype = conn.execute(
                """
                INSERT INTO product_archetypes(
                    run_id,dataset_key,archetype_key,label,member_count,market_count,features
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (run_id,dataset_key,key,label,len(items),len(markets),Jsonb(features)),
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
            for market in MARKETS:
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
            foreign = round(
                (signals["amazon"]["presence_score"] + signals["lazada"]["presence_score"]) / 2,
                2,
            )
            russia = round(
                (signals["wb"]["presence_score"] + signals["ozon"]["presence_score"]) / 2,
                2,
            )
            market_count = sum(1 for market in MARKETS if signals[market]["offer_count"] > 0)
            cross = round(100 * market_count / len(MARKETS), 2)
            gap = round(max(0.0, min(100.0, 50 + foreign - russia)), 2)
            review_score = round(
                100 * math.log1p(review_totals[key]) / max_review_log
                if review_totals[key] > 0 else 0,
                2,
            )
            recurrence = round(100 * len(items) / max_member_count, 2)
            score = round(
                0.30 * foreign
                + 0.25 * gap
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
                        "formula_version": "signals_v1",
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

    return {"archetypes": len(grouped), "normalized": len(rows)}
def get_live_opportunities(run_id: str, limit: int = 5) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT pa.id,pa.archetype_key,pa.label,pa.member_count,pa.market_count,
                   pa.features,os.foreign_signal,os.russia_signal,
                   os.cross_market_presence,os.russia_gap,os.review_mass_score,
                   os.feature_recurrence,os.opportunity_score
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s
            ORDER BY os.opportunity_score DESC,pa.member_count DESC
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
                       rp.rating,rp.review_count
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
                "score_version": "signals_v1",
            })
    return result