from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.openrouter_client import OpenRouterError, scout_search

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

SUPPLIER_QUERIES = {
    "vacuum": "cordless stick vacuum OEM manufacturer private label price MOQ",
    "bath": "bath mat OEM manufacturer private label price MOQ",
    "led": "RGBIC LED strip OEM manufacturer private label price MOQ",
}

ARCHETYPE_SUPPLIER_QUERIES = {
    "vacuum": {
        "bendable_led": "cordless stick vacuum bendable tube LED OEM manufacturer private label price MOQ",
        "pet_hair": "cordless stick vacuum pet hair anti tangle OEM manufacturer private label price MOQ",
        "wet_dry": "wet dry stick vacuum self cleaning dual tank OEM manufacturer private label price MOQ",
        "auto_empty": "cordless stick vacuum auto empty dock OEM manufacturer private label price MOQ",
        "self_standing": "self standing cordless stick vacuum removable battery OEM manufacturer price MOQ",
        "basic_cordless": "cordless stick vacuum OEM manufacturer private label price MOQ",
    },
    "bath": {
        "stone_diatomite": "diatomite stone bath mat quick dry OEM manufacturer private label price MOQ",
        "quick_dry": "quick dry absorbent bath mat OEM manufacturer private label price MOQ",
        "drainage": "drainage ribbed bath mat OEM manufacturer private label price MOQ",
        "memory_foam": "memory foam bath mat OEM manufacturer private label price MOQ",
        "eva_modular": "EVA modular bath mat OEM manufacturer private label price MOQ",
    },
    "led": {
        "matter": "RGBIC LED strip Matter Thread OEM manufacturer private label price MOQ",
        "tv_camera": "TV backlight RGBIC camera sync OEM manufacturer private label price MOQ",
        "desktop": "monitor ambient RGBIC LED kit OEM manufacturer private label price MOQ",
        "neon": "RGBIC neon rope OEM manufacturer private label price MOQ",
        "outdoor": "outdoor RGBIC LED strip IP67 OEM manufacturer private label price MOQ",
        "generic_rgbic": "RGBIC LED strip OEM manufacturer private label price MOQ",
    },
}
def _top_archetype_key(run_id: str) -> str | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT pa.archetype_key
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s
            ORDER BY os.opportunity_score DESC, pa.member_count DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
    return row["archetype_key"] if row else None


def _supplier_query(run_id: str, dataset_key: str) -> str:
    archetype_key = _top_archetype_key(run_id)
    return (
        ARCHETYPE_SUPPLIER_QUERIES.get(dataset_key, {}).get(archetype_key)
        or SUPPLIER_QUERIES[dataset_key]
    )


def _enabled() -> bool:
    return os.environ.get("PRODUCT_HUNTER_LIVE_SCOUT", "0").strip() == "1"


def _model() -> str:
    return os.environ.get(
        "PRODUCT_HUNTER_SCOUT_MODEL",
        "qwen/qwen3-30b-a3b-instruct-2507",
    ).strip()


def _run_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_SUPPLIER_BUDGET_USD", "0.05"))


def _daily_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_DAILY_LIVE_BUDGET_USD", "3.00"))


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
        suppliers = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM supplier_search_calls
            WHERE created_at >= date_trunc('day',now())
            """
        ).fetchone()
    return Decimal(str(market["cost"] or 0)) + Decimal(str(suppliers["cost"] or 0))
def _existing_done(run_id: str, source: str, query: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM supplier_search_calls
            WHERE run_id=%s AND source=%s AND query=%s AND status='done'
            LIMIT 1
            """,
            (run_id, source, query),
        ).fetchone()
    return bool(row)


