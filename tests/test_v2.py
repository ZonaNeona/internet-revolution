import unittest
import os
from decimal import Decimal
from unittest.mock import patch
from types import SimpleNamespace
from backend.api_v2 import ResearchCreate,EconomicInputs,create,cancel,recalculate,Recalculate
from backend.economics_v2 import calculate,DEFAULTS,parse_price,unit_compatible
from backend.fixtures import dataset_key_for
from backend.marketplaces import catalogue
from backend.generic_cluster import _clean_result
from backend.supplier_review import shortlist
from backend import runner,budget
from backend.db import connect
from psycopg.types.json import Jsonb

class PureTests(unittest.TestCase):
    def test_development_network_guard(self):
        for policy,kind in [('off','ontology'),('off','market'),('model_only','market'),('model_only','supplier'),('typo','ontology')]:
            with patch.dict(os.environ,{'PRODUCT_HUNTER_EXTERNAL_CALLS':policy}), patch('backend.budget.connect',side_effect=AssertionError('No reservation should be created')):
                with self.assertRaises(budget.BudgetBlocked): budget.reserve('unused',kind)
    def test_null_model_output(self):
        from backend.openrouter_client import _json_content,OpenRouterError
        for content in ('null','[]','broken'):
            with self.assertRaises(OpenRouterError): _json_content(content)
    def test_provider_keepalive_envelope(self):
        import io
        from backend.openrouter_client import _response_payload
        self.assertEqual(_response_payload(io.BytesIO(b': OPENROUTER PROCESSING\n\n{"usage":{"cost":0.001}}'))['usage']['cost'],0.001)
    def test_explicit_voltage_validation(self):
        from backend.generic_cluster import validate_explicit_specs
        observed=dict(archetypes=[dict(key='a',label='Чайник 12 В')],assignments=[dict(raw_product_id=1,relevant=True,archetype_key='a',confidence=.9),dict(raw_product_id=2,relevant=True,archetype_key='a',confidence=.9)])
        out=validate_explicit_specs(observed,[dict(id=1,title='Car kettle 24V'),dict(id=2,title='Car kettle DC12V')],'category','Автомобильный чайник')
        self.assertFalse(out['assignments'][0]['relevant']);self.assertTrue(out['assignments'][1]['relevant'])
    def test_unsafe_urls(self):
        from backend.openrouter_client import _allowed_url,_looks_like_product_url
        self.assertFalse(_allowed_url('javascript://amazon.com/dp/123',['amazon.com']))
        self.assertFalse(_allowed_url('https://amazon.com.evil.test/dp/123',['amazon.com']))
        self.assertFalse(_looks_like_product_url('https://wildberries.ru/catalog/electronics'))
    def test_registry(self):
        self.assertEqual(len(catalogue()),35);self.assertEqual(sum(x['available'] for x in catalogue()),7)
    def test_inputs(self):
        for data in [dict(query='  '),dict(query='чайник',selected_markets=[]),dict(query='чайник',selected_markets=['temu']),dict(query='чайник',selected_markets=['wb','wb'])]:
            with self.assertRaises(ValueError): ResearchCreate(**data)
        for data in [dict(fx=0),dict(volumes=[0]),dict(retail_price=float('nan')),dict(retail_price=0)]:
            with self.assertRaises(ValueError): EconomicInputs(**data)
    def test_presets(self):
        self.assertEqual(dataset_key_for('Вертикальные пылесосы'),'vacuum')
        self.assertEqual(dataset_key_for('Мини-пылесос для автомобиля'),'generic')
    def test_prices(self):
        self.assertEqual(parse_price('1 299 ₽','RUB'),(1299,1299))
        self.assertEqual(parse_price('US$10.00 - 12.00 / piece','USD'),(10,12))
        self.assertIsNone(parse_price('S$10','USD'))
        self.assertEqual(parse_price('S$10','SGD'),(10,10))
        self.assertIsNone(parse_price('0 ₽','RUB'))
        self.assertIsNone(parse_price('€100','USD'))
        self.assertFalse(unit_compatible('Набор из 3 чашек','$1 / piece','piece'))
        self.assertFalse(unit_compatible('LED','$1 / meter','meter'))
    def test_economics(self):
        self.assertEqual(calculate(DEFAULTS)['status'],'insufficient_data')
        inputs=dict(DEFAULTS,retail_price=100,supplier_price_usd=10,fx=1,shipping_unit=0,import_pct=0,fee_pct=0,fulfillment_unit=0,storage_unit=0,ads_pct=10,returns_pct=0,tax_pct=0,launch_cost=180,monthly_units=10)
        r=calculate(inputs)
        self.assertEqual(r['contribution_unit'],80);self.assertEqual(r['break_even_units'],3)
        self.assertEqual(r['max_acquisition_cost'],90)
        self.assertEqual(r['scenarios'][0]['profit_after_launch'],2220)
        self.assertLess(calculate(dict(inputs,supplier_price_usd=200))['margin_pct'],0)
    def test_cluster_ids(self):
        r=_clean_result(dict(archetypes=[dict(key='k',label='k')],assignments=[dict(raw_product_id=99,relevant=True,archetype_key='k',confidence=1),dict(raw_product_id=1,relevant=True,archetype_key='missing',confidence=1)]),{1,2})
        self.assertEqual({x['raw_product_id'] for x in r['assignments']},{1,2})
        self.assertFalse(any(x['relevant'] for x in r['assignments']))
    def test_product_matches_promoted_to_original(self):
        data=dict(archetypes=[dict(key='smart',label='Чайник с индикатором')],assignments=[dict(raw_product_id=1,relevant=True,archetype_key='smart',confidence=.95,matches_request=True),dict(raw_product_id=2,relevant=True,archetype_key='smart',confidence=.8,matches_request=False)])
        out=_clean_result(data,{1,2},'product','Чайник 12V')
        self.assertEqual(out['assignments'][0]['archetype_key'],'target_product')
        self.assertEqual(out['assignments'][1]['archetype_key'],'smart')
    def test_companies(self):
        offers=[dict(supplier_name='ABC Ltd',source_url='https://www.alibaba.com/product-detail/a',raw_data={}),dict(supplier_name='ABC Ltd',source_url='https://www.alibaba.com/product-detail/b',raw_data={}),dict(supplier_name=None,source_url='https://www.alibaba.com/product-detail/c',raw_data={})]
        self.assertEqual(len(shortlist(offers)),0)
        for item in offers: item['raw_data']={'verification':{'match':'confirmed','matched_features':'Напряжение и комплектация'}}
        offers[1]['supplier_name']='ABC Co., Limited'
        self.assertEqual(len(shortlist(offers)),1)

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.ids=[]
        self.policy=patch.dict(os.environ,{'PRODUCT_HUNTER_EXTERNAL_CALLS':'all','PRODUCT_HUNTER_DEVELOPMENT_TOTAL_BUDGET_USD':'100'})
        self.policy.start()
    def tearDown(self):
        self.policy.stop()
        with connect() as conn:
            for rid in self.ids: conn.execute('DELETE FROM research_runs WHERE id=%s',(rid,))
    def new(self,mode='category',markets=['wb','amazon']):
        r=create(ResearchCreate(query='Тест: дорожная подушка',analysis_mode=mode,selected_markets=markets));self.ids.append(r['id']);return r
    def test_structured_retry_uses_run_scoped_cache(self):
        import io,json
        from backend.structured import complete
        r=self.new()
        payload=dict(usage={'cost':0.001},choices=[dict(finish_reason='stop',message=dict(content='{"ok": true}'))])
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'test-placeholder'}), patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(payload).encode())) as remote:
            self.assertEqual(complete(r['id'],'ontology',{},'test',{'ids':[1]}),{'ok':True})
            with patch.dict(os.environ,{'PRODUCT_HUNTER_EXTERNAL_CALLS':'off'}):
                self.assertEqual(complete(r['id'],'ontology',{},'test',{'ids':[1]}),{'ok':True})
                with self.assertRaises(budget.BudgetBlocked): complete(r['id'],'ontology',{},'test',{'ids':[2]})
            self.assertEqual(remote.call_count,1)
    def test_cancel_race(self):
        r=self.new()
        with connect() as conn: job=conn.execute('SELECT * FROM research_jobs WHERE run_id=%s',(r['id'],)).fetchone()
        def slow(*args): cancel(__import__('uuid').UUID(r['id']));return {}
        with patch('backend.runner.ensure_run_ontology',slow): runner.process_job(job)
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT status FROM research_runs WHERE id=%s',(r['id'],)).fetchone()['status'],'cancelled')
            self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM research_jobs WHERE run_id=%s AND status='pending'",(r['id'],)).fetchone()['n'],0)
    def test_ontology_cache_never_copies_assignments(self):
        from backend.ontology import ensure_run_ontology
        a=self.new(); b=self.new()
        context=dict(mode='category',markets=['wb','amazon'],version=2)
        with connect() as conn:
            conn.execute("UPDATE research_runs SET ontology_status='done',ontology=%s WHERE id=%s",(Jsonb(dict(_context=context,archetypes=[],observed_clusters=dict(assignments=[dict(raw_product_id=99)]))),a['id']))
        with patch('backend.structured.complete',side_effect=AssertionError('Cache miss')):
            out=ensure_run_ontology(b['id'],b['query'])
        self.assertNotIn('observed_clusters',out)
    def test_all_cluster_rows_are_processed(self):
        from backend.generic_cluster import build_observed_clusters
        run=self.new()
        rows=[dict(id=i,market='wb',title='Подушка') for i in range(1,92)]
        def complete(rid,kind,schema,system,data,**kw):
            return dict(archetypes=[dict(key='pillow',label='Подушка')],assignments=[dict(raw_product_id=r['id'],relevant=True,archetype_key='pillow',confidence=.9) for r in data['records']])
        with patch('backend.generic_cluster._load_products',return_value=rows),patch('backend.structured.complete',side_effect=complete) as model:
            out,_=build_observed_clusters(run['id'],run['query'],{})
        self.assertEqual(len(out['assignments']),91);self.assertEqual(model.call_count,4)
    def test_groups_on_disjoint_markets(self):
        from backend.normalizer import normalize_run,build_archetypes,get_live_opportunities
        r=self.new()
        with connect() as conn:
            conn.execute('UPDATE research_runs SET scouts=%s WHERE id=%s',(Jsonb({'wb':{'status':'done'},'amazon':{'status':'done'}}),r['id']))
            ids=[]
            for m,title in [('wb','Подушка надувная'),('amazon','Подушка memory foam')]:
                raw=conn.execute('INSERT INTO raw_products(run_id,market,title,source_url) VALUES (%s,%s,%s,%s) RETURNING id',(r['id'],m,title,'https://test.example/'+m)).fetchone()['id']
                ids.append(raw)
        observed=dict(archetypes=[dict(key='a',label='А'),dict(key='b',label='Б')],assignments=[dict(raw_product_id=raw,relevant=True,archetype_key=key,confidence=.95) for raw,key in zip(ids,['a','b'])])
        with patch('backend.normalizer.build_observed_clusters',return_value=(observed,0)): normalize_run(r['id'],'generic')
        build_archetypes(r['id'],'generic')
        candidates=get_live_opportunities(r['id'])
        self.assertEqual(len(candidates),2)
        for c in candidates:
            self.assertEqual(set(c['market_signals']),{'wb','amazon'})
            self.assertEqual(c['market_count'],1)
    def test_budget(self):
        r=self.new()
        with connect() as conn: conn.execute('UPDATE research_runs SET budget_usd=0.04 WHERE id=%s',(r['id'],))
        call=budget.reserve(r['id'],'test')
        with self.assertRaises(budget.BudgetBlocked): budget.reserve(r['id'],'test')
        budget.settle(call,Decimal('0.01'))
        self.assertAlmostEqual(budget.refresh(r['id'])[0],0.01)
    def test_single_active_worker(self):
        with connect(autocommit=True) as lock:
            lock.execute('SELECT pg_advisory_lock(7348202)')
            with self.assertRaisesRegex(RuntimeError,'Another Product Hunter worker'): runner.main()
    def test_concurrent_budget_reservations(self):
        from concurrent.futures import ThreadPoolExecutor
        r=self.new()
        with connect() as conn: conn.execute('UPDATE research_runs SET budget_usd=0.04 WHERE id=%s',(r['id'],))
        def attempt(_):
            try: budget.reserve(r['id'],'test');return True
            except budget.BudgetBlocked:return False
        with ThreadPoolExecutor(max_workers=2) as pool: result=list(pool.map(attempt,range(2)))
        self.assertEqual(sum(result),1)
    def test_empty_single_market_product_keeps_original(self):
        r=self.new('product',['walmart'])
        with patch('backend.runner.ensure_run_ontology',return_value={}),patch('backend.runner.run_live_market_scouts',return_value={'walmart':{'status':'empty'}}),patch('backend.runner.run_live_supplier_probe',return_value={}),patch('urllib.request.urlopen',side_effect=AssertionError('Unexpected external call')):
            for stage in range(1,8):
                with connect() as conn: job=conn.execute('SELECT * FROM research_jobs WHERE run_id=%s AND stage_index=%s',(r['id'],stage)).fetchone()
                runner.process_job(job)
        with connect() as conn:
            row=conn.execute('SELECT status,quality FROM research_runs WHERE id=%s',(r['id'],)).fetchone()
            self.assertEqual(row,{'status':'completed','quality':'insufficient_data'})
            groups=conn.execute('SELECT archetype_key,member_count FROM product_archetypes WHERE run_id=%s',(r['id'],)).fetchall()
            self.assertEqual(groups,[{'archetype_key':'target_product','member_count':0}])
    def test_full_pipeline_idempotency(self):
        r=self.new('product')
        def ontology(rid,q):
            o=dict(unit_kind='piece',positive_keywords=['подушка'],features=[],archetypes=[],market_queries={'wb':['q1','q2'],'amazon':['q1','q2']})
            with connect() as conn:conn.execute('UPDATE research_runs SET ontology=%s WHERE id=%s',(Jsonb(o),rid))
            return o
        def markets(rid,*args):
            from backend.market_scout import _create_call,_persist_success
            for m in ('wb','amazon'):
                call=_create_call(rid,m,'test','exa')
                result=SimpleNamespace(usage={},cost_usd=Decimal('0'),annotations=[],payload={},products=[dict(title='Дорожная подушка',url='https://'+('wildberries.ru/catalog/1/detail.aspx' if m=='wb' else 'amazon.com/dp/B123'),price_text='2000 ₽' if m=='wb' else '$30',feature_summary='Подушка для шеи')])
                _persist_success(run_id=rid,call_id=call,market=m,result=result)
            return {m:dict(enabled=True,status='done',records=1,queries=1) for m in ('wb','amazon')}
        def clusters(rid,*args):
            with connect() as conn: rows=conn.execute('SELECT id FROM raw_products WHERE run_id=%s',(rid,)).fetchall()
            return dict(archetypes=[dict(key='target_product',label='Дорожная подушка')],assignments=[dict(raw_product_id=x['id'],relevant=True,archetype_key='target_product',confidence=0.95) for x in rows]),0
        with patch('backend.runner.ensure_run_ontology',ontology),patch('backend.runner.run_live_market_scouts',markets),patch('backend.normalizer.build_observed_clusters',clusters),patch('backend.runner.run_live_supplier_probe',return_value={}):
            for stage in range(1,8):
                with connect() as conn: job=conn.execute('SELECT * FROM research_jobs WHERE run_id=%s AND stage_index=%s',(r['id'],stage)).fetchone()
                runner.process_job(job)
                runner.process_job(job) # replay cannot enqueue duplicates
                runner.process_job(job)
        with connect() as conn:
            out=conn.execute('SELECT * FROM research_runs WHERE id=%s',(r['id'],)).fetchone()
            self.assertEqual(out['status'],'completed');self.assertEqual(out['quality'],'partial')
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM marketplace_economics WHERE run_id=%s',(r['id'],)).fetchone()['n'],2)
            self.assertEqual(conn.execute('SELECT COUNT(*) AS n FROM research_jobs WHERE run_id=%s',(r['id'],)).fetchone()['n'],7)
            self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM research_jobs WHERE run_id=%s AND status='done'",(r['id'],)).fetchone()['n'],7)
            target=conn.execute('SELECT id FROM product_archetypes WHERE run_id=%s',(r['id'],)).fetchone()['id']
        before=budget.refresh(r['id'])[0]
        item=recalculate(__import__('uuid').UUID(r['id']),Recalculate(archetype_id=target,market='wb',inputs=EconomicInputs(retail_price=2500,supplier_price_usd=5)))
        self.assertEqual(item['provenance']['retail_price'],'user');self.assertEqual(budget.refresh(r['id'])[0],before)

if __name__=='__main__': unittest.main()
