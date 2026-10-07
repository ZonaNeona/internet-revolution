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
- 4 LIVE Market Scouts: WB / Ozon / Amazon / Lazada;
- live Normalizer / Archetype Engine / Signal Engine;
- live-derived TOP‑5;
- live Supplier Probe по Alibaba + Made-in-China для TOP‑5;
- Preliminary Economics V1;
- final_rank_v1 с решениями TEST / WATCH / NEEDS_DATA / NO-GO;
- 6-часовой cache market/supplier evidence.

Основной V1 pipeline уже live-derived. Modelled остаются только явно помеченные assumptions экономики (FX, комиссии, реклама, возвраты, пошлина, логистика) и отдельные fallback-сценарии.

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
- `GET /api/research/{run_id}/live-evidence`
- `GET /api/research/{run_id}/live-opportunities`
- `GET /api/research/{run_id}/supplier-evidence`
- `GET /api/research/{run_id}/economics`
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

Контрольные fresh category-runs:

- 4 рынка;
- 8/8 успешных search calls;
- 30–38 уникальных product records после дедупликации;
- фактическая стоимость market layer: примерно $0.054 за run;
- наблюдаемое время полного market layer: примерно 17–66 секунд в зависимости от latency внешнего search provider;
- WB / Amazon / Lazada используют Exa, Ozon — Parallel Search;
- Scout extractor: qwen/qwen3-30b-a3b-instruct-2507 без reasoning;
- search_calls, raw_products и source evidence сохраняются в PostgreSQL;
- Budget Guard показывает actual provider spend;
- публичный UI показывает live evidence по каждому рынку.

Повторный run той же категории в течение 6 часов использует cached evidence: контрольные повторы возвращают 36–38 live records при $0.00 новых market-search расходов и завершаются примерно за 7–8 секунд.

Product records нормализуются перед записью в PostgreSQL: поддерживаются альтернативные поля title/name, строковые rating/review count и неполные marketplace records. Если structured extraction невалиден, call фиксируется как failed и не подменяется выдуманными данными.

Product Hunter не выдаёт modelled значения за реальные продажи. Market Signal / Trend Transfer / Russia Gap остаются собственными индексами системы.

Текущие лимиты production demo:

- до $0.15 на live market-search слой одного run;
- до $3.00 live-search расходов в сутки;
- общий hard cap интерфейса — $1.50 на глубокий research run.

## Live Normalizer / Archetype / Signal Engine

После market search Product Hunter уже не использует fixture TOP-5 для поддержанных demo-категорий.

V1 pipeline:

- raw_products → deterministic relevance filter;
- canonical title / brand / features;
- rule-based archetype assignment для vacuum / bath / led;
- cross-market aggregation;
- Market Presence по каждому рынку;
- Foreign Signal;
- Russia Signal;
- Russia Gap;
- Cross-market Presence;
- Review Mass Score;
- Feature Recurrence;
- Opportunity Score signals_v1.

Контрольный cached run «Светодиодные ленты»:

- 30 raw live records;
- 24 релевантных после normalizer;
- 5 live archetypes;
- TOP-1: RGBIC + Matter / Thread;
- Opportunity Score 84.12;
- Russia Gap 100;
- evidence содержит реальные Amazon / Ozon / Lazada URL;
- повторный market layer = $0 новых search-расходов благодаря 6-часовому cache;
- полный cached pipeline до TOP-5 ≈ 8.3 секунды.

Текущий archetype engine V1 детерминированный и оптимизирован под три demo-категории. Универсальный semantic/embedding слой остаётся следующим расширением.

## Live Supplier Probe

Stage 5 уже работает через реальные Alibaba + Made-in-China search calls для всех TOP‑5 live opportunities.

V1:

- supplier query строится отдельно для каждого из TOP-5 архетипов;
- Alibaba и Made-in-China исследуются параллельно;
- supplier product pages и source URLs сохраняются в PostgreSQL;
- price / MOQ / lead time сохраняются только если они реально видимы в evidence;
- отсутствующие поля остаются пустыми;
- 6-часовой cache переиспользует supplier evidence без повторной оплаты.

Контрольный Supplier Probe:

- 2 B2B search calls на один архетип;
- около 11 supplier offers на архетип;
- свежая стоимость одного архетипа около $0.0146;
- TOP‑5 = до 10 B2B search calls, ориентировочно $0.07–0.08;
- часть offers содержит реальные price / MOQ;
- cached повтор = $0 новых supplier-search расходов.

Web-fetch enrichment протестирован отдельно: B2B-площадки часто не отдают дополнительные MOQ/price поля, поэтому fetch не является блокирующим этапом.

## Preliminary Economics V1

Stage 6 реализован.

Экономика использует:
- retail price evidence из WB/Ozon отдельно для каждого TOP-5 архетипа;
- supplier price evidence из live Supplier Probe;
- robust filtering ценовых выбросов;
- versioned assumptions_v1 для FX, marketplace fee, рекламы, возвратов, налогов, пошлины и логистики.

Safety rule:
- если retail/supplier units сопоставимы → READY/PARTIAL + contribution margin;
- если evidence недостаточно или единицы неоднозначны → INSUFFICIENT DATA без выдуманных значений.

Контрольные сценарии:
- vacuum: retail 6 961 ₽ + supplier median $46.50 → PARTIAL margin −15.3%;
- LED/Matter: supplier evidence есть, сопоставимой RUB retail price нет → INSUFFICIENT DATA.

FX 95 ₽/$ в economics_v1 — именно модельное допущение, не live exchange rate.

## Final Ranking V1

После Supplier Probe и Preliminary Economics Product Hunter пересчитывает итоговый рейтинг:

- 80% Market Score;
- 10% Supplier Availability;
- 10% Economics Score.

Decision rules:

- без supplier/economics evidence → NEEDS_DATA;
- отрицательная optimistic margin → NO-GO;
- TEST требует достаточную economics evidence и не менее 20% conservative margin;
- иначе WATCH / NO-GO.

Контрольный cached vacuum-run:

- 36 live market records;
- 5 архетипов;
- 60 supplier offers;
- TOP market-кандидат «Складная труба + LED-подсветка»;
- Market Score 80;
- Supplier Score 100;
- Economics Score 8.5;
- Final Score 74.85;
- решение NO-GO из-за contribution margin -15.3%;
- полный cached pipeline до финального решения ≈ 10.4 секунды;
- $0 новых search-расходов благодаря market/supplier cache.

### Текущий бюджет полного V1

По измеренным provider costs:

- fresh market layer: около $0.054;
- fresh TOP‑5 Supplier Probe: около $0.07–0.08;
- Normalizer / Archetype / Signals / Economics / Final Ranking: без дополнительных OpenRouter-вызовов;
- ожидаемый свежий полный V1-run: примерно $0.12–0.14;
- cached повтор в пределах 6 часов: около $0 новых search-затрат.

Общий интерфейсный hard cap остаётся $1.50/run, то есть текущая рабочая схема имеет большой запас.

## Следующий этап

Deep Supplier Search по TOP-5 и улучшение economics inputs: live FX, более точная логистика/комиссии и unit normalization для товаров с длиной/весом.

Полный roadmap: `IMPLEMENTATION_PLAN.md`.