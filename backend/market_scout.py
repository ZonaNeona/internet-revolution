from __future__ import annotations

import os
import re
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.openrouter_client import OpenRouterError, scout_search

AMAZON_DOMAINS = ["amazon.com", "amazon.de"]

AMAZON_QUERIES = {
    "vacuum": [
        "cordless stick vacuum bendable tube LED",
        "cordless stick vacuum pet hair anti tangle lightweight",
        "wet dry stick vacuum self cleaning dual tank",
    ],
    "bath": [
        "diatomite stone bath mat quick dry non slip",
        "quick dry bath mat multilayer absorbent non slip",
        "modular EVA bath mat wet area drainage",
    ],
    "led": [
        "RGBIC LED strip Matter Thread smart home",
        "TV backlight camera sync RGBIC",
        "monitor ambient light kit RGBIC USB C",
    ],
}
def _supported_demo_query(dataset_key: str, user_query: str) -> bool:
    q = user_query.casefold()
    if dataset_key == "vacuum":
        return "пылесос" in q or "vacuum" in q
    if dataset_key == "bath":
        return "коврик" in q or "bath mat" in q or "камен" in q
    if dataset_key == "led":
        return "лент" in q or "rgb" in q or "led" in q or "matter" in q
    return False


def _enabled() -> bool:
    return os.environ.get("PRODUCT_HUNTER_LIVE_SCOUT", "0").strip() == "1"


def _run_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_LIVE_SCOUT_BUDGET_USD", "0.08"))


def _daily_cap() -> Decimal:
    return Decimal(os.environ.get("PRODUCT_HUNTER_DAILY_LIVE_BUDGET_USD", "3.00"))


def _model() -> str:
    return os.environ.get("PRODUCT_HUNTER_SCOUT_MODEL", "qwen/qwen3-30b-a3b")


def _spent_today() -> Decimal:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE created_at >= date_trunc('day', now())
              AND status='done'
            """
        ).fetchone()
    return Decimal(str(row["cost"] or 0))
def _spent_run(run_id: str) -> Decimal:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(cost_usd),0) AS cost
            FROM search_calls
            WHERE run_id=%s AND status='done'
            """,
            (run_id,),
        ).fetchone()
    return Decimal(str(row["cost"] or 0))


def _create_call(run_id: str, query: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO search_calls(run_id,market,query,engine,model,status)
            VALUES (%s,'amazon',%s,'exa',%s,'running')
            RETURNING id
            """,
            (run_id, query, _model()),
        ).fetchone()
    return int(row["id"])


def _mark_budget_blocked(run_id: str, query: str, reason: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO search_calls(
                run_id,market,query,engine,model,status,error,completed_at
            ) VALUES (%s,'amazon',%s,'exa',%s,'budget_blocked',%s,now())
            """,
            (run_id, query, _model(), reason),
        )
def _normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(product.get("title") or "").strip(),
        "source_url": str(product.get("url") or "").strip(),
        "brand": product.get("brand"),
        "price_text": product.get("price_text", product.get("price")),
        "rating": product.get("rating"),
        "review_count": product.get("review_count", product.get("reviews")),
        "feature_summary": str(
            product.get("feature_summary")
            or product.get("features")
            or product.get("summary")
            or ""
        ).strip(),
        "raw": product,
    }


def _persist_success(*, run_id: str, call_id: int, result) -> int:
    usage = result.usage or {}
    normalized = [_normalize_product(p) for p in result.products]
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
            row = conn.execute(
                """
                INSERT INTO raw_products(
                    run_id,search_call_id,market,title,source_url,brand,price_text,
                    rating,review_count,feature_summary,source_quality,raw_data
                ) VALUES (
                    %s,%s,'amazon',%s,%s,%s,%s,%s,%s,%s,0.80,%s
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
                    run_id,
                    call_id,
                    product["title"],
                    product["source_url"],
                    product["brand"],
                    product["price_text"],
                    product["rating"],
                    product["review_count"],
                    product["feature_summary"],
                    Jsonb(product["raw"]),
                ),
            ).fetchone()
            if row:
                inserted += 1
            conn.execute(
                """
                INSERT INTO source_documents(
                    run_id,search_call_id,market,source_url,title,source_kind,meta
                ) VALUES (%s,%s,'amazon',%s,%s,'marketplace_product',%s)
                ON CONFLICT (run_id,source_url) DO NOTHING
                """,
                (
                    run_id,
                    call_id,
                    product["source_url"],
                    product["title"],
                    Jsonb({"source": "openrouter_web_search"}),
                ),
            )
    return inserted


def _persist_failure(call_id: int, error: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE search_calls
            SET status='failed',error=%s,completed_at=now()
            WHERE id=%s
            """,
            (error[:2000], call_id),
        )
def run_amazon_live_scout(run_id: str, dataset_key: str, user_query: str) -> dict[str, Any]:
    if not _enabled():
        return {
            "enabled": False,
            "status": "disabled",
            "records": 0,
            "queries": 0,
            "cost_usd": 0.0,
        }

    if not _supported_demo_query(dataset_key, user_query):
        return {
            "enabled": False,
            "status": "unsupported_demo",
            "records": 0,
            "queries": 0,
            "cost_usd": 0.0,
        }

    queries = list(AMAZON_QUERIES[dataset_key])[:3]
    completed_calls = 0
    errors: list[str] = []

    for query in queries:
        run_spent = _spent_run(run_id)
        daily_spent = _spent_today()

        if run_spent >= _run_cap():
            _mark_budget_blocked(run_id, query, f"run budget reached: {run_spent}")
            break
        if daily_spent >= _daily_cap():
            _mark_budget_blocked(run_id, query, f"daily budget reached: {daily_spent}")
            break

        call_id = _create_call(run_id, query)
        try:
            result = scout_search(
                query=query,
                market="Amazon",
                allowed_domains=AMAZON_DOMAINS,
                max_results=5,
            )
            _persist_success(run_id=run_id, call_id=call_id, result=result)
            completed_calls += 1
        except OpenRouterError as exc:
            _persist_failure(call_id, str(exc))
            errors.append(str(exc))
        except Exception as exc:
            _persist_failure(call_id, f"{type(exc).__name__}: {exc}")
            errors.append(f"{type(exc).__name__}: {exc}")

    final_cost = _spent_run(run_id)
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS records
            FROM raw_products
            WHERE run_id=%s AND market='amazon'
            """,
            (run_id,),
        ).fetchone()
        total_records = int(row["records"] or 0)
    return {
        "enabled": True,
        "status": "done" if completed_calls else ("failed" if errors else "budget_blocked"),
        "records": total_records,
        "queries": completed_calls,
        "cost_usd": float(final_cost),
        "errors": errors[:3],
    }


def live_evidence(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        calls = conn.execute(
            """
            SELECT id,market,query,engine,model,status,cost_usd,prompt_tokens,
                   completion_tokens,total_tokens,result_count,error,created_at,completed_at
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
            ORDER BY id
            """,
            (run_id,),
        ).fetchall()
    return {"search_calls": calls, "products": products}