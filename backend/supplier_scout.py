from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.openrouter_client import OpenRouterError, supplier_search
from backend import budget

SOURCES = {
    "alibaba": {
        "label": "Alibaba",
        "engine": "exa",
        "domains": ["alibaba.com"],
    },
    "made_in_china": {
        "label": "Made-in-China",
        "engine": "exa",
        "domains": ["made-in-china.com"],
    },
}

FALLBACK_QUERIES = {
    "vacuum": "cordless stick vacuum OEM manufacturer private label price MOQ",
    "bath": "bath mat OEM manufacturer private label price MOQ",
    "led": "RGBIC LED strip OEM manufacturer private label price MOQ",
}

ARCHETYPE_QUERIES = {
    "vacuum": {
        "bendable_led": "cordless stick vacuum bendable tube LED OEM manufacturer private label price MOQ",
        "pet_hair": "cordless stick vacuum pet hair anti tangle OEM manufacturer private label price MOQ",
        "wet_dry": "wet dry stick vacuum self cleaning dual tank OEM manufacturer private label price MOQ",
        "auto_empty": "cordless stick vacuum auto empty dock OEM manufacturer private label price MOQ",
        "self_standing": "self standing cordless stick vacuum removable battery OEM manufacturer price MOQ",
        "basic_cordless": "cordless stick vacuum OEM manufacturer private label price MOQ",
        "generic_vacuum": "upright stick vacuum OEM manufacturer private label price MOQ",
    },
    "bath": {
        "stone_diatomite": "diatomite stone bath mat quick dry OEM manufacturer private label price MOQ",
        "quick_dry": "quick dry absorbent bath mat OEM manufacturer private label price MOQ",
        "drainage": "drainage ribbed bath mat OEM manufacturer private label price MOQ",
        "memory_foam": "memory foam bath mat OEM manufacturer private label price MOQ",
        "eva_modular": "EVA modular bath mat OEM manufacturer private label price MOQ",
        "generic_bath": "bath mat OEM manufacturer private label price MOQ",
    },
    "led": {
        "matter": "RGBIC LED strip Matter Thread OEM manufacturer private label price MOQ",
        "tv_camera": "TV backlight RGBIC camera sync OEM manufacturer private label price MOQ",
        "desktop": "monitor ambient RGBIC LED kit OEM manufacturer private label price MOQ",
        "neon": "RGBIC neon rope OEM manufacturer private label price MOQ",
        "outdoor": "outdoor RGBIC LED strip IP67 OEM manufacturer private label price MOQ",
        "generic_rgbic": "RGBIC LED strip OEM manufacturer private label price MOQ",
        "generic_led": "smart LED strip OEM manufacturer private label price MOQ",
    },
}
def _enabled() -> bool:
    return os.environ.get("PRODUCT_HUNTER_LIVE_SCOUT", "0").strip() == "1"


def _model() -> str:
    return os.environ.get(
        "PRODUCT_HUNTER_SCOUT_MODEL",
        "qwen/qwen3-30b-a3b-instruct-2507",
    ).strip()


def _run_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_SUPPLIER_BUDGET_USD", "0.10"))


def _daily_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_DAILY_LIVE_BUDGET_USD", "3.00"))


def _top_archetypes(run_id: str, limit: int = 5) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT pa.id,pa.archetype_key,pa.label,os.opportunity_score
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s AND pa.member_count>0
            ORDER BY (pa.archetype_key='target_product') DESC,os.opportunity_score DESC,pa.member_count DESC
            LIMIT %s
            """,
            (run_id, limit),
        ).fetchall()


def _query_for(
    run_id: str,
    dataset_key: str,
    archetype_key: str,
    archetype_label: str,
) -> str:
    if dataset_key != "generic":
        return (
            ARCHETYPE_QUERIES.get(dataset_key, {}).get(archetype_key)
            or FALLBACK_QUERIES[dataset_key]
        )

    with connect() as conn:
        row = conn.execute(
            "SELECT ontology FROM research_runs WHERE id=%s",
            (run_id,),
        ).fetchone()
    ontology = dict((row or {}).get("ontology") or {})
    for archetype in [*(ontology.get("observed_clusters") or {}).get("archetypes",[]), *(ontology.get("archetypes") or [])]:
        if str(archetype.get("key") or "") == archetype_key:
            query = str(archetype.get("supplier_query") or "").strip()
            if query:
                return query

    category = str(ontology.get("category_label_en") or "").strip()
    base = archetype_label or category or archetype_key
    return (
        str(base)
        + " OEM manufacturer private label wholesale price MOQ"
    )


def _spent_run(run_id: str) -> Decimal:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM supplier_search_calls
            WHERE run_id=%s
            """,
            (run_id,),
        ).fetchone()
    return Decimal(str(row["cost"] or 0))


