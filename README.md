# Product Hunter

Agentic Product Hunter для поиска перспективных товарных возможностей в международном e-commerce.

Публичный стенд: https://product-hunter.shvarev-demo.ru

## Концепция V2

Пользователь вводит категорию или конкретный товар.

Дальше Product Hunter проходит pipeline:

1. intent / category resolution;
2. query expansion;
3. Market Scouts: WB, Ozon, Amazon, Lazada;
4. extraction + normalization;
5. semantic product archetypes;
6. market / cross-market signals;
7. TOP-20 screening;
8. Supplier Probe: Alibaba + Made-in-China;
9. preliminary economics;
10. TOP-5 opportunities;
11. deep supplier search;
12. recommendation + evidence.

## Ограничения demo

У проекта нет платных marketplace analytics API (MPStats, Keepa и т.п.).

Поэтому V1/V2 demo:

- не показывает выдуманные продажи;
- использует fixture-driven records для стабильной демонстрации;
- показывает собственные индексы Market Signal, Trend Transfer, Russia Gap и Supplier Availability;
- явно маркирует модельные допущения;
- подготавливает UI и contracts под будущие OpenRouter web-search/web-fetch tools.

## Demo-сценарии

Категории:

- Вертикальные пылесосы;
- Коврики для ванной;
- Светодиодные ленты.

Также есть несколько примеров конкретных товаров.

## Текущий статус

### Stateful backend — реализован

- FastAPI API на 127.0.0.1:3005;
- PostgreSQL 16;
- отдельный background worker;
- persistent research_runs;
- очередь research_jobs;
- research_events и audit_log;
- state machine research pipeline;
- polling UI из API;
- resume после reload через ?run=<uuid>;
- история research runs из PostgreSQL;
- demo skip через API;
- nginx proxy /api/*;
- PM2: demo-product-hunter-api + demo-product-hunter-worker.

Следующий технический этап: подключить первый реальный OpenRouter Research Tool (web search / fetch) к одному Market Scout.\n