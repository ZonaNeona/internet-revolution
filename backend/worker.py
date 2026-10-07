from __future__ import annotations

import time
import traceback

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.fixtures import DATASETS, STAGES, initial_scouts, initial_stats
from backend.market_scout import _model as scout_model, run_live_market_scouts
from backend.supplier_scout import run_live_supplier_probe
from backend.normalizer import build_archetypes, normalize_run

POLL_SECONDS = 0.20
NEXT_STAGE_DELAY = 0.75


def claim_job():
    with connect() as conn:
        job = conn.execute(
            """
            SELECT id,run_id,job_type,stage_index,attempts
            FROM research_jobs
            WHERE status='pending' AND available_at <= now()
            ORDER BY available_at,id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        ).fetchone()
        if not job:
            return None
        conn.execute(
            """
            UPDATE research_jobs
            SET status='running',locked_at=now(),attempts=attempts+1,updated_at=now()
            WHERE id=%s
            """,
            (job["id"],),
        )
        return dict(job)


def stage_state(dataset_key: str, stage_index: int, live_scouts: dict | None = None):
    dataset = DATASETS[dataset_key]
    stats = initial_stats()
    scouts = initial_scouts()

    if stage_index >= 1:
        stats["queries"] = dataset["stats"]["queries"]

    if stage_index >= 2:
        scouts = {
            name: {"status": "done", "source": "fixture", **values}
            for name, values in dataset["scouts"].items()
        }
        for market, live in (live_scouts or {}).items():
            if market in scouts and live.get("enabled"):
                scouts[market].update({
                    "status": live.get("status", "done"),
                    "source": "live",
                    "records": live.get("records", 0),
                    "queries": live.get("queries", 0),
                    "pages": live.get("records", 0),
                    "cost_usd": live.get("cost_usd", 0),
                })

    if stage_index >= 3:
        live_records = sum(
            int(value.get("records", 0) or 0)
            for value in (live_scouts or {}).values()
            if value.get("enabled")
        )
        if live_records:
            stats["pages"] = live_records
            stats["records"] = live_records
        else:
            stats["pages"] = dataset["stats"]["pages"]
            stats["records"] = dataset["stats"]["records"]
    if stage_index >= 4:
        stats["archetypes"] = dataset["stats"]["archetypes"]
    if stage_index >= 5:
        stats["candidates"] = dataset["stats"]["candidates"]
        stats["supplier_matches"] = dataset["stats"]["supplier_matches"]
    return stats, scouts


def live_totals(run_id: str) -> tuple[float, int, int]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(cost_usd),0) AS cost,
                COUNT(*) FILTER (WHERE status IN ('done','failed')) AS calls
            FROM search_calls
            WHERE run_id=%s
            """,
            (run_id,),
        ).fetchone()
        products = conn.execute(
            "SELECT COUNT(*) AS count FROM raw_products WHERE run_id=%s",
            (run_id,),
        ).fetchone()
    return float(row["cost"] or 0), int(row["calls"] or 0), int(products["count"] or 0)