def _spent_today_total() -> Decimal:
    with connect() as conn:
        market = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE created_at >= date_trunc('day',now())
            """
        ).fetchone()
        supplier = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM supplier_search_calls
            WHERE created_at >= date_trunc('day',now())
            """
        ).fetchone()
    return Decimal(str(market["cost"] or 0)) + Decimal(str(supplier["cost"] or 0))
def _existing_done(
    run_id: str,
    archetype_id: int,
    source: str,
    query: str,
) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM supplier_search_calls
            WHERE run_id=%s AND archetype_id=%s
              AND source=%s AND query=%s AND status='done'
            LIMIT 1
            """,
            (run_id, archetype_id, source, query),
        ).fetchone()
    return bool(row)


def _create_call(
    run_id: str,
    archetype_id: int,
    source: str,
    query: str,
    engine: str,
) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO supplier_search_calls(
                run_id,archetype_id,source,query,engine,model,status
            ) VALUES (%s,%s,%s,%s,%s,%s,'running')
            RETURNING id
            """,
            (run_id, archetype_id, source, query, engine, _model()),
        ).fetchone()
    return int(row["id"])


def _mark_budget_blocked(
    run_id: str,
    archetype_id: int,
    source: str,
    query: str,
    engine: str,
    reason: str,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO supplier_search_calls(
                run_id,archetype_id,source,query,engine,model,
                status,error,completed_at
            ) VALUES (%s,%s,%s,%s,%s,%s,'budget_blocked',%s,now())
            """,
            (
                run_id, archetype_id, source, query, engine,
                _model(), reason,
            ),
        )


def _refresh_counters(run_id: str) -> None:
    with connect() as conn:
        market = conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) AS cost FROM search_calls WHERE run_id=%s",
            (run_id,),
        ).fetchone()
        supplier = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost,
                   COUNT(*) FILTER (WHERE status='done') AS calls
            FROM supplier_search_calls
            WHERE run_id=%s
            """,
            (run_id,),
        ).fetchone()
        offers = conn.execute(
            "SELECT COUNT(*) AS count FROM supplier_offers WHERE run_id=%s",
            (run_id,),
        ).fetchone()

        market_cost = Decimal(str(market["cost"] or 0))
        supplier_cost = Decimal(str(supplier["cost"] or 0))
        conn.execute(
            """
            UPDATE research_runs
            SET supplier_actual_cost_usd=%s,
                supplier_search_calls=%s,
                supplier_records=%s,
                actual_cost_usd=%s,
                estimated_cost_usd=%s,
                updated_at=now()
            WHERE id=%s
            """,
            (
                supplier_cost,
                int(supplier["calls"] or 0),
                int(offers["count"] or 0),
                market_cost + supplier_cost,
                market_cost + supplier_cost,
                run_id,
            ),
        )
def _normalize_offer(item: dict[str, Any]) -> dict[str, Any]:
    features = (
        item.get("feature_summary")
        or item.get("features")
        or item.get("description")
        or ""
    )
    if isinstance(features, list):
        features = "; ".join(str(x) for x in features if x is not None)

    customization = (
        item.get("customization")
        or item.get("customization_text")
        or item.get("customization_options")
    )
    if isinstance(customization, list):
        customization = "; ".join(str(x) for x in customization if x is not None)

    return {
        "supplier_name": (
            item.get("supplier_name")
            or item.get("manufacturer")
            or item.get("brand")
        ),
        "product_title": str(
            item.get("product_title")
            or item.get("title")
            or item.get("name")
            or "Supplier offer"
        ).strip(),
        "source_url": str(item.get("url") or "").strip(),
        "price_text": item.get("price_text", item.get("price")),
        "moq_text": item.get("moq_text", item.get("moq")),
        "lead_time_text": item.get("lead_time_text", item.get("lead_time")),
        "customization_text": customization,
        "feature_summary": str(features or "").strip(),
        "country": item.get("country") or item.get("place_of_origin"),
        "raw": item,
    }


