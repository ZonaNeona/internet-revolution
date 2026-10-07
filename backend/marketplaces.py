"""Single registry for search, geography and the public catalogue."""
ACTIVE = {
    'ozon': dict(label='Ozon', country='RU', currency='RUB', domains=['ozon.ru'], engine='parallel'),
    'wb': dict(label='Wildberries', country='RU', currency='RUB', domains=['wildberries.ru'], engine='exa'),
    'amazon': dict(label='Amazon', country='US', currency='USD', domains=['amazon.com'], engine='exa'),
    'lazada': dict(label='Lazada', country='SG', currency='SGD', domains=['lazada.sg'], engine='exa'),
    'aliexpress': dict(label='AliExpress', country='US', currency='USD', domains=['aliexpress.com', 'aliexpress.us'], engine='parallel'),
    'ebay': dict(label='eBay', country='US', currency='USD', domains=['ebay.com'], engine='parallel'),
    'walmart': dict(label='Walmart', country='US', currency='USD', domains=['walmart.com'], engine='exa'),
}
PLANNED = [
    ('yandex', 'Яндекс Маркет'), ('megamarket', 'Мегамаркет'), ('avito', 'Avito'),
    ('kaspi', 'Kaspi'), ('uzum', 'Uzum'), ('shopee', 'Shopee'), ('temu', 'Temu'),
    ('tiktok', 'TikTok Shop'), ('tokopedia', 'Tokopedia'), ('blibli', 'Blibli'),
    ('rakuten', 'Rakuten'), ('yahoo_jp', 'Yahoo! Shopping Japan'), ('mercari', 'Mercari'),
    ('coupang', 'Coupang'), ('gmarket', 'Gmarket'), ('taobao', 'Taobao'), ('tmall', 'Tmall'),
    ('jd', 'JD.com'), ('pinduoduo', 'Pinduoduo'), ('flipkart', 'Flipkart'), ('meesho', 'Meesho'),
    ('mercadolibre', 'Mercado Libre'), ('allegro', 'Allegro'), ('cdiscount', 'Cdiscount'),
    ('kaufland', 'Kaufland'), ('bol', 'bol'), ('trendyol', 'Trendyol'), ('noon', 'Noon'),
]

def catalogue():
    return [dict(id=k, **{x:v for x,v in m.items() if x not in ('domains','engine')},
                 available=True, method='public_web_search') for k,m in ACTIVE.items()] + [
        dict(id=k, label=name, available=False, reason='Недоступно в демо') for k,name in PLANNED]

def run_config(run_id):
    from backend.db import connect
    with connect() as conn:
        return dict(conn.execute('SELECT * FROM research_runs WHERE id=%s', (run_id,)).fetchone())

def selected(run_id):
    return run_config(run_id)['selected_markets']
