from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.openrouter_client import OpenRouterError, scout_search

MARKETS = {
    "wb": {
        "label": "Wildberries",
        "engine": "exa",
        "domains": ["wildberries.ru", "global.wildberries.ru"],
        "queries": {
            "vacuum": [
                "вертикальный беспроводной пылесос Wildberries",
                "вертикальный пылесос складная труба LED Wildberries",
            ],
            "bath": [
                "коврик для ванной быстросохнущий Wildberries",
                "каменный коврик для ванной Wildberries",
            ],
            "led": [
                "светодиодная лента RGBIC Wildberries",
                "светодиодная лента Matter умный дом Wildberries",
            ],
        },
    },
    "ozon": {
        "label": "Ozon",
        "engine": "parallel",
        "domains": ["ozon.ru"],
        "queries": {
            "vacuum": [
                "вертикальный беспроводной пылесос Ozon",
                "вертикальный пылесос складная труба Ozon",
            ],
            "bath": [
                "коврик для ванной быстросохнущий Ozon",
                "каменный коврик для ванной Ozon",
            ],
            "led": [
                "светодиодная лента RGBIC Ozon",
                "светодиодная лента Matter умный дом Ozon",
            ],
        },
    },
    "amazon": {
        "label": "Amazon",
        "engine": "exa",
        "domains": ["amazon.com", "amazon.de"],
        "queries": {
            "vacuum": [
                "cordless stick vacuum bendable tube LED",
                "cordless stick vacuum pet hair anti tangle lightweight",
            ],
            "bath": [
                "diatomite stone bath mat quick dry non slip",
                "quick dry bath mat multilayer absorbent non slip",
            ],
            "led": [
                "RGBIC LED strip Matter Thread smart home",
                "TV backlight camera sync RGBIC",
            ],
        },
    },
    "lazada": {
        "label": "Lazada",
        "engine": "exa",
        "domains": [
            "lazada.sg", "lazada.com.ph", "lazada.com.my",
            "lazada.co.th", "lazada.vn", "lazada.co.id",
        ],
        "queries": {
            "vacuum": [
                "cordless stick vacuum bendable tube LED",
                "cordless stick vacuum pet hair anti tangle",
            ],
            "bath": [
                "diatomite stone bath mat quick dry",
                "quick dry absorbent bath mat non slip",
            ],
            "led": [
                "RGBIC LED strip Matter smart home",
                "TV backlight camera sync RGBIC",
            ],
        },
    },
}


from backend.marketplaces import ACTIVE, run_config
from backend import budget
MARKETS = {k:dict(v, queries=(MARKETS.get(k) or {}).get('queries',{})) for k,v in ACTIVE.items()}

def _query_plan(run_id, dataset_key):
    run=run_config(run_id)
    ontology=run.get('ontology') or {}
    return {m:[str(q).strip()+' '+ACTIVE[m]['country'] for q in (ontology.get('market_queries',{}).get(m) or [])][:2] for m in run['selected_markets']}

def _enabled() -> bool:
    return os.environ.get("PRODUCT_HUNTER_LIVE_SCOUT", "0").strip() == "1"


def _run_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_LIVE_SCOUT_BUDGET_USD", "0.15"))


def _daily_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_DAILY_LIVE_BUDGET_USD", "3.00"))


def _model() -> str:
    return os.environ.get(
        "PRODUCT_HUNTER_SCOUT_MODEL",
        "qwen/qwen3-30b-a3b-instruct-2507",
    )


def _spent_today() -> Decimal:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE created_at >= date_trunc('day', now())
            """
        ).fetchone()
    return Decimal(str(row["cost"] or 0))


def _spent_run(run_id: str) -> Decimal:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE run_id=%s
            """,
            (run_id,),
        ).fetchone()
    return Decimal(str(row["cost"] or 0))


def _spent_market(run_id: str, market: str) -> Decimal:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE run_id=%s AND market=%s
            """,
            (run_id, market),
        ).fetchone()
    return Decimal(str(row["cost"] or 0))
def _existing_done(run_id: str, market: str, query: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM search_calls
            WHERE run_id=%s AND market=%s AND query=%s AND status='done'
            LIMIT 1
            """,
            (run_id, market, query),
        ).fetchone()
    return bool(row)