def supplier_totals(run_id: str) -> tuple[float, int, int]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(cost_usd),0) AS cost,
                COUNT(*) FILTER (WHERE status IN ('done','failed')) AS calls
            FROM supplier_search_calls
            WHERE run_id=%s
            """,
            (run_id,),
        ).fetchone()
        offers = conn.execute(
            "SELECT COUNT(*) AS count FROM supplier_offers WHERE run_id=%s",
            (run_id,),
        ).fetchone()
    return float(row["cost"] or 0), int(row["calls"] or 0), int(offers["count"] or 0)


def derived_counts(run_id: str) -> tuple[int, int, int]:
    with connect() as conn:
        normalized = conn.execute(
            "SELECT COUNT(*) AS count FROM normalized_products WHERE run_id=%s",
            (run_id,),
        ).fetchone()
        archetypes = conn.execute(
            "SELECT COUNT(*) AS count FROM product_archetypes WHERE run_id=%s",
            (run_id,),
        ).fetchone()
        opportunities = conn.execute(
            "SELECT COUNT(*) AS count FROM opportunity_scores WHERE run_id=%s",
            (run_id,),
        ).fetchone()
    return (
        int(normalized["count"] or 0),
        int(archetypes["count"] or 0),
        int(opportunities["count"] or 0),
    )


def event_message(dataset_key: str, stage_index: int, live_scouts: dict | None = None) -> str:
    dataset = DATASETS[dataset_key]
    stats = dataset["stats"]
    if stage_index == 2 and live_scouts:
        parts = []
        total_queries = 0
        total_records = 0
        total_cost = 0.0
        for market in ("wb", "ozon", "amazon", "lazada"):
            live = live_scouts.get(market) or {}
            if not live.get("enabled"):
                continue
            queries = int(live.get("queries", 0) or 0)
            records = int(live.get("records", 0) or 0)
            cost = float(live.get("cost_usd", 0) or 0)
            total_queries += queries
            total_records += records
            total_cost += cost
            parts.append(market.upper() + " " + str(records))
        if parts:
            return (
                "collect_markets LIVE → "
                + ", ".join(parts)
                + " · "
                + str(total_queries)
                + " search calls · "
                + str(total_records)
                + " records · USD "
                + format(total_cost, ".4f")
            )

    messages = {
        1: f"expand_queries → {stats['queries']} поисковых гипотез",
        2: "collect_markets → demo sampling",
        3: f"normalize_products → {stats['records']} product records",
        4: f"cluster_archetypes → {stats['archetypes']} товарных архетипов",
        5: f"probe_suppliers → {stats['supplier_matches']} supplier matches",
        6: "calculate_preliminary_economics → TOP-20 пересчитан",
        7: "rank_top_5 → итоговый отчёт готов",
    }
    return messages.get(stage_index, STAGES[stage_index]["message"])


def mark_market_stage_started(run_id: str, stage: dict) -> None:
    scouts = {
        name: {
            "status": "running",
            "source": "live",
            "records": 0,
            "queries": 0,
            "pages": 0,
            "cost_usd": 0,
        }
        for name in ("wb", "ozon", "amazon", "lazada")
    }
    with connect() as conn:
        conn.execute(
            """
            UPDATE research_runs
            SET stage_index=2,stage_key=%s,stage_title=%s,
                stage_description=%s,progress=28,scouts=%s,updated_at=now()
            WHERE id=%s
            """,
            (
                stage["key"],
                stage["title"],
                stage["description"],
                Jsonb(scouts),
                run_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta)
            VALUES (%s,'stage',2,'Hermes','collect_markets → 4 LIVE Market Scouts запущены',%s)
            """,
            (run_id, Jsonb({"stage": stage["key"], "progress": 28})),
        )


