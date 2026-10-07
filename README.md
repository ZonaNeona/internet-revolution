# Product Hunter

Демонстрационный Product Hunter для поиска и проверки товарных возможностей в международном e-commerce.

Публичный стенд: https://product-hunter.shvarev-demo.ru

## Текущий статус

- Этап 0: отдельный репозиторий и публичный стенд — реализовано.
- Этап 1: fixture-driven UX — первая итерация реализована.
- Backend, PostgreSQL, jobs и реальные collectors будут добавляться по IMPLEMENTATION_PLAN.md.

## UX первой итерации

- исследования и их прогресс;
- создание нового исследования;
- таблица товарных возможностей;
- объяснимый Opportunity Score;
- глубокая карточка кандидата: обзор, рынок, конкуренты, отзывы, экономика, поставщики, решение;
- evidence-first drill-down;
- human approval states;
- Hermes как контекстный AI-аналитик поверх Product Hunter.

## Архитектурный принцип

Hermes не содержит бизнес-логику и не считает экономику в промпте. В рабочей архитектуре он вызывает Product Hunter tools/API, а расчёты, состояние workflow и evidence находятся в детерминированном backend-слое.

Полный план находится в IMPLEMENTATION_PLAN.md.