def _create_call(run_id: str, market: str, query: str, engine: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO search_calls(run_id,market,query,engine,model,status)
            VALUES (%s,%s,%s,%s,%s,'running')
            RETURNING id
            """,
            (run_id, market, query, engine, _model()),
        ).fetchone()
    return int(row["id"])


def _mark_budget_blocked(
    run_id: str, market: str, query: str, engine: str, reason: str
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO search_calls(
                run_id,market,query,engine,model,status,error,completed_at
            ) VALUES (%s,%s,%s,%s,%s,'budget_blocked',%s,now())
            """,
            (run_id, market, query, engine, _model(), reason),
        )


def _parse_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("\u00a0", " ").strip().lower()
    match = re.search(r"\d+(?:[\s.,]\d+)*", text)
    if not match:
        return None
    raw = match.group(0).replace(" ", "")
    if raw.count(",") == 1 and "." not in raw:
        raw = raw.replace(",", ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        number = float(raw)
    except ValueError:
        return None
    if "k" in text or "тыс" in text:
        number *= 1000
    elif "m" in text or "млн" in text:
        number *= 1000000
    return number


def _parse_int(value: Any) -> int | None:
    number = _parse_number(value)
    return int(round(number)) if number is not None else None


def _normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(product.get("title") or product.get("name") or "").strip(),
        "source_url": str(product.get("url") or "").strip(),
        "brand": product.get("brand"),
        "price_text": product.get("price_text", product.get("price")),
        "rating": _parse_number(product.get("rating")),
        "review_count": _parse_int(product.get("review_count", product.get("reviews"))),
        "feature_summary": str(
            product.get("feature_summary")
            or product.get("features")
            or product.get("summary")
            or product.get("description")
            or ""
        ).strip(),
        "raw": product,
    }
def _refresh_run_live_counters(run_id: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE research_runs
            SET actual_cost_usd=(
                    SELECT COALESCE(SUM(cost_usd),0)
                    FROM search_calls
                    WHERE run_id=%s
                ),
                estimated_cost_usd=(
                    SELECT COALESCE(SUM(cost_usd),0)
                    FROM search_calls
                    WHERE run_id=%s
                ),
                live_search_calls=(
                    SELECT COUNT(*)
                    FROM search_calls
                    WHERE run_id=%s
                      AND status IN ('done','failed')
                ),
                live_records=(
                    SELECT COUNT(*)
                    FROM raw_products
                    WHERE run_id=%s
                ),
                updated_at=now()
            WHERE id=%s
            """,
            (run_id, run_id, run_id, run_id, run_id),
        )


def _persist_success(*, run_id: str, call_id: int, market: str, result) -> int:
    usage = result.usage or {}
    normalized = [_normalize_product(p) for p in result.products if isinstance(p, dict)]
    normalized = [p for p in normalized if p["title"] and p["source_url"]]

    with connect() as conn:
        conn.execute(
            """
            UPDATE search_calls
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
        for product in normalized:
            product['raw']['target_country'] = MARKETS[market]['country']
            product['raw']['expected_currency'] = MARKETS[market]['currency']
            product['raw']['field_provenance'] = 'web_search_extraction'
            row = conn.execute(
                """
                INSERT INTO raw_products(
                    run_id,search_call_id,market,title,source_url,brand,price_text,
                    rating,review_count,feature_summary,source_quality,raw_data
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0.80,%s
                )
                ON CONFLICT (run_id,market,source_url) DO UPDATE SET
                    search_call_id=EXCLUDED.search_call_id,
                    title=EXCLUDED.title,
                    brand=COALESCE(EXCLUDED.brand,raw_products.brand),
                    price_text=COALESCE(EXCLUDED.price_text,raw_products.price_text),
                    rating=COALESCE(EXCLUDED.rating,raw_products.rating),
                    review_count=COALESCE(EXCLUDED.review_count,raw_products.review_count),
                    feature_summary=COALESCE(NULLIF(EXCLUDED.feature_summary,''),raw_products.feature_summary),
                    raw_data=EXCLUDED.raw_data
                RETURNING id
                """,
                (
                    run_id, call_id, market, product["title"], product["source_url"],
                    product["brand"], product["price_text"], product["rating"],
                    product["review_count"], product["feature_summary"], Jsonb(product["raw"]),
                ),
            ).fetchone()
            if row:
                inserted += 1

            conn.execute(
                """
                INSERT INTO source_documents(
                    run_id,search_call_id,market,source_url,title,source_kind,meta
                ) VALUES (%s,%s,%s,%s,%s,'marketplace_product',%s)
                ON CONFLICT (run_id,source_url) DO NOTHING
                """,
                (
                    run_id, call_id, market, product["source_url"], product["title"],
                    Jsonb({"source": "openrouter_web_search"}),
                ),
            )
    _refresh_run_live_counters(run_id)
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
            UPDATE search_calls
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
    _refresh_run_live_counters(run_id)


def _market_record_count(run_id: str, market: str) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM raw_products WHERE run_id=%s AND market=%s",
            (run_id, market),
        ).fetchone()
    return int(row["count"] or 0)