def mark_supplier_stage_started(run_id: str, stage: dict) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE research_runs
            SET stage_index=5,stage_key=%s,stage_title=%s,
                stage_description=%s,progress=72,updated_at=now()
            WHERE id=%s
            """,
            (stage["key"], stage["title"], stage["description"], run_id),
        )
        conn.execute(
            """
            INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta)
            VALUES (%s,'stage',5,'Hermes','probe_suppliers → Alibaba + Made-in-China LIVE запущены',%s)
            """,
            (run_id, Jsonb({"stage": stage["key"], "progress": 72})),
        )


def process_job(job: dict):
    rid = str(job["run_id"])
    stage_index = int(job["stage_index"])

    with connect() as conn:
        run = conn.execute(
            "SELECT * FROM research_runs WHERE id=%s",
            (rid,),
        ).fetchone()

    if not run:
        with connect() as conn:
            conn.execute(
                "UPDATE research_jobs SET status='failed',last_error='run missing',updated_at=now() WHERE id=%s",
                (job["id"],),
            )
        return

    if run["status"] in ("completed", "failed", "cancelled"):
        with connect() as conn:
            conn.execute(
                "UPDATE research_jobs SET status='cancelled',updated_at=now() WHERE id=%s",
                (job["id"],),
            )
        return

    dataset_key = run["dataset_key"]
    stage = STAGES[stage_index]
    live_scouts: dict[str, dict] = {}
    supplier_probe: dict[str, object] = {}

    if stage_index == 2:
        mark_market_stage_started(rid, stage)
        try:
            live_scouts = run_live_market_scouts(rid, dataset_key, run["query"])
        except Exception as exc:
            live_scouts = {
                market: {
                    "enabled": True,
                    "status": "failed",
                    "records": 0,
                    "queries": 0,
                    "cost_usd": 0.0,
                    "errors": [f"{type(exc).__name__}: {exc}"],
                }
                for market in ("wb", "ozon", "amazon", "lazada")
            }

    if stage_index == 5:
        mark_supplier_stage_started(rid, stage)
        try:
            supplier_probe = run_live_supplier_probe(rid, dataset_key)
        except Exception as exc:
            supplier_probe = {
                "enabled": True,
                "status": "failed",
                "sources": {},
                "records": 0,
                "cost_usd": 0.0,
                "errors": [f"{type(exc).__name__}: {exc}"],
            }

    market_cost, live_calls, live_records = live_totals(rid)
    supplier_cost, supplier_calls, supplier_records = supplier_totals(rid)
    actual_cost = market_cost + supplier_cost

    derive_meta: dict[str, int] = {}
    if stage_index == 3 and live_records:
        derive_meta = normalize_run(rid, dataset_key)
    elif stage_index == 4 and live_records:
        normalized_count, _, _ = derived_counts(rid)
        if normalized_count == 0:
            normalize_run(rid, dataset_key)
        derive_meta = build_archetypes(rid, dataset_key)

    if stage_index > 2:
        previous_scouts = run.get("scouts") or {}
        for market, prev in previous_scouts.items():
            if prev.get("source") == "live":
                live_scouts[market] = {
                    "enabled": True,
                    "status": prev.get("status", "done"),
                    "records": prev.get("records", 0),
                    "queries": prev.get("queries", 0),
                    "cost_usd": prev.get("cost_usd", 0),
                }

    stats, scouts = stage_state(dataset_key, stage_index, live_scouts)
    normalized_count, archetype_count, opportunity_count = derived_counts(rid)
    if normalized_count:
        stats["records"] = normalized_count
    if archetype_count:
        stats["archetypes"] = archetype_count
    if opportunity_count:
        stats["candidates"] = opportunity_count
    if supplier_records:
        stats["supplier_matches"] = supplier_records

    event_text = event_message(dataset_key, stage_index, live_scouts)
    if stage_index == 3 and normalized_count:
        event_text = (
            "normalize_products LIVE → "
            + str(normalized_count)
            + " relevant records из "
            + str(live_records)
        )
    elif stage_index == 4 and archetype_count:
        event_text = (
            "cluster_archetypes LIVE → "
            + str(archetype_count)
            + " архетипов · "
            + str(opportunity_count)
            + " scored"
        )
    elif stage_index == 5 and supplier_probe.get("enabled"):
        sources = supplier_probe.get("sources") or {}
        source_parts = []
        for source in ("alibaba", "made_in_china"):
            item = sources.get(source) or {}
            if item.get("enabled"):
                source_parts.append(source + " " + str(item.get("records", 0)))
        event_text = (
            "probe_suppliers LIVE → "
            + ", ".join(source_parts)
            + " · "
            + str(supplier_calls)
            + " search calls · "
            + str(supplier_records)
            + " offers · USD "
            + format(supplier_cost, ".4f")
        )

    completed = stage_index == len(STAGES) - 1

    with connect() as conn:
        conn.execute(
            """
            UPDATE research_runs
            SET status=%s,stage_index=%s,stage_key=%s,stage_title=%s,
                stage_description=%s,progress=%s,
                estimated_cost_usd=%s,actual_cost_usd=%s,
                live_search_calls=%s,live_records=%s,
                stats=%s,scouts=%s,result_summary=%s,
                completed_at=CASE WHEN %s THEN now() ELSE completed_at END,
                updated_at=now(),error=NULL
            WHERE id=%s
            """,
            (
                "completed" if completed else "running",
                stage_index,
                stage["key"],
                stage["title"],
                stage["description"],
                stage["progress"],
                actual_cost,
                actual_cost,
                live_calls,
                live_records,
                Jsonb(stats),
                Jsonb(scouts),
                Jsonb({
                    "ready": completed,
                    "dataset_key": dataset_key,
                    "live_markets": [
                        market for market, value in live_scouts.items()
                        if value.get("enabled")
                    ],
                    "live_supplier": bool(supplier_probe.get("enabled") or supplier_records),
                    "supplier_records": supplier_records,
                }),
                completed,
                rid,
            ),
        )
        conn.execute(
            """
            INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta)
            VALUES (%s,'stage',%s,'Hermes',%s,%s)
            """,
            (
                rid,
                stage_index,
                event_text,
                Jsonb({
                    "stage": stage["key"],
                    "progress": stage["progress"],
                    "actual_cost_usd": actual_cost,
                    "live_search_calls": live_calls,
                    "live_records": live_records,
                    "supplier_cost_usd": supplier_cost,
                    "supplier_search_calls": supplier_calls,
                    "supplier_records": supplier_records,
                }),
            ),
        )
        conn.execute(
            "UPDATE research_jobs SET status='done',updated_at=now() WHERE id=%s",
            (job["id"],),
        )

        if not completed:
            conn.execute(
                """
                INSERT INTO research_jobs(run_id,job_type,stage_index,status,payload,available_at)
                VALUES (%s,'advance_research',%s,'pending',%s,now() + (%s * interval '1 second'))
                """,
                (rid, stage_index + 1, Jsonb({}), NEXT_STAGE_DELAY),
            )
        else:
            conn.execute(
                """
                INSERT INTO audit_log(run_id,action,actor,details)
                VALUES (%s,'research_completed','worker',%s)
                """,
                (rid, Jsonb({
                    "dataset_key": dataset_key,
                    "actual_cost_usd": actual_cost,
                    "live_search_calls": live_calls,
                    "live_records": live_records,
                    "supplier_cost_usd": supplier_cost,
                    "supplier_search_calls": supplier_calls,
                    "supplier_records": supplier_records,
                })),
            )


def fail_job(job: dict, exc: Exception):
    error = f"{type(exc).__name__}: {exc}"
    attempts = int(job.get("attempts") or 0) + 1
    with connect() as conn:
        if attempts < 3:
            conn.execute(
                """
                UPDATE research_jobs
                SET status='pending',last_error=%s,available_at=now()+interval '3 seconds',
                    updated_at=now()
                WHERE id=%s
                """,
                (error, job["id"]),
            )
        else:
            conn.execute(
                "UPDATE research_jobs SET status='failed',last_error=%s,updated_at=now() WHERE id=%s",
                (error, job["id"]),
            )
            conn.execute(
                """
                UPDATE research_runs
                SET status='failed',error=%s,updated_at=now()
                WHERE id=%s
                """,
                (error, str(job["run_id"])),
            )
            conn.execute(
                """
                INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta)
                VALUES (%s,'error',%s,'worker',%s,%s)
                """,
                (
                    str(job["run_id"]),
                    job["stage_index"],
                    "Worker остановил research run после повторных ошибок",
                    Jsonb({"error": error}),
                ),
            )


def recover_stale_jobs():
    # Single-worker deployment: every RUNNING job/call found on startup
    # belongs to the dead predecessor.
    with connect() as conn:
        conn.execute(
            """
            UPDATE research_jobs
            SET status='pending',available_at=now(),locked_at=NULL,updated_at=now(),
                last_error=CASE
                    WHEN COALESCE(last_error,'') = '' THEN '[recovered worker restart]'
                    ELSE last_error || ' [recovered worker restart]'
                END
            WHERE status='running'
            """
        )
        conn.execute(
            """
            UPDATE search_calls
            SET status='failed',completed_at=now(),
                error=CASE
                    WHEN COALESCE(error,'') = '' THEN '[interrupted by worker restart]'
                    ELSE error || ' [interrupted by worker restart]'
                END
            WHERE status='running'
            """
        )
        conn.execute(
            """
            UPDATE supplier_search_calls
            SET status='failed',completed_at=now(),
                error=CASE
                    WHEN COALESCE(error,'') = '' THEN '[interrupted by worker restart]'
                    ELSE error || ' [interrupted by worker restart]'
                END
            WHERE status='running'
            """
        )


def main():
    recover_stale_jobs()
    print("Product Hunter worker started; scout_model=" + scout_model(), flush=True)
    while True:
        job = None
        try:
            job = claim_job()
            if not job:
                time.sleep(POLL_SECONDS)
                continue
            process_job(job)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            traceback.print_exc()
            if job:
                try:
                    fail_job(job, exc)
                except Exception:
                    traceback.print_exc()
            time.sleep(0.5)


if __name__ == "__main__":
    main()