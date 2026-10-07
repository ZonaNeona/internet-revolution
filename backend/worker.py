from __future__ import annotations

import time
import traceback

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.fixtures import DATASETS, STAGES, initial_scouts, initial_stats
from backend.market_scout import run_amazon_live_scout

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


def stage_state(dataset_key: str, stage_index: int, live_amazon: dict | None = None):
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
        if live_amazon and live_amazon.get("enabled"):
            scouts["amazon"].update({
                "status": live_amazon.get("status", "done"),
                "source": "live",
                "records": live_amazon.get("records", 0),
                "queries": live_amazon.get("queries", 0),
                "pages": live_amazon.get("records", 0),
                "cost_usd": live_amazon.get("cost_usd", 0),
            })

    if stage_index >= 3:
        stats["pages"] = dataset["stats"]["pages"]
        stats["records"] = dataset["stats"]["records"]
    if stage_index >= 4:
        stats["archetypes"] = dataset["stats"]["archetypes"]
    if stage_index >= 5:
        stats["candidates"] = dataset["stats"]["candidates"]
        stats["supplier_matches"] = dataset["stats"]["supplier_matches"]
    if stage_index >= 7:
        stats = dict(dataset["stats"])

    return stats, scouts


def live_totals(run_id: str) -> tuple[float, int, int]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(cost_usd) FILTER (WHERE status='done'),0) AS cost,
                COUNT(*) FILTER (WHERE status='done') AS calls
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


def event_message(dataset_key: str, stage_index: int, live_amazon: dict | None = None) -> str:
    dataset = DATASETS[dataset_key]
    stats = dataset["stats"]
    if stage_index == 2 and live_amazon and live_amazon.get("enabled"):
        if live_amazon.get("status") == "done":
            return (
                "collect_markets → Amazon LIVE: "
                + str(live_amazon.get("queries", 0))
                + " search calls, "
                + str(live_amazon.get("records", 0))
                + " records, USD "
                + format(float(live_amazon.get("cost_usd", 0)), ".4f")
            )
        return "collect_markets → Amazon LIVE fallback: " + str(live_amazon.get("status"))

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
    live_amazon = None

    if stage_index == 2:
        try:
            live_amazon = run_amazon_live_scout(rid, dataset_key, run["query"])
        except Exception as exc:
            live_amazon = {
                "enabled": True,
                "status": "failed",
                "records": 0,
                "queries": 0,
                "cost_usd": live_totals(rid)[0],
                "errors": [f"{type(exc).__name__}: {exc}"],
            }

    actual_cost, live_calls, live_records = live_totals(rid)

    if stage_index > 2:
        previous_scouts = run.get("scouts") or {}
        prev_amazon = previous_scouts.get("amazon") or {}
        if prev_amazon.get("source") == "live":
            live_amazon = {
                "enabled": True,
                "status": prev_amazon.get("status", "done"),
                "records": prev_amazon.get("records", live_records),
                "queries": prev_amazon.get("queries", live_calls),
                "cost_usd": prev_amazon.get("cost_usd", actual_cost),
            }

    stats, scouts = stage_state(dataset_key, stage_index, live_amazon)
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
                    "live_amazon": bool(live_amazon and live_amazon.get("enabled")),
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
                event_message(dataset_key, stage_index, live_amazon),
                Jsonb({
                    "stage": stage["key"],
                    "progress": stage["progress"],
                    "actual_cost_usd": actual_cost,
                    "live_search_calls": live_calls,
                    "live_records": live_records,
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
    # Single-worker deployment: every RUNNING job found on startup
    # belongs to the dead predecessor and can be retried immediately.
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


def main():
    recover_stale_jobs()
    print("Product Hunter worker started", flush=True)
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