def _run_one_query(run_id: str, market: str, query: str) -> None:
    if _existing_done(run_id, market, query):
        return
    cfg = MARKETS[market]
    engine = cfg.get("engine", "exa")
    try:
        reservation = budget.reserve(run_id,'market')
    except budget.BudgetBlocked as exc:
        _mark_budget_blocked(run_id,market,query,engine,str(exc))
        budget.warning(run_id,str(exc))
        return
    billed = None
    call_id = _create_call(run_id, market, query, engine)
    try:
        result = scout_search(
            query=query,
            market=cfg["label"],
            allowed_domains=cfg["domains"],
            max_results=5,
            engine=engine,
        )
        billed = result.cost_usd if result.usage.get('cost') is not None else None
        _persist_success(
            run_id=run_id, call_id=call_id, market=market, result=result
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
        _persist_failure(run_id, call_id, f"{type(exc).__name__}: {exc}")
    finally:
        budget.settle(reservation,billed)


def _market_summary(run_id: str, market: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (query)
                    query,status,error
                FROM search_calls
                WHERE run_id=%s AND market=%s
                ORDER BY query,id DESC
            )
            SELECT
                COUNT(*) FILTER (WHERE status='done') AS done_calls,
                COUNT(*) FILTER (WHERE status='failed') AS failed_calls,
                COUNT(*) FILTER (WHERE status='budget_blocked') AS blocked_calls
            FROM latest
            """,
            (run_id, market),
        ).fetchone()
        cost_row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE run_id=%s AND market=%s
            """,
            (run_id, market),
        ).fetchone()
        errors = conn.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (query)
                    query,status,error,id
                FROM search_calls
                WHERE run_id=%s AND market=%s
                ORDER BY query,id DESC
            )
            SELECT error
            FROM latest
            WHERE status='failed' AND error IS NOT NULL
            ORDER BY id DESC
            LIMIT 3
            """,
            (run_id, market),
        ).fetchall()
    done = int(row["done_calls"] or 0)
    failed = int(row["failed_calls"] or 0)
    blocked = int(row["blocked_calls"] or 0)
    records = _market_record_count(run_id, market)

    if done and (failed or blocked):
        status = "partial"
    elif done and records == 0:
        status = "empty"
    elif done:
        status = "done"
    elif failed:
        status = "failed"
    elif blocked:
        status = "budget_blocked"
    else:
        status = "empty"

    return {
        "enabled": True,
        "status": status,
        "records": records,
        "queries": done,
        "cost_usd": float(cost_row["cost"] or 0),
        "errors": [item["error"] for item in errors if item.get("error")],
    }


def _reuse_cached_call(run_id: str, market: str, query: str, engine: str) -> bool:
    with connect() as conn:
        source = conn.execute(
            """
            SELECT id,result_count
            FROM search_calls
            WHERE run_id<>%s
              AND run_id IN (SELECT id FROM research_runs WHERE pipeline_version=2)
              AND market=%s
              AND query=%s
              AND engine=%s
              AND model=%s
              AND status='done'
              AND COALESCE((response_meta->>'cache_hit')::boolean,false)=false
              AND completed_at >= now() - interval '6 hours'
            ORDER BY completed_at DESC
            LIMIT 1
            """,
            (run_id, market, query, engine, _model()),
        ).fetchone()
        if not source:
            return False

        cached = conn.execute(
            """
            INSERT INTO search_calls(
                run_id,market,query,engine,model,status,cost_usd,
                result_count,response_meta,completed_at
            ) VALUES (%s,%s,%s,%s,%s,'done',0,%s,%s,now())
            RETURNING id
            """,
            (
                run_id, market, query, engine, _model(),
                source["result_count"],
                Jsonb({"cache_hit": True, "source_call_id": source["id"]}),
            ),
        ).fetchone()
        cached_id = cached["id"]

        conn.execute(
            """
            INSERT INTO raw_products(
                run_id,search_call_id,market,title,source_url,brand,price_text,
                rating,review_count,feature_summary,source_quality,raw_data,created_at
            )
            SELECT %s,%s,market,title,source_url,brand,price_text,
                   rating,review_count,feature_summary,source_quality,raw_data,created_at
            FROM raw_products
            WHERE search_call_id=%s
            ON CONFLICT (run_id,market,source_url) DO NOTHING
            """,
            (run_id, cached_id, source["id"]),
        )

        conn.execute(
            """
            INSERT INTO source_documents(
                run_id,search_call_id,market,source_url,title,source_kind,meta
            )
            SELECT %s,%s,market,source_url,title,source_kind,meta
            FROM source_documents
            WHERE search_call_id=%s
            ON CONFLICT (run_id,source_url) DO NOTHING
            """,
            (run_id, cached_id, source["id"]),
        )

    _refresh_run_live_counters(run_id)
    budget.refresh(run_id)
    return True


def run_live_market_scouts(run_id: str, dataset_key: str, user_query: str) -> dict[str, dict[str, Any]]:
    if not _enabled():
        return {
            market: {
                "enabled": False, "status": "disabled", "records": 0,
                "queries": 0, "cost_usd": 0.0, "errors": [],
            }
            for market in run_config(run_id)["selected_markets"]
        }

    query_plan = _query_plan(run_id, dataset_key)
    if not any(query_plan.values()):
        return {
            market: {
                "enabled": False, "status": "no_query_plan", "records": 0,
                "queries": 0, "cost_usd": 0.0, "errors": [],
            }
            for market in run_config(run_id)["selected_markets"]
        }

    planned: list[tuple[str, str]] = []
    max_queries = max((len(items) for items in query_plan.values()), default=0)
    for query_index in range(max_queries):
        for market in run_config(run_id)["selected_markets"]:
            queries = query_plan.get(market) or []
            if query_index < len(queries):
                planned.append((market, queries[query_index]))

    for market, query in planned:
        if _existing_done(run_id, market, query):
            continue
        cfg = MARKETS[market]
        _reuse_cached_call(
            run_id, market, query, cfg.get("engine", "exa")
        )

    pending = [
        item for item in planned
        if not _existing_done(run_id, item[0], item[1])
    ]

    executable = pending

    if executable:
        with ThreadPoolExecutor(max_workers=min(8, len(executable))) as pool:
            futures = [
                pool.submit(_run_one_query, run_id, market, query)
                for market, query in executable
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass

    return {
        market: _market_summary(run_id, market)
        for market in run_config(run_id)["selected_markets"]
    }


def live_evidence(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        calls = conn.execute(
            """
            SELECT id,market,query,engine,model,status,cost_usd,prompt_tokens,
                   completion_tokens,total_tokens,result_count,response_meta,
                   error,created_at,completed_at
            FROM search_calls
            WHERE run_id=%s
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
        products = conn.execute(
            """
            SELECT id,market,title,source_url,brand,price_text,rating,review_count,
                   feature_summary,source_quality,created_at
            FROM raw_products
            WHERE run_id=%s
            ORDER BY market,id
            """,
            (run_id,),
        ).fetchall()
    return {"search_calls": calls, "products": products}
