"""Durable V2 worker; a session lock protects recovery from a live predecessor."""
import time
import traceback
import threading
from psycopg.types.json import Jsonb
from backend.db import connect
from backend import budget
from backend.fixtures import STAGES
from backend.marketplaces import run_config
from backend.ontology import ensure_run_ontology
from backend.market_scout import run_live_market_scouts
from backend.normalizer import normalize_run, build_archetypes
from backend.supplier_scout import run_live_supplier_probe
from backend.supplier_review import review
from backend.economics_v2 import build_all, rank, get_all

TERMINAL=('completed','failed','cancelled')

def heartbeat():
    with connect() as conn:
        conn.execute('INSERT INTO worker_health(id) VALUES (1) ON CONFLICT(id) DO UPDATE SET heartbeat=now()')

def claim_job():
    with connect() as conn:
        job=conn.execute("SELECT * FROM research_jobs WHERE status='pending' AND available_at<=now() ORDER BY available_at,id FOR UPDATE SKIP LOCKED LIMIT 1").fetchone()
        if job: conn.execute("UPDATE research_jobs SET status='running',attempts=attempts+1,locked_at=now(),updated_at=now() WHERE id=%s",(job['id'],))
        return job

def counters(rid):
    with connect() as conn:
        def count(table): return conn.execute('SELECT COUNT(*) AS n FROM '+table+' WHERE run_id=%s',(rid,)).fetchone()['n']
        return dict(queries=count('search_calls'),pages=count('raw_products'),records=count('normalized_products'),archetypes=count('product_archetypes'),candidates=count('opportunity_scores'),supplier_matches=count('supplier_offers'))

def process_job(job):
    rid=str(job['run_id']); stage=int(job['stage_index']); run=run_config(rid)
    with connect() as conn:
        current=conn.execute('SELECT status FROM research_jobs WHERE id=%s',(job['id'],)).fetchone()
        if not current or current['status'] in ('done','cancelled'): return
    if run['status'] in TERMINAL:
        with connect() as conn: conn.execute("UPDATE research_jobs SET status='cancelled' WHERE id=%s",(job['id'],))
        return
    if run['pipeline_version']==1:
        from backend.worker_v1 import process_job as legacy
        return legacy(job)
    with connect() as conn:
        if conn.execute("SELECT 1 FROM research_jobs WHERE run_id=%s AND stage_index=%s AND status='done'",(rid,stage)).fetchone():
            conn.execute("UPDATE research_jobs SET status='cancelled' WHERE id=%s AND status IN ('pending','running')",(job['id'],)); return
        conn.execute("UPDATE research_runs SET stage_index=%s,stage_key=%s,stage_title=%s,stage_description=%s,updated_at=now() WHERE id=%s AND status NOT IN ('cancelled','failed','completed')",(stage,STAGES[stage]['key'],STAGES[stage]['title'],STAGES[stage]['description'],rid))
    if stage==1:
        try: ensure_run_ontology(rid,run['query'])
        except Exception as exc: budget.warning(rid,'Не удалось построить структуру поиска ('+type(exc).__name__+'); повторите исследование позже')
    elif stage==2:
        scouts={m:dict(status='running',source='live',records=0,queries=0) for m in run['selected_markets']}
        with connect() as conn: conn.execute('UPDATE research_runs SET scouts=%s WHERE id=%s',(Jsonb(scouts),rid))
        scouts=run_live_market_scouts(rid,run['dataset_key'],run['query'])
        for m,v in scouts.items(): v['source']='live'; v['pages']=v.get('records',0)
        with connect() as conn: conn.execute('UPDATE research_runs SET scouts=%s WHERE id=%s',(Jsonb(scouts),rid))
        for m,v in scouts.items():
            if v.get('status')!='done': budget.warning(rid,m+': '+v.get('status','unknown'))
    elif stage==3: normalize_run(rid,run['dataset_key'])
    elif stage==4: build_archetypes(rid,run['dataset_key'])
    elif stage==5: run_live_supplier_probe(rid,run['dataset_key']); review(rid)
    elif stage==6: build_all(rid)
    elif stage==7: rank(rid)
    total,unknown=budget.refresh(rid); stats=counters(rid); finished=stage==7; run=run_config(rid)
    quality='pending'
    if finished:
        eco=get_all(rid)
        quality='insufficient_data' if not stats['records'] else 'partial' if run['warnings'] or not eco or any(x['result']['evidence_quality']!='sufficient' for x in eco) else 'complete'
    with connect() as conn:
        latest=conn.execute('SELECT status FROM research_runs WHERE id=%s FOR UPDATE',(rid,)).fetchone()
        if latest['status'] in TERMINAL:
            conn.execute("UPDATE research_jobs SET status='cancelled' WHERE id=%s",(job['id'],)); return
        conn.execute('''UPDATE research_runs SET status=%s,progress=%s,stats=%s,quality=%s,live_records=%s,live_search_calls=%s,supplier_records=%s,result_summary=%s,
            completed_at=CASE WHEN %s THEN now() ELSE completed_at END,updated_at=now(),error=NULL WHERE id=%s''',
            ('completed' if finished else 'running',STAGES[stage]['progress'],Jsonb(stats),quality,stats['pages'],stats['queries'],stats['supplier_matches'],Jsonb(dict(ready=finished,quality=quality,cost_has_estimates=bool(unknown))),finished,rid))
        conn.execute("INSERT INTO research_events(run_id,event_type,stage_index,actor,message,meta) VALUES (%s,'stage',%s,'Hermes',%s,%s)",(rid,stage,STAGES[stage]['title']+' · карточек '+str(stats['records'])+' · кандидатов '+str(stats['candidates']),Jsonb(dict(stage=STAGES[stage]['key'],cost=total))))
        conn.execute("UPDATE research_jobs SET status='done',updated_at=now() WHERE id=%s",(job['id'],))
        if not finished:
            conn.execute("""INSERT INTO research_jobs(run_id,job_type,stage_index,status) SELECT %s,'advance_research',%s,'pending'
                WHERE NOT EXISTS(SELECT 1 FROM research_jobs WHERE run_id=%s AND stage_index=%s AND status IN ('pending','running','done'))""",(rid,stage+1,rid,stage+1))

