# Product Hunter

Agentic Product Hunter для поиска перспективных товарных возможностей в международном e-commerce.

Публичный стенд: https://product-hunter.shvarev-demo.ru

API health: https://product-hunter.shvarev-demo.ru/api/health
API docs: https://product-hunter.shvarev-demo.ru/api/docs

## Product pipeline

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

## Текущая архитектура

```text
Nginx
 ├─ static Product Hunter UI
 └─ /api/* → FastAPI :3005
                   │
                   ├─ PostgreSQL 16
                   │   ├─ research_runs
                   │   ├─ research_jobs
                   │   ├─ research_events
                   │   └─ audit_log
                   │
                   └─ PM2 worker
                       └─ DB-backed stage machine
```

### Уже реализовано

- PostgreSQL persistence;
- FastAPI API;
- отдельный background worker;
- job state machine;
- polling UI;
- восстановление research run после F5 по `?run=<uuid>`;
- server-side demo skip;
- research history API;
- audit/event log;
- Budget Guard state;
- recovery оборванного job после рестарта worker;
- fixture-driven Market Scouts / Product Archetypes / TOP-5.

Backend и worker — реальные. Рыночные данные на текущем этапе остаются fixtures.

## Почему worker state находится в PostgreSQL

Research run не должен зависеть от HTTP-запроса или открытого браузера.

Каждый этап — отдельный DB job. Если браузер закрыть, исследование продолжается. Если worker перезапустить, незавершённый job возвращается в очередь и run продолжается.

Сейчас deployment использует один worker. Поэтому при старте worker все оставшиеся `running` jobs считаются оборванными предыдущим процессом и возвращаются в `pending`.

При масштабировании до нескольких workers этот механизм заменяется lease + worker_id + heartbeat.

## API

Основные endpoints:

- `GET /api/health`
- `GET /api/research`
- `POST /api/research`
- `GET /api/research/{run_id}`
- `GET /api/research/{run_id}/events`
- `POST /api/research/{run_id}/skip`

## Database

Миграции лежат в `backend/migrations/`.

Для production-сервера DATABASE_URL хранится вне репозитория в `/etc/product-hunter.env`.

Секреты в Git не коммитятся.

## Process management

PM2:

- `demo-product-hunter-api`
- `demo-product-hunter-worker`

Конфигурация: `ecosystem.config.cjs`.

## Live OpenRouter research

Все четыре Market Scout работают через реальный OpenRouter web-search:

- Wildberries → Exa;
- Ozon → Parallel Search;
- Amazon → Exa;
- Lazada → Exa.

Измеренный полный category-run «Вертикальные пылесосы»:

- 4 рынка;
- 7 успешных search calls;
- 19 уникальных product records после дедупликации;
- фактическая стоимость market layer: $0.05664;
- время до готового TOP-5: около 56 секунд;
- search_calls, raw_products и source evidence сохраняются в PostgreSQL;
- Budget Guard показывает actual provider spend;
- публичный UI показывает live evidence по каждому рынку.

Ингestion не зависит от идеального JSON модели: если structured output повреждён, Product Hunter извлекает product URL из OpenRouter search annotations. Числовые поля нормализуются перед записью в PostgreSQL.

Product Hunter не выдаёт modelled значения за реальные продажи. Market Signal / Trend Transfer / Russia Gap остаются собственными индексами системы.

Текущие лимиты production demo:

- до $0.15 на live market-search слой одного run;
- до $3.00 live-search расходов в сутки;
- общий hard cap интерфейса — $1.50 на глубокий research run.

## Следующий этап

Подключить реальный Supplier Probe для Alibaba / Made-in-China, после чего preliminary economics сможет использовать live supplier price / MOQ вместо fixture-значений.

Полный roadmap: `IMPLEMENTATION_PLAN.md`.