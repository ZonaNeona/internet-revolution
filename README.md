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

Реализован fixture-driven Этап 0/1 из IMPLEMENTATION_PLAN.md:

- новый search-first UX;
- визуальный research run;
- Hermes orchestration mock;
- 4 Market Scouts;
- Product Archetypes;
- Market / Transfer / Russia Gap signals;
- TOP-5 opportunities;
- Supplier Probe;
- TOP-5 supplier fixtures;
- preliminary economics;
- evidence layer;
- Budget Guard UX.

Следующий технический этап: FastAPI + PostgreSQL + jobs, после чего подключаем первый реальный OpenRouter Research Tool.