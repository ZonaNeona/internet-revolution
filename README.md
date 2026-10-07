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

Amazon Market Scout уже работает на реальном OpenRouter web-search.

Первый измеренный live run:

- 3 Amazon search calls;
- 14 уникальных product records после дедупликации;
- фактическая стоимость $0.024472;
- search_calls, raw_products и source evidence сохранены в PostgreSQL;
- Budget Guard показывает actual spend;
- публичный UI умеет показывать live evidence.

WB, Ozon и Lazada пока остаются fixture-driven. Product Hunter не выдаёт fixture/modelled значения за реальные продажи.

Текущие лимиты production demo:

- до $0.08 на live Amazon Scout одного run;
- до $3.00 live-search расходов в сутки;
- общий hard cap интерфейса — $1.50 на глубокий research run.

## Следующий этап

Расширить тот же Market Scout контракт на WB/Ozon/Lazada, затем подключить реальный Supplier Probe. После этого fixture-данные будут заменяться live records по одному источнику без изменения остальной архитектуры.

Полный roadmap: `IMPLEMENTATION_PLAN.md`.