from __future__ import annotations

import re
import statistics
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect

ASSUMPTIONS = {
    "version": "economics_v1",
    "fx_usd_rub": 95.0,
    "fx_kind": "modelled_assumption_not_live_rate",
    "marketplace_fee_pct": 18.0,
    "ad_spend_pct": 12.0,
    "returns_pct": 3.0,
    "tax_pct": 6.0,
    "duty_pct": 10.0,
    "logistics_rub": {
        "vacuum": 450.0,
        "bath": 180.0,
        "led": 120.0,
    },
}


def _numbers(text: str) -> list[float]:
    values: list[float] = []
    for raw in re.findall(r"\d[\d\s]*(?:[.,]\d+)?", text or ""):
        cleaned = raw.replace(" ", "").replace(",", ".")
        try:
            values.append(float(cleaned))
        except ValueError:
            continue
    return values


def _parse_rub_price(text: str | None) -> tuple[float, float] | None:
    if not text:
        return None
    low = text.casefold()
    if "₽" not in text and "руб" not in low:
        return None
    if "тг" in low or "$" in text or "usd" in low:
        return None
    values = _numbers(text)
    if not values:
        return None
    if len(values) == 1:
        return values[0], values[0]
    return min(values[:2]), max(values[:2])


def _parse_supplier_usd(
    price_text: str | None,
    moq_text: str | None,
    dataset_key: str,
) -> tuple[float, float] | None:
    if not price_text:
        return None
    low = price_text.casefold()
    if "$" not in price_text and "usd" not in low:
        return None

    moq = (moq_text or "").casefold()
    ambiguous_units = ("meter", "metre", "метр", "kg", "кг")
    if any(unit in low for unit in ambiguous_units):
        return None
    if dataset_key == "led" and any(unit in moq for unit in ambiguous_units):
        return None

    values = _numbers(price_text.replace("US$", "$"))
    if not values:
        return None
    if len(values) == 1:
        result = (values[0], values[0])
    else:
        result = (min(values[:2]), max(values[:2]))

    lo, hi = result
    if lo <= 0 or hi <= 0 or hi > 10000:
        return None
    return result
