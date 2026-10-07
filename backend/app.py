from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb

from .db import connect
from .fixtures import DATASETS, STAGES, dataset_key_for, initial_scouts, initial_stats
from .market_scout import live_evidence
from .normalizer import get_live_opportunities
from .supplier_scout import supplier_evidence

app = FastAPI(title="Product Hunter API", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)


class ResearchCreate(BaseModel):
    query: str = Field(min_length=2, max_length=240)


def _public_run(row: dict, events: list[dict] | None = None) -> dict:
    if not row:
        raise HTTPException(status_code=404, detail="Research run not found")
    item = dict(row)
    for key in (
        "budget_usd",
        "estimated_cost_usd",
        "actual_cost_usd",
        "supplier_actual_cost_usd",
    ):
        if isinstance(item.get(key), Decimal):
            item[key] = float(item[key])
    if events is not None:
        item["events"] = events
    return jsonable_encoder(item)


def _get_events(conn, run_id: str, limit: int = 60) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id,event_type,stage_index,actor,message,meta,created_at
        FROM research_events
        WHERE run_id=%s
        ORDER BY id ASC
        LIMIT %s
        """,
        (run_id, limit),
    ).fetchall()
    return rows


def _get_run(conn, run_id: str) -> dict | None:
    return conn.execute(
        "SELECT * FROM research_runs WHERE id=%s",
        (run_id,),
    ).fetchone()


@app.get("/api/health")
def health():
    with connect() as conn:
        row = conn.execute("SELECT now() AS db_time").fetchone()
    return {"ok": True, "service": "product-hunter-api", "db_time": row["db_time"]}


@app.get("/api/research")
def list_research(limit: int = Query(default=10, ge=1, le=50)):
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id,query,dataset_key,status,stage_index,stage_key,stage_title,
                   progress,estimated_cost_usd,actual_cost_usd,
                   live_search_calls,live_records,
                   supplier_actual_cost_usd,supplier_search_calls,supplier_records,
                   created_at,updated_at,completed_at
            FROM research_runs
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return {"items": [_public_run(row) for row in rows]}


@app.post("/api/research", status_code=201)
def create_research(payload: ResearchCreate):
    query = payload.query.strip()
    dataset_key = dataset_key_for(query)
    run_id = str(uuid.uuid4())
    stage = STAGES[0]
    now = datetime.now(timezone.utc)

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO research_runs (
                id,query,dataset_key,status,stage_index,stage_key,stage_title,
                stage_description,progress,budget_usd,estimated_cost_usd,
                stats,scouts,result_summary,created_at,updated_at
            ) VALUES (
                %s,%s,%s,'running',0,%s,%s,%s,%s,1.50,0,
                %s,%s,%s,%s,%s
            )
            """,
            (
                run_id,
                query,
                dataset_key,
                stage["key"],
                stage["title"],
                stage["description"],
                stage["progress"],
                Jsonb(initial_stats()),
                Jsonb(initial_scouts()),
                Jsonb({"ready": False}),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta)
            VALUES (%s,'stage',0,'Hermes',%s,%s)
            """,
            (run_id, f"Research run создан: {query}", Jsonb({"stage": stage["key"]})),
        )
        conn.execute(
            """
            INSERT INTO research_jobs(run_id,job_type,stage_index,status,payload,available_at)
            VALUES (%s,'advance_research',1,'pending',%s,now() + interval '650 milliseconds')
            """,
            (run_id, Jsonb({})),
        )
        conn.execute(
            """
            INSERT INTO audit_log(run_id,action,actor,details)
            VALUES (%s,'research_created','web',%s)
            """,
            (run_id, Jsonb({"query": query, "dataset_key": dataset_key})),
        )
        row = _get_run(conn, run_id)
        events = _get_events(conn, run_id)
    return _public_run(row, events)


@app.get("/api/research/{run_id}")
def get_research(run_id: uuid.UUID):
    with connect() as conn:
        row = _get_run(conn, str(run_id))
        events = _get_events(conn, str(run_id))
    return _public_run(row, events)


@app.get("/api/research/{run_id}/live-opportunities")
def get_research_live_opportunities(
    run_id: uuid.UUID,
    limit: int = Query(default=5, ge=1, le=20),
):
    rid = str(run_id)
    with connect() as conn:
        if not _get_run(conn, rid):
            raise HTTPException(status_code=404, detail="Research run not found")
        total = conn.execute(
            "SELECT COUNT(*) AS count FROM opportunity_scores WHERE run_id=%s",
            (rid,),
        ).fetchone()
    return {
        "count": int(total["count"] or 0),
        "items": jsonable_encoder(get_live_opportunities(rid, limit)),
    }


@app.get("/api/research/{run_id}/live-evidence")
def get_live_evidence(run_id: uuid.UUID):
    rid = str(run_id)
    with connect() as conn:
        if not _get_run(conn, rid):
            raise HTTPException(status_code=404, detail="Research run not found")
    return jsonable_encoder(live_evidence(rid))


@app.get("/api/research/{run_id}/supplier-evidence")
def get_supplier_evidence(run_id: uuid.UUID):
    rid = str(run_id)
    with connect() as conn:
        if not _get_run(conn, rid):
            raise HTTPException(status_code=404, detail="Research run not found")
    return jsonable_encoder(supplier_evidence(rid))


@app.get("/api/research/{run_id}/events")
def get_events(run_id: uuid.UUID, limit: int = Query(default=60, ge=1, le=200)):
    with connect() as conn:
        if not _get_run(conn, str(run_id)):
            raise HTTPException(status_code=404, detail="Research run not found")
        events = _get_events(conn, str(run_id), limit)
    return {"items": jsonable_encoder(events)}


@app.post("/api/research/{run_id}/skip")
def skip_research(run_id: uuid.UUID):
    rid = str(run_id)
    with connect() as conn:
        run = _get_run(conn, rid)
        if not run:
            raise HTTPException(status_code=404, detail="Research run not found")
        dataset = DATASETS[run["dataset_key"]]
        final_stats = dict(dataset["stats"])
        final_scouts = {
            name: {"status": "done", "source": "fixture", **values}
            for name, values in dataset["scouts"].items()
        }
        current_scouts = run.get("scouts") or {}
        for market, value in current_scouts.items():
            if market in final_scouts and (value or {}).get("source") == "live":
                final_scouts[market] = value
        actual_cost = float(run.get("actual_cost_usd") or 0)
        final_stage = STAGES[-1]
        conn.execute(
            """
            UPDATE research_runs
            SET status='completed',stage_index=%s,stage_key=%s,stage_title=%s,
                stage_description=%s,progress=100,estimated_cost_usd=%s,
                actual_cost_usd=%s,
                stats=%s,scouts=%s,result_summary=%s,
                completed_at=now(),updated_at=now(),error=NULL
            WHERE id=%s
            """,
            (
                len(STAGES) - 1,
                final_stage["key"],
                final_stage["title"],
                final_stage["description"],
                actual_cost,
                actual_cost,
                Jsonb(final_stats),
                Jsonb(final_scouts),
                Jsonb({"ready": True, "dataset_key": run["dataset_key"]}),
                rid,
            ),
        )
        conn.execute(
            """
            UPDATE research_jobs
            SET status='cancelled',updated_at=now()
            WHERE run_id=%s AND status IN ('pending','running')
            """,
            (rid,),
        )
        conn.execute(
            """
            INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta)
            VALUES (%s,'stage',%s,'Hermes','Demo run завершён досрочно',%s)
            """,
            (rid, len(STAGES) - 1, Jsonb({"skipped": True})),
        )
        conn.execute(
            """
            INSERT INTO audit_log(run_id,action,actor,details)
            VALUES (%s,'research_skipped','web',%s)
            """,
            (rid, Jsonb({"reason": "demo_skip"})),
        )
        row = _get_run(conn, rid)
        events = _get_events(conn, rid)
    return _public_run(row, events)