"""Explicit, editable scenarios. Volumes and costs are assumptions, never demand."""
import math
import re
import statistics
from psycopg.types.json import Jsonb
from backend.db import connect
from backend.marketplaces import ACTIVE, run_config
from backend.supplier_review import shortlist

DEFAULTS = dict(supplier_price_usd=None, retail_price=None, fx=1.0, batch_size=100,
    shipping_unit=2.0, import_pct=10.0, fee_pct=18.0, fulfillment_unit=2.0,
    storage_unit=0.2, ads_pct=12.0, returns_pct=3.0, tax_pct=6.0,
    launch_cost=None, monthly_units=None, volumes=[30,100,300])

def parse_price(text, currency):
    if not text: return None
    value=str(text).replace('\u00a0',' ').strip()
    low=value.lower()
    if currency=='RUB':
        if not re.search(r'₽|руб|\brub\b',low) or re.search(r'usd|sgd|\$|€|cny|тг',low): return None
    elif currency=='SGD':
        if not re.search(r'sgd|s\$',low) or re.search(r'us\$|usd|₽|€',low): return None
    elif currency=='USD':
        if not re.search(r'usd|us\$|\$',low) or re.search(r'sgd|(?<!u)s\$|a\$|c\$|cad|aud|₽|€|cny',low): return None
    # Parse only the price prefix/range; numbers in MOQ/pack/voltage are not prices.
    value=re.split(r'/|per\b|moq|minimum|за\s',value,flags=re.I)[0]
    nums=re.findall(r'\d+(?:[ ,]\d{3})*(?:[.,]\d{1,2})?',value)
    if not nums or len(nums)>2: return None
    def number(x):
        x=x.replace(' ','')
        if re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?',x): x=x.replace(',','')
        else: x=x.replace(',','.')
        return float(x)
    values=[number(x) for x in nums]
    if any(not math.isfinite(x) or x<=0 for x in values): return None
    return min(values),max(values)

def unit_compatible(retail_title, supplier_text, unit_kind):
    text=(supplier_text or '').lower()
    if re.search(r'\b(meter|metre|kg|roll|pair)\b|метр|рулон|пара',text): return False
    if re.search(r'\b\d+[ -]*(pack|pcs|pieces)\b|\b(pack|set)\s+of\s*\d+|набор|комплект',retail_title or '',re.I): return False
    if unit_kind=='piece':
        return bool(re.search(r'\b(piece|pieces|pc|pcs|unit)\b|штук|шт\b',text)) and not re.search(r'\b(set|kit|pack)\b',text)
    # Sets/lengths require a confirmed bill of materials, not simply the word "set".
    return False

def calculate(inputs):
    p=inputs.get('retail_price'); supplier=inputs.get('supplier_price_usd')
    missing=[k for k in ('retail_price','supplier_price_usd') if inputs.get(k) is None]
    if missing: return dict(status='insufficient_data',missing=missing)
    landed=supplier*inputs['fx']*(1+inputs['import_pct']/100)+inputs['shipping_unit']
    variable=sum(inputs[k] for k in ('fee_pct','ads_pct','returns_pct','tax_pct'))/100
    cost=landed+inputs['fulfillment_unit']+inputs['storage_unit']+p*variable
    profit=p-cost
    before_ads=profit+p*inputs['ads_pct']/100
    launch=inputs.get('launch_cost'); batch=inputs['batch_size']; pace=inputs.get('monthly_units')
    capital=landed*batch+(launch or 0)
    # Recovery of upfront inventory uses cash after sale costs, not contribution twice.
    cash_per_sale=p*(1-variable)-inputs['fulfillment_unit']-inputs['storage_unit']
    recovery_units=math.ceil(capital/cash_per_sale) if launch is not None and cash_per_sale>0 else None
    return dict(status='calculated',landed_unit=round(landed,2),total_unit_cost=round(cost,2),
        contribution_unit=round(profit,2),margin_pct=round(100*profit/p,2),
        max_acquisition_cost=round(max(0,before_ads),2),
        break_even_units=math.ceil(launch/profit) if launch is not None and profit>0 else None,
        inventory_cash=round(landed*batch,2),launch_cash=round(capital,2) if launch is not None else None,
        payback_months=round(recovery_units/pace,2) if recovery_units is not None and pace and recovery_units<=batch else None,
        payback_note='Окупаемость в пределах заданной партии; при недостатке данных или продаж — не рассчитана.',
        scenarios=[dict(units=n,contribution=round(n*profit,2),profit_after_launch=round(n*profit-launch,2) if launch is not None else None) for n in inputs['volumes']])