def fail_job(job,exc):
    error=type(exc).__name__+': ошибка этапа; подробности в журнале сервера'
    with connect() as conn:
        run=conn.execute('SELECT status FROM research_runs WHERE id=%s FOR UPDATE',(job['run_id'],)).fetchone()
        if run['status'] in TERMINAL:
            conn.execute("UPDATE research_jobs SET status='cancelled' WHERE id=%s",(job['id'],)); return
        if job['attempts']<2:
            conn.execute("UPDATE research_jobs SET status='pending',last_error=%s,available_at=now()+interval '3 seconds',updated_at=now() WHERE id=%s",(error,job['id']))
        else:
            conn.execute("UPDATE research_jobs SET status='failed',last_error=%s WHERE id=%s",(error,job['id']))
            conn.execute("UPDATE research_runs SET status='failed',quality='partial',error=%s,updated_at=now(),completed_at=now() WHERE id=%s",(error,job['run_id']))

def recover_stale_jobs():
    with connect() as conn:
        conn.execute("UPDATE research_jobs SET status='pending',available_at=now(),locked_at=NULL WHERE status='running'")
        for table in ('search_calls','supplier_search_calls'):
            conn.execute('UPDATE '+table+" SET status='failed',error='Interrupted worker restart',completed_at=now() WHERE status='running'")
        conn.execute("UPDATE budget_calls SET state='estimated' WHERE state='reserved'")

def main():
    with connect(autocommit=True) as lock:
        if not lock.execute('SELECT pg_try_advisory_lock(7348202) AS ok').fetchone()['ok']: raise RuntimeError('Another Product Hunter worker is active')
        recover_stale_jobs()
        def pulse():
            while True:
                try: heartbeat()
                except Exception: pass
                time.sleep(15)
        threading.Thread(target=pulse,daemon=True).start()
        while True:
            lock.execute('SELECT 1'); heartbeat(); job=claim_job()
            if not job: time.sleep(1); continue
            try: process_job(job)
            except Exception as exc: traceback.print_exc(); fail_job(job,exc)

if __name__=='__main__': main()
