from __future__ import annotations

import time
import traceback

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.fixtures import DATASETS, STAGES, initial_scouts, initial_stats

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


def stage_state(dataset_key: str, stage_index: int):
    dataset = DATASETS[dataset_key]
    stats = initial_stats()
    scouts = initial_scouts()

    if stage_index >= 1:
        stats["queries"] = dataset["stats"]["queries"]
    if stage_index >= 2:
        scouts = {
            name: {"status": "done", **values}
            for name, values in dataset["scouts"].items()
        }
    if stage_index >= 3:
        stats["pages"] = dataset["stats"]["pages"]
        stats["records"] = dataset["stats"]["records"]
    if stage_index >= 4:
        stats["archetypes"] = dataset["stats"]["archetypes"]
    if stage_index >= 5:
        stats["candidates"] = dataset["stats"]["candidates"]
        stats["supplier_matches"] = dataset["stats"]["supplier_matches"]
    if stage_index >= 6:
        stats["candidates"] = dataset["stats"]["candidates"]
        stats["supplier_matches"] = dataset["stats"]["supplier_matches"]
    if stage_index >= 7:
        stats = dict(dataset["stats"])

    return stats, scouts


def event_message(dataset_key: str, stage_index: int) -> str:
    dataset = DATASETS[dataset_key]
    stats = dataset["stats"]
    messages = {
        1: f"expand_queries → {stats['queries']} поисковых гипотез",
        2: "collect_markets → 4 scouts завершили demo sampling",
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
            "SELECT * FROM research_runs WHERE id=%s FOR UPDATE",
            (rid,),
        ).fetchone()
        if not run:
            conn.execute(
                "UPDATE research_jobs SET status='failed',last_error='run missing',updated_at=now() WHERE id=%s",
                (job["id"],),
            )
            return
        if run["status"] in ("completed", "failed", "cancelled"):
            conn.execute(
                "UPDATE research_jobs SET status='cancelled',updated_at=now() WHERE id=%s",
                (job["id"],),
            )
            return

        dataset_key = run["dataset_key"]
        dataset = DATASETS[dataset_key]
        stage = STAGES[stage_index]
        stats, scouts = stage_state(dataset_key, stage_index)
        cost = round(float(dataset["cost"]) * (stage["progress"] / 100.0), 4)
        completed = stage_index == len(STAGES) - 1

        conn.execute(
            """
            UPDATE research_runs
            SET status=%s,stage_index=%s,stage_key=%s,stage_title=%s,
                stage_description=%s,progress=%s,estimated_cost_usd=%s,
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
                cost,
                Jsonb(stats),
                Jsonb(scouts),
                Jsonb({"ready": completed, "dataset_key": dataset_key}),
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
                event_message(dataset_key, stage_index),
                Jsonb({"stage": stage["key"], "progress": stage["progress"]}),
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
                (rid, Jsonb({"dataset_key": dataset_key, "cost_usd": cost})),
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
    with connect() as conn:
        conn.execute(
            """
            UPDATE research_jobs
            SET status='pending',available_at=now(),updated_at=now(),
                last_error=COALESCE(last_error,'') || ' [recovered stale lock]'
            WHERE status='running'
              AND locked_at < now() - interval '2 minutes'
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