def _persist_success(
    *,
    run_id: str,
    archetype_id: int,
    call_id: int,
    source: str,
    result,
) -> int:
    usage = result.usage or {}
    normalized = [
        _normalize_offer(item)
        for item in result.offers
        if isinstance(item, dict)
    ]
    normalized = [
        item for item in normalized
        if item["product_title"] and item["source_url"]
    ]

    with connect() as conn:
        conn.execute(
            """
            UPDATE supplier_search_calls
            SET status='done',cost_usd=%s,prompt_tokens=%s,
                completion_tokens=%s,total_tokens=%s,result_count=%s,
                response_meta=%s,completed_at=now()
            WHERE id=%s
            """,
            (
                result.cost_usd,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
                len(normalized),
                Jsonb({
                    "annotations_count": len(result.annotations),
                    "provider_model": result.payload.get("model"),
                }),
                call_id,
            ),
        )

        inserted = 0
        for item in normalized:
            row = conn.execute(
                """
                INSERT INTO supplier_offers(
                    run_id,archetype_id,search_call_id,source,supplier_name,
                    product_title,source_url,price_text,moq_text,lead_time_text,
                    customization_text,feature_summary,country,
                    source_quality,raw_data
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0.80,%s
                )
                ON CONFLICT (run_id,archetype_id,source,source_url)
                WHERE archetype_id IS NOT NULL
                DO UPDATE SET
                    search_call_id=EXCLUDED.search_call_id,
                    supplier_name=COALESCE(EXCLUDED.supplier_name,supplier_offers.supplier_name),
                    product_title=EXCLUDED.product_title,
                    price_text=COALESCE(EXCLUDED.price_text,supplier_offers.price_text),
                    moq_text=COALESCE(EXCLUDED.moq_text,supplier_offers.moq_text),
                    lead_time_text=COALESCE(EXCLUDED.lead_time_text,supplier_offers.lead_time_text),
                    customization_text=COALESCE(EXCLUDED.customization_text,supplier_offers.customization_text),
                    feature_summary=COALESCE(NULLIF(EXCLUDED.feature_summary,''),supplier_offers.feature_summary),
                    country=COALESCE(EXCLUDED.country,supplier_offers.country),
                    raw_data=EXCLUDED.raw_data
                RETURNING id
                """,
                (
                    run_id, archetype_id, call_id, source,
                    item["supplier_name"], item["product_title"],
                    item["source_url"], item["price_text"], item["moq_text"],
                    item["lead_time_text"], item["customization_text"],
                    item["feature_summary"], item["country"], Jsonb(item["raw"]),
                ),
            ).fetchone()
            if row:
                inserted += 1

    _refresh_counters(run_id)
    budget.refresh(run_id)
    return inserted
def _persist_failure(
    run_id: str,
    call_id: int,
    error: str,
    *,
    cost_usd: Decimal | float | str = 0,
    usage: dict[str, Any] | None = None,
) -> None:
    usage = usage or {}
    with connect() as conn:
        conn.execute(
            """
            UPDATE supplier_search_calls
            SET status='failed',error=%s,cost_usd=%s,
                prompt_tokens=%s,completion_tokens=%s,total_tokens=%s,
                completed_at=now()
            WHERE id=%s
            """,
            (
                error[:2000],
                Decimal(str(cost_usd or 0)),
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
                call_id,
            ),
        )
    _refresh_counters(run_id)


