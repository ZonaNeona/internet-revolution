from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect


def _supplier_score(run_id: str, archetype_id: int) -> tuple[float, dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS offers,
                   COUNT(DISTINCT source) AS sources,
                   COUNT(*) FILTER (WHERE price_text IS NOT NULL) AS priced
            FROM supplier_offers
            WHERE run_id=%s AND archetype_id=%s
            """,
            (run_id, archetype_id),
        ).fetchone()

    offers = int(row["offers"] or 0)
    sources = int(row["sources"] or 0)
    priced = int(row["priced"] or 0)
    score = min(
        100.0,
        min(40.0, sources * 20.0)
        + min(40.0, offers * 5.0)
        + min(20.0, priced * 5.0),
    )
    return round(score, 2), {
        "offers": offers,
        "sources": sources,
        "priced": priced,
    }


def _economics_score(
    run_id: str,
    archetype_id: int,
) -> tuple[float | None, dict[str, Any]]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT status,contribution_margin_min,contribution_margin_max,
                   retail_evidence_count,supplier_evidence_count
            FROM economics_scenarios
            WHERE run_id=%s AND archetype_id=%s
            """,
            (run_id, archetype_id),
        ).fetchone()

    if not row:
        return 35.0, {"status": "missing"}

    status = row["status"]
    margin_min = (
        float(row["contribution_margin_min"])
        if row["contribution_margin_min"] is not None
        else None
    )
    margin_max = (
        float(row["contribution_margin_max"])
        if row["contribution_margin_max"] is not None
        else None
    )

    if status not in ("ready", "partial") or margin_min is None:
        return 35.0, {
            "status": status,
            "margin_min": margin_min,
            "margin_max": margin_max,
            "retail_evidence_count": int(row["retail_evidence_count"] or 0),
            "supplier_evidence_count": int(row["supplier_evidence_count"] or 0),
        }

    # Rank on the conservative side of the range, not the midpoint.
    score = max(0.0, min(100.0, 40.0 + 2.0 * margin_min))
    if status == "partial":
        score *= 0.90

    return round(score, 2), {
        "status": status,
        "margin_min": margin_min,
        "margin_max": margin_max,
        "retail_evidence_count": int(row["retail_evidence_count"] or 0),
        "supplier_evidence_count": int(row["supplier_evidence_count"] or 0),
    }


def _decision(
    final_score: float,
    supplier: dict[str, Any],
    economics: dict[str, Any],
) -> str:
    status = economics.get("status")
    margin_min = economics.get("margin_min")
    margin_max = economics.get("margin_max")
    offers = int(supplier.get("offers") or 0)

    if offers == 0:
        return "NEEDS_DATA"

    if status not in ("ready", "partial"):
        return "NEEDS_DATA" if final_score >= 45 else "NO-GO"

    if margin_max is not None and margin_max < 0:
        return "NO-GO"

    if margin_min is not None and margin_min >= 20 and final_score >= 70:
        return "TEST"

    if margin_max is not None and margin_max >= 10 and final_score >= 60:
        return "WATCH"

    return "NO-GO"


def rank_final_opportunities(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT os.id,os.archetype_id,os.opportunity_score,
                   pa.label,pa.member_count
            FROM opportunity_scores os
            JOIN product_archetypes pa ON pa.id=os.archetype_id
            WHERE os.run_id=%s
            ORDER BY os.opportunity_score DESC,pa.member_count DESC
            """,
            (run_id,),
        ).fetchall()

    ranked: list[dict[str, Any]] = []
    for row in rows:
        market_score = float(row["opportunity_score"] or 0)
        supplier_score, supplier_meta = _supplier_score(
            run_id, int(row["archetype_id"])
        )
        economics_score, economics_meta = _economics_score(
            run_id, int(row["archetype_id"])
        )

        final_score = (
            0.80 * market_score
            + 0.10 * supplier_score
            + 0.10 * economics_score
        )
        weights = {
            "market": 0.80,
            "supplier": 0.10,
            "economics": 0.10,
        }

        final_score = round(max(0.0, min(100.0, final_score)), 2)
        decision = _decision(final_score, supplier_meta, economics_meta)

        explanation = {
            "version": "final_rank_v1",
            "weights": weights,
            "market_score": market_score,
            "supplier": supplier_meta,
            "economics": economics_meta,
            "decision_rule": (
                "no supplier/economics evidence => NEEDS_DATA; "
                "negative optimistic margin => NO-GO; "
                "TEST requires sufficient economics and >=20% conservative margin"
            ),
        }

        with connect() as conn:
            conn.execute(
                """
                UPDATE opportunity_scores
                SET market_score=%s,
                    supplier_availability_score=%s,
                    economics_score=%s,
                    final_score=%s,
                    decision=%s,
                    final_explanation=%s
                WHERE id=%s
                """,
                (
                    market_score,
                    supplier_score,
                    economics_score,
                    final_score,
                    decision,
                    Jsonb(explanation),
                    row["id"],
                ),
            )

        ranked.append({
            "archetype_id": int(row["archetype_id"]),
            "label": row["label"],
            "market_score": market_score,
            "supplier_availability_score": supplier_score,
            "economics_score": economics_score,
            "final_score": final_score,
            "decision": decision,
            "explanation": explanation,
        })

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return {
        "count": len(ranked),
        "items": ranked,
        "top": ranked[0] if ranked else None,
        "version": "final_rank_v1",
    }