def recommendations(label, market, result, features):
    rules=[f'Позиционирование: {label}. Подтвердите характеристики образцом перед размещением.',
        'Карточка: реальные фото, размеры, комплектация и сценарий использования; не обещайте неподтверждённые свойства.',
        f"Площадка: {ACTIVE[market]['label']} / {ACTIVE[market]['country']}. Доступность торговли для вашего юридического лица не проверена."]
    if result.get('status')!='calculated':
        rules.append('Сначала подтвердите сопоставимые цены и комплектацию; рекламный бюджет пока не определён.')
    elif result['contribution_unit']<=0:
        rules.append('При этих допущениях вклад в прибыль неположительный. Пересмотрите закупку, цену и расходы до рекламного теста.')
    else:
        rules.append(f"Для теста стоимость привлечения заказа должна быть ниже {result['max_acquisition_cost']} {ACTIVE[market]['currency']} до учёта разовых расходов.")
    if features:
        rules.append('Отличия и признаки из выборки: '+', '.join(k for k,v in features.items() if not k.startswith('_') and v)[:250]+'. Проверить по исходным карточкам.')
    return rules

def build(run_id, archetype_id, market, overrides=None):
    run=run_config(run_id)
    if market not in run['selected_markets']: raise ValueError('Площадка не выбрана для исследования')
    cfg=ACTIVE[market]
    with connect() as conn:
        candidate=conn.execute('SELECT * FROM product_archetypes WHERE run_id=%s AND id=%s',(run_id,archetype_id)).fetchone()
        if not candidate: raise ValueError('Товар не принадлежит исследованию')
        retail=conn.execute('''SELECT rp.* FROM archetype_members am JOIN normalized_products np ON np.id=am.normalized_product_id JOIN raw_products rp ON rp.id=np.raw_product_id WHERE am.archetype_id=%s AND np.run_id=%s AND np.market=%s''',(archetype_id,run_id,market)).fetchall()
        suppliers=conn.execute('SELECT * FROM supplier_offers WHERE run_id=%s AND archetype_id=%s',(run_id,archetype_id)).fetchall()
        previous=conn.execute('SELECT payload FROM marketplace_economics WHERE run_id=%s AND archetype_id=%s AND market=%s',(run_id,archetype_id,market)).fetchone()
    unit=(run.get('ontology') or {}).get('unit_kind','other')
    retail_usable=[]; supplier_usable=[]
    for r in retail:
        price=parse_price(r['price_text'],cfg['currency'])
        if price and not re.search(r'\b\d+[ -]*(pack|pcs|pieces)\b|\b(pack|set)\s+of\s*\d+|набор|комплект',r['title'],re.I):
            retail_usable.append(dict(value=price[0],max=price[1],url=r['source_url'],observed_at=str(r['created_at']),text=r['price_text']))
    for r in shortlist(suppliers):
        price=parse_price(r['price_text'],'USD')
        if price and r['verification'].get('match')=='confirmed' and unit_compatible(candidate['label'],r['price_text'],unit):
            supplier_usable.append(dict(value=price[1],min=price[0],url=r['source_url'],company=r['company_key'],observed_at=str(r['created_at']),text=r['price_text']))
    inputs=dict(DEFAULTS)
    inputs['fx']={'USD':1.0,'RUB':95.0,'SGD':1.35}[cfg['currency']]
    for k in ('shipping_unit','fulfillment_unit','storage_unit'): inputs[k]=round(inputs[k]*inputs['fx'],2)
    provenance={k:'modelled_assumption' for k in inputs}
    for k in ('launch_cost','monthly_units'): provenance[k]='missing'
    if retail_usable:
        inputs['retail_price']=statistics.median(r['value'] for r in retail_usable); provenance['retail_price']='source'
    else: provenance['retail_price']='missing'
    if supplier_usable:
        inputs['supplier_price_usd']=statistics.median(r['value'] for r in supplier_usable); provenance['supplier_price_usd']='source'
    else: provenance['supplier_price_usd']='missing'
    saved=(previous or {}).get('payload',{}).get('overrides',{})
    saved={**saved,**(overrides or {})}
    for key,value in saved.items():
        if key in inputs:
            inputs[key]=value; provenance[key]='user' if value is not None else 'missing'
    result=calculate(inputs)
    complete=len(retail_usable)>=2 and len(supplier_usable)>=2 and not any(k in saved for k in ('retail_price','supplier_price_usd'))
    result['evidence_quality']='sufficient' if complete else 'partial' if retail_usable or supplier_usable else 'insufficient'
    payload=dict(version='economics_v2',archetype_id=archetype_id,label=candidate['label'],market=market,
        country=cfg['country'],currency=cfg['currency'],inputs=inputs,provenance=provenance,overrides=saved,
        result=result,evidence=dict(retail=retail_usable,suppliers=supplier_usable),
        notes=['Расходы и курс — редактируемые допущения, не действующие тарифы.','30/100/300 единиц — сценарии, не прогноз спроса.',
               'Наборы и неоднозначные единицы требуют ручного подтверждения цены за сопоставимую комплектацию.'],
        recommendations=recommendations(candidate['label'],market,result,
            {f['label']:candidate['features'][f['key']] for f in (run.get('ontology') or {}).get('features',[]) if f['key'] in candidate['features']}))
    with connect() as conn:
        conn.execute('''INSERT INTO marketplace_economics(run_id,archetype_id,market,payload) VALUES (%s,%s,%s,%s)
            ON CONFLICT(run_id,archetype_id,market) DO UPDATE SET payload=EXCLUDED.payload,updated_at=now()''',(run_id,archetype_id,market,Jsonb(payload)))
    return payload