def _robust_values(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values
    med = statistics.median(values)
    if med <= 0:
        return values
    lower = med * 0.35
    upper = med * 2.8
    filtered = [value for value in values if lower <= value <= upper]
    return filtered or values


def _top_archetype(
    run_id: str,
    archetype_id: int | None = None,
) -> dict[str, Any] | None:
    with connect() as conn:
        if archetype_id is not None:
            return conn.execute(
                """
                SELECT pa.id,pa.archetype_key,pa.label
                FROM opportunity_scores os
                JOIN product_archetypes pa ON pa.id=os.archetype_id
                WHERE os.run_id=%s AND pa.id=%s
                LIMIT 1
                """,
                (run_id, archetype_id),
            ).fetchone()
        return conn.execute(
            """
            SELECT pa.id,pa.archetype_key,pa.label
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s
            ORDER BY COALESCE(os.final_score,os.opportunity_score) DESC,
                     os.opportunity_score DESC,pa.member_count DESC
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()


def _retail_evidence(run_id: str, archetype_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT np.market,rp.price_text,np.canonical_title,rp.source_url
            FROM archetype_members am
            JOIN normalized_products np ON np.id=am.normalized_product_id
            JOIN raw_products rp ON rp.id=np.raw_product_id
            WHERE am.archetype_id=%s
              AND np.run_id=%s
              AND np.market IN ('wb','ozon')
              AND rp.price_text IS NOT NULL
            ORDER BY np.market,np.id
            """,
            (archetype_id, run_id),
        ).fetchall()


def _supplier_evidence(
    run_id: str,
    archetype_id: int,
) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT source,price_text,moq_text,product_title,source_url
            FROM supplier_offers
            WHERE run_id=%s
              AND archetype_id=%s
              AND price_text IS NOT NULL
            ORDER BY source,id
            """,
            (run_id, archetype_id),
        ).fetchall()
def calculate_preliminary_economics(
    run_id: str,
    dataset_key: str,
    archetype_id: int | None = None,
) -> dict[str, Any]:
    top = _top_archetype(run_id, archetype_id)
    if not top:
        return {
            "status": "insufficient_data",
            "reason": "No scored archetype is available.",
        }

    retail_rows = _retail_evidence(run_id, int(top["id"]))
    supplier_rows = _supplier_evidence(run_id, int(top["id"]))

    retail_parsed: list[tuple[float, float, dict[str, Any]]] = []
    for row in retail_rows:
        parsed = _parse_rub_price(row["price_text"])
        if parsed:
            retail_parsed.append((parsed[0], parsed[1], row))

    supplier_parsed: list[tuple[float, float, dict[str, Any]]] = []
    for row in supplier_rows:
        parsed = _parse_supplier_usd(
            row["price_text"],
            row["moq_text"],
            dataset_key,
        )
        if parsed:
            supplier_parsed.append((parsed[0], parsed[1], row))

    retail_values = _robust_values([
        (lo + hi) / 2 for lo, hi, _ in retail_parsed
    ])
    supplier_lows = _robust_values([lo for lo, _, _ in supplier_parsed])
    supplier_highs = _robust_values([hi for _, hi, _ in supplier_parsed])

    retail_min = min(retail_values) if retail_values else None
    retail_max = max(retail_values) if retail_values else None
    supplier_min = statistics.median(supplier_lows) if supplier_lows else None
    supplier_max = statistics.median(supplier_highs) if supplier_highs else None
    if (
        supplier_min is not None
        and supplier_max is not None
        and supplier_min > supplier_max
    ):
        supplier_min, supplier_max = supplier_max, supplier_min

    status = "insufficient_data"
    if retail_min is not None and supplier_min is not None:
        status = "ready" if len(retail_values) >= 2 and len(supplier_lows) >= 2 else "partial"

    landed_min = landed_max = None
    margin_min = margin_max = None

    if status in ("ready", "partial"):
        fx = float(ASSUMPTIONS["fx_usd_rub"])
        duty = float(ASSUMPTIONS["duty_pct"]) / 100
        logistics = float(ASSUMPTIONS["logistics_rub"][dataset_key])
        variable_pct = sum(
            float(ASSUMPTIONS[key]) / 100
            for key in (
                "marketplace_fee_pct",
                "ad_spend_pct",
                "returns_pct",
                "tax_pct",
            )
        )
        landed_min = supplier_min * fx * (1 + duty) + logistics
        landed_max = supplier_max * fx * (1 + duty) + logistics

        optimistic_profit = retail_max - landed_min - retail_max * variable_pct
        conservative_profit = retail_min - landed_max - retail_min * variable_pct
        margin_max = 100 * optimistic_profit / retail_max
        margin_min = 100 * conservative_profit / retail_min
    notes: dict[str, Any] = {
        "retail_candidates": len(retail_rows),
        "retail_usable": len(retail_values),
        "supplier_candidates": len(supplier_rows),
        "supplier_usable": len(supplier_lows),
    }

    if not retail_values:
        notes["retail_issue"] = "No comparable RUB retail price for this archetype."
    if not supplier_lows:
        if dataset_key == "led":
            notes["supplier_issue"] = (
                "Supplier prices use ambiguous length units; V1 refuses to compare them "
                "with retail strip kits."
            )
        else:
            notes["supplier_issue"] = "No comparable USD supplier unit price."

    retail_evidence = [
        {
            "market": row["market"],
            "price_text": row["price_text"],
            "title": row["canonical_title"],
            "url": row["source_url"],
        }
        for _, _, row in retail_parsed
    ]
    supplier_evidence = [
        {
            "source": row["source"],
            "price_text": row["price_text"],
            "moq_text": row["moq_text"],
            "title": row["product_title"],
            "url": row["source_url"],
        }
        for _, _, row in supplier_parsed
    ]

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO economics_scenarios(
                run_id,archetype_id,status,currency,
                retail_price_min,retail_price_max,retail_evidence_count,
                supplier_price_min_usd,supplier_price_max_usd,supplier_evidence_count,
                landed_cost_min_rub,landed_cost_max_rub,
                contribution_margin_min,contribution_margin_max,
                assumptions,evidence,notes,updated_at
            ) VALUES (
                %s,%s,%s,'RUB',
                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,now()
            )
            ON CONFLICT (run_id,archetype_id) DO UPDATE SET
                status=EXCLUDED.status,
                retail_price_min=EXCLUDED.retail_price_min,
                retail_price_max=EXCLUDED.retail_price_max,
                retail_evidence_count=EXCLUDED.retail_evidence_count,
                supplier_price_min_usd=EXCLUDED.supplier_price_min_usd,
                supplier_price_max_usd=EXCLUDED.supplier_price_max_usd,
                supplier_evidence_count=EXCLUDED.supplier_evidence_count,
                landed_cost_min_rub=EXCLUDED.landed_cost_min_rub,
                landed_cost_max_rub=EXCLUDED.landed_cost_max_rub,
                contribution_margin_min=EXCLUDED.contribution_margin_min,
                contribution_margin_max=EXCLUDED.contribution_margin_max,
                assumptions=EXCLUDED.assumptions,
                evidence=EXCLUDED.evidence,
                notes=EXCLUDED.notes,
                updated_at=now()
            """,
            (
                run_id,
                top["id"],
                status,
                retail_min,
                retail_max,
                len(retail_values),
                supplier_min,
                supplier_max,
                len(supplier_lows),
                landed_min,
                landed_max,
                margin_min,
                margin_max,
                Jsonb(ASSUMPTIONS),
                Jsonb({
                    "retail": retail_evidence,
                    "suppliers": supplier_evidence,
                }),
                Jsonb(notes),
            ),
        )

    return {
        "status": status,
        "archetype_id": int(top["id"]),
        "archetype_key": top["archetype_key"],
        "label": top["label"],
        "retail_price_min": retail_min,
        "retail_price_max": retail_max,
        "supplier_price_min_usd": supplier_min,
        "supplier_price_max_usd": supplier_max,
        "landed_cost_min_rub": landed_min,
        "landed_cost_max_rub": landed_max,
        "contribution_margin_min": margin_min,
        "contribution_margin_max": margin_max,
        "assumptions": ASSUMPTIONS,
        "notes": notes,
    }
def get_economics(run_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        return conn.execute(
            """
            SELECT es.*,pa.archetype_key,pa.label
            FROM economics_scenarios es
            JOIN product_archetypes pa ON pa.id=es.archetype_id
            WHERE es.run_id=%s
            ORDER BY es.id
            """,
            (run_id,),
        ).fetchall()

def calculate_all_preliminary_economics(
    run_id: str,
    dataset_key: str,
    limit: int = 5,
) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT pa.id
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s
            ORDER BY COALESCE(os.final_score,os.opportunity_score) DESC,
                     os.opportunity_score DESC,
                     pa.member_count DESC
            LIMIT %s
            """,
            (run_id, limit),
        ).fetchall()

    items = [
        calculate_preliminary_economics(
            run_id,
            dataset_key,
            int(row["id"]),
        )
        for row in rows
    ]

    return {
        "count": len(items),
        "ready": sum(1 for item in items if item.get("status") == "ready"),
        "partial": sum(1 for item in items if item.get("status") == "partial"),
        "insufficient": sum(
            1 for item in items if item.get("status") == "insufficient_data"
        ),
        "items": items,
    }
