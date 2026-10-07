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

## Ограничения текущего demo

У проекта нет платных marketplace analytics API.

Поэтому demo:

- не показывает выдуманные продажи;
- использует fixture-driven product records;
- показывает собственные Market Signal / Trend Transfer / Russia Gap / Supplier Availability;
- явно маркирует модельные допущения;
- готов к подключению OpenRouter web research tools следующим этапом.

## Следующий этап

Подключить первый реальный OpenRouter Market Scout:

`query expansion → web search → structured extraction → source evidence → raw_products`

После этого fixture-данные начнут поэтапно заменяться настоящими web-research records.

Полный roadmap: `IMPLEMENTATION_PLAN.md`.