def build_all(run_id):
    from backend.normalizer import get_live_opportunities
    return [build(run_id,int(c['id']),m) for c in get_live_opportunities(run_id,5) for m in run_config(run_id)['selected_markets']]

def get_all(run_id):
    with connect() as conn:
        return [r['payload'] for r in conn.execute('SELECT payload FROM marketplace_economics WHERE run_id=%s ORDER BY archetype_id,market',(run_id,)).fetchall()]

def rank(run_id):
    from backend.normalizer import get_live_opportunities
    for c in get_live_opportunities(run_id,20):
        scenarios=[x for x in get_all(run_id) if x['archetype_id']==c['id']]
        known=[x for x in scenarios if x['result']['status']=='calculated']
        best=max(known,key=lambda x:x['result']['margin_pct'],default=None)
        with connect() as conn:
            suppliers=shortlist(conn.execute('SELECT * FROM supplier_offers WHERE run_id=%s AND archetype_id=%s',(run_id,c['id'])).fetchall())
        supply=min(100,len(suppliers)*20)
        margin=best['result']['margin_pct'] if best else None
        econ=max(0,min(100,40+2*margin)) if margin is not None else 0
        score=round(float(c['opportunity_score'])*0.8+supply*0.1+econ*0.1,2)
        decision='NEEDS_DATA'
        if best and margin<0: decision='NO-GO'
        elif best and margin>=20 and score>=70 and best['result']['evidence_quality']=='sufficient' and float((c.get('explanation') or {}).get('confidence',0))>=0.7:
            decision='TEST'
        elif best and margin>=10 and score>=60: decision='WATCH'
        explanation=dict(version='final_rank_v2',best_market=best['market'] if best else None,
            assumptions=True,scope='Оценка лучшего рассчитанного сценария; сравните остальные площадки',
            supplier_companies=len(suppliers),economics_quality=best['result']['evidence_quality'] if best else 'insufficient')
        with connect() as conn:
            conn.execute('''UPDATE opportunity_scores SET market_score=opportunity_score,supplier_availability_score=%s,economics_score=%s,final_score=%s,decision=%s,final_explanation=%s WHERE run_id=%s AND archetype_id=%s''',
                (supply,econ,score,decision,Jsonb(explanation),run_id,c['id']))
