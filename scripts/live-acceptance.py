import json
import pathlib
import sys
import urllib.request

BASE='http://127.0.0.1:3015/api/research'
dest=pathlib.Path('/tmp/product-hunter-v2-acceptance.json')
cases=[('автомобильный чайник','category',['ozon','wb','amazon','lazada','aliexpress','ebay','walmart']),
       ('мини-принтер','category',['ozon','amazon','ebay']),
       ('дорожная подушка','category',['wb','lazada','aliexpress']),
       ('автомобильный чайник 12V','product',['ozon','amazon','walmart']),
       ('Вертикальные пылесосы','category',['wb','amazon']),
       ('Коврики для ванной','category',['ozon','amazon']),
       ('Светодиодные ленты','category',['ozon','amazon'])]
if sys.argv[-1]=='create':
    runs=[]
    for query,mode,markets in cases:
        req=urllib.request.Request(BASE,data=json.dumps(dict(query=query,analysis_mode=mode,selected_markets=markets)).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as response:r=json.load(response)
        runs.append(dict(id=r['id'],query=query))
    dest.write_text(json.dumps(runs,ensure_ascii=False))
for item in json.loads(dest.read_text()):
    with urllib.request.urlopen(BASE+'/'+item['id']) as response:r=json.load(response)
    print(json.dumps(dict(id=r['id'],query=r['query'],status=r['status'],stage=r['stage_index'],quality=r['quality'],cost=r['actual_cost_usd'],stats=r['stats'],warnings=r['warnings']),ensure_ascii=False))