def _reuse_cached_call(
    run_id: str,
    archetype_id: int,
    source: str,
    query: str,
    engine: str,
) -> bool:
    with connect() as conn:
        old = conn.execute(
            """
            SELECT id,result_count
            FROM supplier_search_calls
            WHERE run_id<>%s AND source=%s AND query=%s AND engine=%s
              AND run_id IN (SELECT id FROM research_runs WHERE pipeline_version=2)
              AND model=%s AND status='done'
              AND COALESCE((response_meta->>'cache_hit')::boolean,false)=false
              AND completed_at >= now() - interval '6 hours'
            ORDER BY completed_at DESC
            LIMIT 1
            """,
            (run_id, source, query, engine, _model()),
        ).fetchone()
        if not old:
            return False

        cached = conn.execute(
            """
            INSERT INTO supplier_search_calls(
                run_id,archetype_id,source,query,engine,model,status,
                cost_usd,result_count,response_meta,completed_at
            ) VALUES (%s,%s,%s,%s,%s,%s,'done',0,%s,%s,now())
            RETURNING id
            """,
            (
                run_id, archetype_id, source, query, engine, _model(),
                old["result_count"],
                Jsonb({"cache_hit": True, "source_call_id": old["id"]}),
            ),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO supplier_offers(
                run_id,archetype_id,search_call_id,source,supplier_name,
                product_title,source_url,price_text,moq_text,lead_time_text,
                customization_text,feature_summary,country,source_quality,raw_data,created_at
            )
            SELECT %s,%s,%s,source,supplier_name,
                   product_title,source_url,price_text,moq_text,lead_time_text,
                   customization_text,feature_summary,country,source_quality,raw_data,created_at
            FROM supplier_offers
            WHERE search_call_id=%s
            ON CONFLICT (run_id,archetype_id,source,source_url)
            WHERE archetype_id IS NOT NULL
            DO NOTHING
            """,
            (run_id, archetype_id, cached["id"], old["id"]),
        )

    _refresh_counters(run_id)
    budget.refresh(run_id)
    return True
def _run_one(
    run_id: str,
    dataset_key: str,
    archetype: dict[str, Any],
    source: str,
) -> None:
    archetype_id = int(archetype["id"])
    query = _query_for(
        run_id,
        dataset_key,
        archetype["archetype_key"],
        archetype["label"],
    )
    cfg = SOURCES[source]
    engine = cfg["engine"]

    if _existing_done(run_id, archetype_id, source, query):
        return
    if _reuse_cached_call(run_id, archetype_id, source, query, engine):
        return

    try:
        reservation = budget.reserve(run_id,'supplier')
    except budget.BudgetBlocked as exc:
        _mark_budget_blocked(run_id,archetype_id,source,query,engine,str(exc))
        budget.warning(run_id,str(exc))
        return
    billed = None
    call_id = _create_call(run_id, archetype_id, source, query, engine)
    try:
        result = supplier_search(
            query=query,
            source=cfg["label"],
            allowed_domains=cfg["domains"],
            max_results=6,
            engine=engine,
        )
        billed = result.cost_usd if result.usage.get('cost') is not None else None
        _persist_success(
            run_id=run_id,
            archetype_id=archetype_id,
            call_id=call_id,
            source=source,
            result=result,
        )
    except OpenRouterError as exc:
        billed = exc.cost_usd if exc.usage else None
        _persist_failure(
            run_id,
            call_id,
            str(exc),
            cost_usd=exc.cost_usd,
            usage=exc.usage,
        )
    except Exception as exc:
        _persist_failure(
            run_id, call_id, f"{type(exc).__name__}: {exc}"
        )
    finally:
        budget.settle(reservation,billed)


def _archetype_summary(
    run_id: str,
    archetype: dict[str, Any],
) -> dict[str, Any]:
    archetype_id = int(archetype["id"])
    with connect() as conn:
        calls = conn.execute(
            """
            SELECT source,
                   COUNT(*) FILTER (WHERE status='done') AS done_calls,
                   COUNT(*) FILTER (WHERE status='failed') AS failed_calls,
                   COUNT(*) FILTER (WHERE status='budget_blocked') AS blocked_calls,
                   COALESCE(SUM(cost_usd),0) AS cost
            FROM supplier_search_calls
            WHERE run_id=%s AND archetype_id=%s
            GROUP BY source
            """,
            (run_id, archetype_id),
        ).fetchall()
        offers = conn.execute(
            """
            SELECT source,COUNT(*) AS count
            FROM supplier_offers
            WHERE run_id=%s AND archetype_id=%s
            GROUP BY source
            """,
            (run_id, archetype_id),
        ).fetchall()

    offer_map = {row["source"]: int(row["count"] or 0) for row in offers}
    call_map = {row["source"]: row for row in calls}
    sources: dict[str, Any] = {}
    for source in SOURCES:
        row = call_map.get(source) or {}
        done = int(row.get("done_calls") or 0)
        failed = int(row.get("failed_calls") or 0)
        blocked = int(row.get("blocked_calls") or 0)
        status = (
            "done" if done
            else "failed" if failed
            else "budget_blocked" if blocked
            else "empty"
        )
        sources[source] = {
            "status": status,
            "queries": done,
            "records": offer_map.get(source, 0),
            "cost_usd": float(row.get("cost") or 0),
        }

    return {
        "archetype_id": archetype_id,
        "archetype_key": archetype["archetype_key"],
        "label": archetype["label"],
        "opportunity_score": float(archetype["opportunity_score"]),
        "sources": sources,
        "records": sum(offer_map.values()),
        "cost_usd": sum(
            item["cost_usd"] for item in sources.values()
        ),
    }
def run_live_supplier_probe(
    run_id: str,
    dataset_key: str,
    limit: int = 5,
) -> dict[str, Any]:
    if not _enabled():
        return {
            "enabled": False,
            "status": "disabled",
            "archetypes": [],
            "records": 0,
            "cost_usd": 0.0,
        }

    archetypes = _top_archetypes(run_id, limit)
    if not archetypes:
        return {
            "enabled": True,
            "status": "empty",
            "archetypes": [],
            "records": 0,
            "cost_usd": 0.0,
        }

    planned: list[tuple[dict[str, Any], str, str]] = []
    for archetype in archetypes:
        query = _query_for(
            run_id,
            dataset_key,
            archetype["archetype_key"],
            archetype["label"],
        )
        for source, cfg in SOURCES.items():
            if not _existing_done(
                run_id, int(archetype["id"]), source, query
            ):
                _reuse_cached_call(
                    run_id, int(archetype["id"]), source,
                    query, cfg["engine"]
                )
            if not _existing_done(
                run_id, int(archetype["id"]), source, query
            ):
                planned.append((archetype, source, query))

    executable = planned

    if executable:
        with ThreadPoolExecutor(max_workers=min(10, len(executable))) as pool:
            futures = [
                pool.submit(
                    _run_one, run_id, dataset_key, archetype, source
                )
                for archetype, source, _ in executable
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

    summaries = [
        _archetype_summary(run_id, archetype)
        for archetype in archetypes
    ]
    _refresh_counters(run_id)
    return {
        "enabled": True,
        "status": "done",
        "archetypes": summaries,
        "records": sum(item["records"] for item in summaries),
        "cost_usd": float(_spent_run(run_id)),
    }


def supplier_evidence(
    run_id: str,
    archetype_id: int | None = None,
) -> dict[str, Any]:
    params: list[Any] = [run_id]
    call_where = "run_id=%s"
    offer_where = "run_id=%s"
    if archetype_id is not None:
        call_where += " AND archetype_id=%s"
        offer_where += " AND archetype_id=%s"
        params.append(archetype_id)

    with connect() as conn:
        calls = conn.execute(
            f"""
            SELECT id,archetype_id,source,query,engine,model,status,
                   cost_usd,prompt_tokens,completion_tokens,total_tokens,
                   result_count,response_meta,error,created_at,completed_at
            FROM supplier_search_calls
            WHERE {call_where}
            ORDER BY id
            """,
            tuple(params),
        ).fetchall()
        offers = conn.execute(
            f"""
            SELECT id,archetype_id,source,supplier_name,product_title,
                   source_url,price_text,moq_text,lead_time_text,
                   customization_text,feature_summary,country,
                   source_quality,created_at,raw_data
            FROM supplier_offers
            WHERE {offer_where}
            ORDER BY source,id
            """,
            tuple(params),
        ).fetchall()

    return {"search_calls": calls, "offers": offers}
