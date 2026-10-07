import uuid
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ConfigDict, field_validator
from psycopg.types.json import Jsonb
from backend.db import connect
from backend.fixtures import dataset_key_for, initial_stats
from backend.marketplaces import ACTIVE, catalogue
from backend.normalizer import get_live_opportunities
from backend.market_scout import live_evidence
from backend.supplier_scout import supplier_evidence
from backend.supplier_review import shortlist
from backend import economics_v2

app=FastAPI(title='Product Hunter API',version='2.0.0',docs_url='/api/docs',openapi_url='/api/openapi.json',redoc_url=None)

class ResearchCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query: str=Field(min_length=2,max_length=240)
    analysis_mode: Literal['category','product']='category'
    selected_markets: list[str]=Field(default_factory=lambda:list(ACTIVE),min_length=1,max_length=7)
    @field_validator('query')
    @classmethod
    def query_valid(cls,v):
        v=' '.join(v.split())
        if len(v)<2: raise ValueError('Введите минимум два символа')
        return v
    @field_validator('selected_markets')
    @classmethod
    def markets_valid(cls,v):
        if len(set(v))!=len(v) or any(x not in ACTIVE for x in v): raise ValueError('Выберите доступные площадки без повторов')
        return v

class EconomicInputs(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    supplier_price_usd: float|None=Field(default=None,gt=0,le=1000000)
    retail_price: float|None=Field(default=None,gt=0,le=100000000)
    fx: float=Field(default=1,gt=0,le=100000)
    batch_size: int=Field(default=100,ge=1,le=1000000)
    shipping_unit: float=Field(default=0,ge=0,le=10000000)
    import_pct: float=Field(default=0,ge=0,le=100)
    fee_pct: float=Field(default=0,ge=0,le=100)
    fulfillment_unit: float=Field(default=0,ge=0,le=10000000)
    storage_unit: float=Field(default=0,ge=0,le=10000000)
    ads_pct: float=Field(default=0,ge=0,le=100)
    returns_pct: float=Field(default=0,ge=0,le=100)
    tax_pct: float=Field(default=0,ge=0,le=100)
    launch_cost: float|None=Field(default=None,ge=0,le=100000000)
    monthly_units: float|None=Field(default=None,gt=0,le=1000000)
    volumes: list[int]=Field(default_factory=lambda:[30,100,300],min_length=1,max_length=6)
    @field_validator('volumes')
    @classmethod
    def volumes_valid(cls,v):
        if any(n<=0 or n>1000000 for n in v): raise ValueError('Объёмы: 1–1000000')
        return v

class Recalculate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    archetype_id: int=Field(gt=0)
    market: str
    inputs: EconomicInputs

def read_run(rid):
    with connect() as conn:
        row=conn.execute('SELECT * FROM research_runs WHERE id=%s',(rid,)).fetchone()
        if not row: raise HTTPException(404,'Исследование не найдено')
        events=conn.execute('SELECT * FROM (SELECT id,event_type,stage_index,actor,message,meta,created_at FROM research_events WHERE run_id=%s ORDER BY id DESC LIMIT 100) e ORDER BY id',(rid,)).fetchall()
        if row['pipeline_version']==2:
            costs=conn.execute('SELECT COALESCE(SUM(cost),0) AS confirmed_usd,COALESCE(SUM(reserved) FILTER (WHERE cost IS NULL),0) AS uncertain_usd FROM budget_calls WHERE run_id=%s',(rid,)).fetchone()
            row['cost_breakdown']=costs
            row['actual_cost_usd']=costs['confirmed_usd']+costs['uncertain_usd']
            row['result_summary']=dict(row.get('result_summary') or {},cost_has_estimates=bool(costs['uncertain_usd']))
    return jsonable_encoder(dict(row,events=events))

@app.get('/api/health')
def health():
    with connect() as conn: row=conn.execute('SELECT now() AS db_time,(SELECT heartbeat FROM worker_health WHERE id=1) AS worker_heartbeat').fetchone()
    alive=bool(row['worker_heartbeat'] and (row['db_time']-row['worker_heartbeat']).total_seconds()<60)
    return dict(ok=True,worker_available=alive,service='product-hunter-api',**row)

@app.get('/api/marketplaces')
def markets(): return dict(items=catalogue())

@app.get('/api/research')
def research_list(limit:int=Query(10,ge=1,le=50)):
    with connect() as conn: rows=conn.execute('SELECT id,query,status,quality,analysis_mode,selected_markets,progress,actual_cost_usd,created_at FROM research_runs ORDER BY created_at DESC LIMIT %s',(limit,)).fetchall()
    return dict(items=jsonable_encoder(rows))

@app.post('/api/research',status_code=201)
def create(payload:ResearchCreate):
    rid=str(uuid.uuid4()); key=dataset_key_for(payload.query) if payload.analysis_mode=='category' else 'generic'
    scouts={m:dict(status='waiting',source='live',records=0,queries=0,pages=0) for m in payload.selected_markets}
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(7348203)')
        if conn.execute("SELECT COUNT(*) AS n FROM research_runs WHERE status IN ('running','queued')").fetchone()['n']>=16: raise HTTPException(429,'Очередь заполнена, попробуйте позже')
        conn.execute("""INSERT INTO research_runs(id,query,dataset_key,research_mode,analysis_mode,selected_markets,pipeline_version,status,stage_key,stage_title,progress,scouts,stats)
            VALUES (%s,%s,%s,%s,%s,%s,2,'running','resolve_intent','Разбираем запрос',8,%s,%s)""",(rid,payload.query,key,'generic' if key=='generic' else 'preset',payload.analysis_mode,Jsonb(payload.selected_markets),Jsonb(scouts),Jsonb(initial_stats())))
        conn.execute("INSERT INTO research_jobs(run_id,job_type,stage_index,status) VALUES (%s,'advance_research',1,'pending')",(rid,))
        conn.execute("INSERT INTO audit_log(run_id,action,actor,details) VALUES (%s,'research_created','web',%s)",(rid,Jsonb(payload.model_dump())))
    return read_run(rid)

@app.get('/api/research/{run_id}')
def get_run(run_id:uuid.UUID): return read_run(str(run_id))

@app.get('/api/research/{run_id}/events')
def events(run_id:uuid.UUID,limit:int=Query(60,ge=1,le=200)): return dict(items=read_run(str(run_id))['events'][-limit:])

@app.get('/api/research/{run_id}/live-opportunities')
def opportunities(run_id:uuid.UUID,limit:int=Query(5,ge=1,le=20)):
    read_run(str(run_id)); items=get_live_opportunities(str(run_id),limit)
    with connect() as conn: count=conn.execute('SELECT COUNT(*) AS n FROM opportunity_scores WHERE run_id=%s',(run_id,)).fetchone()['n']
    return dict(count=count,items=jsonable_encoder(items))

@app.get('/api/research/{run_id}/live-evidence')
def evidence(run_id:uuid.UUID):
    read_run(str(run_id)); return jsonable_encoder(live_evidence(str(run_id)))

@app.get('/api/research/{run_id}/supplier-evidence')
def suppliers(run_id:uuid.UUID,archetype_id:int|None=Query(None,ge=1)):
    read_run(str(run_id)); data=supplier_evidence(str(run_id),archetype_id)
    data['shortlist']=shortlist(data['offers']); data['shortage']=max(0,3-len(data['shortlist']))
    return jsonable_encoder(data)

@app.get('/api/research/{run_id}/economics')
def economics(run_id:uuid.UUID):
    run=read_run(str(run_id))
    if run['pipeline_version']==1:
        from backend.economics import get_economics
        return dict(version=1,items=jsonable_encoder(get_economics(str(run_id))))
    return dict(version=2,items=economics_v2.get_all(str(run_id)))

@app.post('/api/research/{run_id}/economics/recalculate')
def recalculate(run_id:uuid.UUID,payload:Recalculate):
    run=read_run(str(run_id))
    if run['pipeline_version']!=2 or run['status']!='completed': raise HTTPException(409,'Дождитесь завершения исследования V2')
    try:
        item=economics_v2.build(str(run_id),payload.archetype_id,payload.market,payload.inputs.model_dump(exclude_unset=True))
        economics_v2.rank(str(run_id)); return item
    except ValueError as exc: raise HTTPException(422,str(exc))

@app.post('/api/research/{run_id}/cancel')
@app.post('/api/research/{run_id}/skip',deprecated=True)
def cancel(run_id:uuid.UUID):
    rid=str(run_id); read_run(rid)
    with connect() as conn:
        conn.execute('SELECT status FROM research_runs WHERE id=%s FOR UPDATE',(rid,))
        conn.execute("UPDATE research_runs SET status='cancelled',quality='partial',completed_at=now(),updated_at=now() WHERE id=%s AND status IN ('queued','running')",(rid,))
        conn.execute("UPDATE research_jobs SET status='cancelled',updated_at=now() WHERE run_id=%s AND status IN ('pending','running')",(rid,))
    return read_run(rid)

# Test preview shares the API origin; production remains served by nginx.
import os
from pathlib import Path
if os.getenv('PRODUCT_HUNTER_SERVE_STATIC')=='1':
    from fastapi.staticfiles import StaticFiles
    app.mount('/',StaticFiles(directory=str(Path(__file__).resolve().parent.parent),html=True),name='preview')