def _create_call(run_id: str, source: str, query: str, engine: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO supplier_search_calls(
                run_id,source,query,engine,model,status
            ) VALUES (%s,%s,%s,%s,%s,'running')
            RETURNING id
            """,
            (run_id, source, query, engine, _model()),
        ).fetchone()
    return int(row["id"])


def _mark_budget_blocked(
    run_id: str, source: str, query: str, engine: str, reason: str
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO supplier_search_calls(
                run_id,source,query,engine,model,status,error,completed_at
            ) VALUES (%s,%s,%s,%s,%s,'budget_blocked',%s,now())
            """,
            (run_id, source, query, engine, _model(), reason),
        )
def _refresh_counters(run_id: str) -> None:
    with connect() as conn:
        market = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls WHERE run_id=%s
            """,
            (run_id,),
        ).fetchone()
        supplier = conn.execute(
            """
            SELECT
                COALESCE(SUM(cost_usd),0) AS cost,
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
    *, run_id: str, call_id: int, source: str, result
) -> int:
    usage = result.usage or {}
    normalized = [
        _normalize_offer(item)
        for item in result.products
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
            SET status='done',cost_usd=%s,prompt_tokens=%s,completion_tokens=%s,
                total_tokens=%s,result_count=%s,response_meta=%s,completed_at=now()
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
                    run_id,search_call_id,source,supplier_name,product_title,
                    source_url,price_text,moq_text,lead_time_text,
                    customization_text,feature_summary,country,source_quality,raw_data
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0.80,%s
                )
                ON CONFLICT (run_id,source,source_url) DO UPDATE SET
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
                    run_id, call_id, source, item["supplier_name"],
                    item["product_title"], item["source_url"], item["price_text"],
                    item["moq_text"], item["lead_time_text"],
                    item["customization_text"], item["feature_summary"],
                    item["country"], Jsonb(item["raw"]),
                ),
            ).fetchone()
            if row:
                inserted += 1

    _refresh_counters(run_id)
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


def _offer_count(run_id: str, source: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM supplier_offers WHERE run_id=%s AND source=%s",
            (run_id, source),
        ).fetchone()
    return int(row["count"] or 0)
def _reuse_cached_call(run_id: str, source: str, query: str, engine: str) -> bool:
    with connect() as conn:
        old = conn.execute(
            """
            SELECT id,result_count
            FROM supplier_search_calls
            WHERE run_id<>%s AND source=%s AND query=%s AND engine=%s
              AND model=%s AND status='done'
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
                run_id,source,query,engine,model,status,cost_usd,
                result_count,response_meta,completed_at
            ) VALUES (%s,%s,%s,%s,%s,'done',0,%s,%s,now())
            RETURNING id
            """,
            (
                run_id, source, query, engine, _model(),
                old["result_count"],
                Jsonb({"cache_hit": True, "source_call_id": old["id"]}),
            ),
        ).fetchone()
        cached_id = cached["id"]

        conn.execute(
            """
            INSERT INTO supplier_offers(
                run_id,search_call_id,source,supplier_name,product_title,
                source_url,price_text,moq_text,lead_time_text,
                customization_text,feature_summary,country,source_quality,raw_data
            )
            SELECT %s,%s,source,supplier_name,product_title,
                   source_url,price_text,moq_text,lead_time_text,
                   customization_text,feature_summary,country,source_quality,raw_data
            FROM supplier_offers
            WHERE search_call_id=%s
            ON CONFLICT (run_id,source,source_url) DO NOTHING
            """,
            (run_id, cached_id, old["id"]),
        )

    _refresh_counters(run_id)
    return True
def _run_source(run_id: str, dataset_key: str, source: str) -> None:
    cfg = SOURCES[source]
    query = _supplier_query(run_id, dataset_key)
    engine = cfg["engine"]

    if _existing_done(run_id, source, query):
        return
    if _reuse_cached_call(run_id, source, query, engine):
        return

    call_id = _create_call(run_id, source, query, engine)
    try:
        result = scout_search(
            query=query,
            market=cfg["label"],
            allowed_domains=cfg["domains"],
            max_results=6,
            engine=engine,
        )
        _persist_success(
            run_id=run_id,
            call_id=call_id,
            source=source,
            result=result,
        )
    except OpenRouterError as exc:
        _persist_failure(
            run_id,
            call_id,
            str(exc),
            cost_usd=exc.cost_usd,
            usage=exc.usage,
        )
    except Exception as exc:
        _persist_failure(run_id, call_id, f"{type(exc).__name__}: {exc}")


