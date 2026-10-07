import re
from urllib.parse import urlsplit
from psycopg.types.json import Jsonb
from backend.db import connect
from backend.structured import complete
from backend.budget import warning

SCHEMA = dict(type='object',properties={'items':dict(type='array',items=dict(type='object',properties={
    'id':dict(type='integer'),'match':dict(type='string',enum=['confirmed','partial','rejected']),
    'matched_features':dict(type='string'),'differences':dict(type='string')},
    required=['id','match','matched_features','differences'],additionalProperties=False))},required=['items'],additionalProperties=False)

def company_key(offer):
    original=str(offer.get('supplier_name') or '').casefold()
    original=re.sub(r'\b(co|company|ltd|limited|inc|incorporated|corp|corporation|llc)\b','',original)
    name=re.sub(r'[^\w]+','',original)
    if name and name not in ('alibaba','madeinchina','supplier','manufacturer','verifiedsupplier','unknown','na'):
        return name
    host=urlsplit(offer.get('source_url') or '').hostname or ''
    if host.endswith('.made-in-china.com') and host.split('.')[0] not in ('www','m'):
        return host
    return None

def review(run_id):
    with connect() as conn:
        rows=conn.execute('SELECT so.*,pa.label,pa.features FROM supplier_offers so JOIN product_archetypes pa ON pa.id=so.archetype_id WHERE so.run_id=%s ORDER BY so.id',(run_id,)).fetchall()
    pending=[r for r in rows if not (r.get('raw_data') or {}).get('verification')]
    for offset in range(0,len(pending),30):
        chunk=pending[offset:offset+30]
        try:
            answer=complete(run_id,'supplier_match',SCHEMA,
                'Compare supplier offers to the requested candidate using supplied evidence only. '
                'confirmed requires matching defining features; partial for missing key characteristics; rejected for unrelated products. '
                'Never infer missing specifications. Return every ID once; describe differences in Russian.',
                [dict(id=r['id'],candidate=r['label'],candidate_features=r['features'],title=r['product_title'],evidence=r['feature_summary']) for r in chunk])
            valid_ids={r['id'] for r in chunk}
            by_id={}
            for x in answer.get('items',[]):
                if not isinstance(x,dict) or type(x.get('id')) is not int or x['id'] not in valid_ids: continue
                if x.get('match') not in ('confirmed','partial','rejected') or not isinstance(x.get('matched_features'),str) or not isinstance(x.get('differences'),str): continue
                by_id[x['id']]=x
        except Exception as exc:
            warning(run_id,'Не все предложения поставщиков удалось проверить ('+type(exc).__name__+')')
            by_id={}
        with connect() as conn:
            for row in chunk:
                check=by_id.get(row['id'],dict(match='partial',matched_features='',differences='Недостаточно данных для проверки характеристик'))
                data=dict(row.get('raw_data') or {},verification=check,company_key=company_key(row))
                conn.execute('UPDATE supplier_offers SET raw_data=%s WHERE id=%s',(Jsonb(data),row['id']))

def shortlist(offers,include_unverified=False):
    seen=set(); result=[]
    for offer in sorted(offers,key=lambda r:((r.get('raw_data') or {}).get('verification',{}).get('match')!='confirmed',not bool(r.get('price_text')))):
        data=offer.get('raw_data') or {}
        verification=data.get('verification') or {}
        if verification.get('match')=='rejected': continue
        if not include_unverified and (verification.get('match') not in ('confirmed','partial') or not verification.get('matched_features')):
            continue
        key=company_key(offer)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(dict(offer,verification=data.get('verification',{}),company_key=key))
        if len(result)==5: break
    return result