def _source_summary(run_id: str, source: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status='done') AS done_calls,
                COUNT(*) FILTER (WHERE status='failed') AS failed_calls,
                COUNT(*) FILTER (WHERE status='budget_blocked') AS blocked_calls,
                COALESCE(SUM(cost_usd),0) AS cost
            FROM supplier_search_calls
            WHERE run_id=%s AND source=%s
            """,
            (run_id, source),
        ).fetchone()
    done = int(row["done_calls"] or 0)
    failed = int(row["failed_calls"] or 0)
    blocked = int(row["blocked_calls"] or 0)
    records = _offer_count(run_id, source)
    status = (
        "done" if done
        else "failed" if failed
        else "budget_blocked" if blocked
        else "empty"
    )
    return {
        "enabled": True,
        "status": status,
        "records": records,
        "queries": done,
        "cost_usd": float(row["cost"] or 0),
    }
def run_live_supplier_probe(
    run_id: str,
    dataset_key: str,
) -> dict[str, Any]:
    if not _enabled() or dataset_key not in SUPPLIER_QUERIES:
        return {
            "enabled": False,
            "status": "disabled",
            "sources": {},
            "records": 0,
            "cost_usd": 0.0,
        }

    planned = list(SOURCES)
    query = _supplier_query(run_id, dataset_key)
    for source in planned:
        cfg = SOURCES[source]
        if not _existing_done(run_id, source, query):
            _reuse_cached_call(run_id, source, query, cfg["engine"])

    pending = [
        source for source in planned
        if not _existing_done(run_id, source, query)
    ]

    available = min(
        max(Decimal("0"), _run_cap() - _spent_run(run_id)),
        max(Decimal("0"), _daily_cap() - _spent_today_total()),
    )
    planned_call_cost = Decimal("0.012")
    allowed_new = min(len(pending), int(available / planned_call_cost))

    executable = pending[:allowed_new]
    blocked = pending[allowed_new:]
    for source in blocked:
        cfg = SOURCES[source]
        _mark_budget_blocked(
            run_id, source, query, cfg["engine"],
            "supplier budget guard reserved capacity",
        )

    if executable:
        with ThreadPoolExecutor(max_workers=len(executable)) as pool:
            futures = [
                pool.submit(_run_source, run_id, dataset_key, source)
                for source in executable
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

    summaries = {
        source: _source_summary(run_id, source)
        for source in SOURCES
    }
    cost = sum(item["cost_usd"] for item in summaries.values())
    records = sum(item["records"] for item in summaries.values())
    status = "done" if any(item["queries"] for item in summaries.values()) else "failed"
    _refresh_counters(run_id)
    return {
        "enabled": True,
        "status": status,
        "sources": summaries,
        "records": records,
        "cost_usd": cost,
    }


def supplier_evidence(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        calls = conn.execute(
            """
            SELECT id,source,query,engine,model,status,cost_usd,prompt_tokens,
                   completion_tokens,total_tokens,result_count,response_meta,error,
                   created_at,completed_at
            FROM supplier_search_calls
            WHERE run_id=%s
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
        offers = conn.execute(
            """
            SELECT id,source,supplier_name,product_title,source_url,price_text,
                   moq_text,lead_time_text,customization_text,feature_summary,
                   country,source_quality,created_at
            FROM supplier_offers
            WHERE run_id=%s
            ORDER BY source,id
            """,
            (run_id,),
        ).fetchall()
    return {"search_calls": calls, "offers": offers}