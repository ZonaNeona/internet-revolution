# Product Hunter — план реализации v2

## 1. Что строим

Product Hunter — система поиска перспективных товаров для запуска на маркетплейсах.

Главная задача системы:

> пользователь вводит категорию или конкретный товар → Product Hunter исследует несколько рынков → находит повторяющиеся товарные архетипы и рыночные сигналы → ищет недооценённые cross-market возможности → проверяет доступность производства в Китае → считает предварительную экономику → возвращает TOP-5 товаров с обоснованием и TOP-5 поставщиков.

Публичный стенд: `product-hunter.shvarev-demo.ru`.

Проект сознательно НЕ является общей BI-панелью, ERP, рекламным кабинетом или системой управления действующими SKU.

---

# 2. Основной UX

Первый экран почти пустой:

**Что будем исследовать?**

Пользователь может:

1. ввести категорию;
2. ввести название конкретного товара;
3. выбрать один из demo-примеров.

Demo-категории:

- Вертикальные пылесосы;
- Коврики для ванной;
- Светодиодные ленты.

Demo-конкретные товары:

- беспроводной пылесос со складной трубой;
- быстросохнущий каменный коврик для ванной;
- RGBIC светодиодная лента с Matter;
- аккумуляторный мини-пылесос для авто.

После запуска пользователь видит не готовый dashboard, а **ход исследования**.

---

# 3. Golden Path

```text
Запрос пользователя
        ↓
Intent + category resolution
        ↓
Query expansion
        ↓
Market Scouts
 WB / Ozon / Amazon / Lazada
        ↓
Search results + доступные public pages
        ↓
Normalization / deduplication
        ↓
Product archetypes
        ↓
Market Signal + Cross-market Signal
        ↓
TOP-20 кандидатов
        ↓
Supplier Probe
 Alibaba / Made-in-China
        ↓
Preliminary Economics
        ↓
TOP-5 Opportunities
        ↓
Deep Supplier Search
        ↓
TOP-5 Suppliers per opportunity
        ↓
Recommendation + evidence
```

Целевое время demo-run: 1–3 минуты.

---

# 4. Исходные ограничения

У проекта нет платного доступа к:

- MPStats;
- Keepa;
- внутренней статистике WB/Ozon/Amazon;
- коммерческим marketplace datasets.

Поэтому V1 строится на:

- OpenRouter models;
- OpenRouter web search / web fetch или эквивалентных web tools;
- доступных публичных страницах;
- search engine snippets;
- собственной нормализации и индексах;
- fixture-данных там, где реальную статистику получить нельзя.

## Ключевой принцип

**Мы не выдаём модельные оценки за реальные продажи.**

Если система не знает продажи, UI не показывает выдуманное значение “18 432 продаж”.

Вместо этого используются:

- Market Signal;
- Cross-market Signal;
- Search Presence;
- Review Mass;
- Offer Density;
- Feature Recurrence;
- Russia Gap;
- Supplier Availability;
- modelled demand / momentum.

Все модельные показатели должны быть помечены как **оценка Product Hunter**.

---

# 5. Роль web agents

Web agents — это разведчики, а не источник точной коммерческой статистики.

Они используются для:

- поиска карточек товаров;
- поиска цен;
- рейтингов и числа отзывов, когда они видимы;
- характеристик;
- брендов и продавцов;
- поиска похожих товаров;
- поиска обзоров и обсуждений;
- поиска supplier listings;
- поиска OEM/ODM производителей;
- извлечения MOQ, цены, lead time и customization, если данные публичны.

Они НЕ должны:

- придумывать продажи;
- делать вид, что имеют внутренние marketplace API;
- обходить защиту сайтов;
- бесконечно сканировать маркетплейс.

---

# 6. Market Scouts

Для каждой категории Hermes создаёт набор поисковых гипотез.

Пример:

`Вертикальные пылесосы`

может быть раскрыт в:

- беспроводной вертикальный пылесос;
- вертикальный пылесос складная труба;
- пылесос с LED-подсветкой;
- пылесос для шерсти животных;
- cordless stick vacuum;
- bendable stick vacuum;
- wet dry vacuum;
- green LED vacuum;
- pet hair cordless vacuum.

После этого параллельно работают четыре scout-а:

- WB Scout;
- Ozon Scout;
- Amazon Scout;
- Lazada Scout.

Каждый scout:

1. получает query set;
2. ищет результаты только по своему рынку;
3. возвращает structured records;
4. останавливается, когда перестаёт находить новые типы товаров или исчерпан budget.

---

# 7. Структура raw product record

Минимальный normalized record:

```json
{
  "market": "amazon",
  "source_url": "...",
  "title": "...",
  "brand": "...",
  "price": 49.99,
  "currency": "EUR",
  "rating": 4.4,
  "review_count": 1832,
  "seller": "...",
  "features": {
    "power_w": 500,
    "battery_min": 55,
    "foldable_tube": true,
    "green_led": true,
    "pet_brush": true,
    "wet_cleaning": false
  },
  "source_quality": 0.82,
  "fetched_at": "..."
}
```

Поля могут быть null.

Каждое значение должно знать свой source/evidence.

---

# 8. Product Archetypes

Product Hunter ранжирует не отдельные branded SKU, а **товарные архетипы**.

Пример:

не:

> Dyson V15 Detect

а:

> беспроводной вертикальный пылесос 450–550 Вт, складная труба, LED-подсветка, pet brush, floor dock.

Pipeline:

1. очистка названий;
2. нормализация характеристик;
3. embeddings;
4. semantic clustering;
5. LLM label generation;
6. deterministic validation.

Из 1 000–3 000 search results целимся получить порядка 30–60 архетипов.

---

# 9. Сигналы V1

## 9.1 Search Presence

Насколько часто архетип встречается:

- в разных поисковых запросах;
- у разных продавцов;
- на разных площадках.

## 9.2 Review Mass

Суммарная масса отзывов у наиболее близких представителей.

Не эквивалент продажам, но полезна как proxy зрелости спроса.

## 9.3 Offer Density

Число независимых предложений / брендов / продавцов.

## 9.4 Feature Recurrence

Как часто конкретный feature повторяется у сильных представителей.

## 9.5 Cross-market Presence

На скольких рынках архетип имеет устойчивый signal.

## 9.6 Russia Gap

Сильный зарубежный signal + сравнительно слабое предложение WB/Ozon.

## 9.7 Supplier Availability

Можно ли найти OEM/ODM-предложения с похожей спецификацией.

---

# 10. Trend Transfer V1

Главная фишка Product Hunter.

V1 не утверждает, что знает исторические продажи.

Вместо этого система ищет:

> товарный архетип уже широко представлен / активно обсуждается на зарубежных рынках, но на WB/Ozon предложение заметно слабее.

Пример:

```text
Amazon signal     92
Lazada signal     78
WB signal         34
Ozon signal       41
Russia Gap        89
Trend Transfer    91
```

Это **cross-sectional signal**, а не доказанная временная корреляция.

---

# 11. Trend Transfer V2

Когда накопится собственная история запусков исследований:

- сохранять market snapshots;
- строить временные ряды;
- считать momentum;
- считать acceleration;
- изучать lead/lag между рынками;
- обучать transfer model на истории.

Только после накопления данных можно утверждать:

> сигнал на рынке A исторически предшествует росту на рынке B на N недель.

---

# 12. Ranking

Первичный Market Score считается до поиска поставщиков.

Пример состава:

- Search Presence;
- Cross-market Presence;
- Russia Gap;
- Review Mass;
- Competition / Offer Density;
- Feature Recurrence.

Далее выбирается TOP-20.

После Supplier Probe добавляются:

- Supplier Availability;
- preliminary margin;
- sourcing complexity;
- MOQ fit.

Финальный Opportunity Score V1 концептуально:

- 25% demand proxies;
- 20% cross-market / trend transfer;
- 20% Russia Gap;
- 15% competition;
- 10% preliminary economics;
- 10% supplier availability.

Формула должна быть версионируемой и объяснимой.

---

# 13. Supplier Probe

Для TOP-20 запускается дешёвый быстрый поиск поставщиков.

Источники V1:

- Alibaba;
- Made-in-China.

Цель Probe:

- понять, производится ли похожий товар;
- получить ориентир цены;
- MOQ;
- lead time;
- customization;
- наличие OEM/ODM.

На этом этапе не нужен exhaustive sourcing.

---

# 14. Deep Supplier Search

После preliminary economics остаётся TOP-5 возможностей.

Для каждой из них система:

1. расширяет supplier queries;
2. собирает больше supplier pages;
3. нормализует компании;
4. удаляет дубликаты;
5. сопоставляет спецификации;
6. считает Supplier Score;
7. возвращает TOP-5 поставщиков.

Для сравнения товара с supplier listing используются:

- normalized features;
- text embeddings;
- при необходимости VLM по изображениям.

---

# 15. Preliminary Economics

Система использует:

- наблюдаемую retail price;
- supplier price range;
- modelled logistics;
- modelled marketplace fee;
- modelled ad spend;
- modelled returns.

Если комиссии/логистика не получены из источника, UI показывает:

> модельное допущение.

Экономика V1 нужна для **ранжирования**, а не для бухгалтерской точности.

---

# 16. Hermes

Hermes — оркестратор research run.

Он НЕ является источником market numbers.

Пример execution plan:

```text
resolve_intent
expand_queries
collect_wb
collect_ozon
collect_amazon
collect_lazada
normalize_products
cluster_archetypes
calculate_market_signals
rank_top_20
probe_suppliers
calculate_preliminary_economics
rank_top_5
deep_supplier_search
build_report
```

Hermes:

- запускает tools;
- контролирует budget;
- решает, достаточно ли evidence;
- может прекратить исследование слабого кандидата;
- формирует explanation;
- отвечает на вопросы пользователя поверх сохранённых данных.

---

# 17. Budget Guard

Research run имеет лимиты:

- max web searches;
- max fetched pages;
- max model tokens;
- max estimated USD cost;
- max runtime.

Цель V1:

**\$0.50–2 на глубокий demo-run**, в зависимости от моделей и числа доступных страниц.

Пример:

```text
budget_usd = 1.50
search_calls_used = 31 / 60
fetches_used = 48 / 120
estimated_cost = \$0.73
```

Если evidence достаточно — Hermes прекращает дальнейший web research.

---

# 18. Архитектура

```text
Product Hunter UI
        |
Product Hunter API
        |
Research Orchestrator
        |
      Hermes
        |
+-------+-------+-------+-------+
|       |       |       |       |
WB    Ozon   Amazon  Lazada  Supplier
Scout Scout   Scout   Scout   Scouts
|       |       |       |       |
+-------+-------+-------+-------+
        |
Raw Evidence Store
        |
Normalizer
        |
Archetype Engine
        |
Signal Calculator
        |
TOP-20
        |
Supplier Probe
        |
Economics
        |
TOP-5
        |
Deep Supplier Search
        |
Decision Report
```

---

# 19. Хранилище

Основные сущности:

- research_runs;
- research_queries;
- search_calls;
- source_documents;
- raw_products;
- normalized_products;
- product_archetypes;
- archetype_members;
- market_signals;
- opportunity_scores;
- suppliers;
- supplier_offers;
- economics_scenarios;
- evidence_items;
- agent_runs;
- audit_log.

---

# Статус реализации на 2026-10-07

- ✅ Этап 0 — новый search-first UX.
- ✅ Этап 1 — fixture-driven research execution.
- ✅ Этап 2 — глубокий TOP-5 UX.
- ✅ Этап 3 — FastAPI + PostgreSQL + persistent jobs/state machine.
- 🟡 Этап 4 — market-search часть реализована на всех 4 рынках: WB/Ozon/Amazon/Lazada работают через OpenRouter web-search; supplier search / fetch-source — следующие.

Backend уже хранит research runs, jobs, events и audit trail в PostgreSQL. UI восстанавливает активный run после reload по ?run=<uuid>.

---

# 20. Этапы реализации

## Этап 0 — смена UX-концепции

**Статус: ✅ реализовано.**

Сделать новый первый экран:

- один search input;
- demo-категории;
- demo-конкретные товары;
- запуск исследования;
- экран выполнения pipeline;
- экран TOP-5 результатов.

Fixture-driven.

### Done

Пользователь вводит «Вертикальные пылесосы» и проходит весь новый Golden Path.

---

## Этап 1 — fixture-driven research execution

**Статус: ✅ реализовано.**

Реализовать визуально:

- query expansion;
- 4 Market Scouts;
- число найденных результатов;
- нормализация;
- clustering;
- TOP-20;
- supplier probe;
- preliminary economics;
- TOP-5.

Никаких ложных “реальных продаж”.

---

## Этап 2 — глубокий TOP-5 UX

**Статус: ✅ реализовано на fixture-данных.**

Для каждого результата:

- описание архетипа;
- почему он перспективен;
- четыре market signals;
- Trend Transfer;
- Russia Gap;
- конкуренция;
- preliminary economics;
- TOP-5 suppliers;
- evidence.

---

## Этап 3 — backend + PostgreSQL + jobs

**Статус: ✅ реализовано.** FastAPI, PostgreSQL, отдельный worker, DB-backed jobs, polling UI, resume после F5 и recovery после рестарта worker.

- FastAPI;
- PostgreSQL;
- migrations;
- research state machine;
- background worker;
- progress events;
- retry;
- audit.

---

## Этап 4 — OpenRouter Research Tools

**Статус: 🟡 market-search реализован, supplier/fetch ещё в работе.** WB, Ozon, Amazon и Lazada работают через реальные OpenRouter web-search calls. Ozon использует Parallel Search, остальные рынки — Exa. Измеренный полный run «Вертикальные пылесосы»: 4 рынка → 7 успешных search calls → 19 уникальных records → $0.05664 → около 56 секунд до TOP-5. Search calls, actual provider cost, raw products и source evidence сохраняются в PostgreSQL. Есть annotation fallback, numeric normalization, retry semantics и budget reservation.

Сделать tools:

- search_market;
- fetch_source;
- extract_product;
- expand_queries;
- search_suppliers;
- fetch_supplier.

Включить:

- domain filters;
- max result limits;
- retries;
- cache;
- budget guard.

---

## Этап 5 — Product Normalizer

- canonical title;
- currency normalization;
- brand normalization;
- feature extraction;
- unit normalization;
- deduplication;
- evidence links.

---

## Этап 6 — Archetype Engine

- embeddings;
- semantic clustering;
- deterministic feature checks;
- archetype naming;
- member confidence.

---

## Этап 7 — Signal Engine

Считать V1:

- Search Presence;
- Review Mass;
- Offer Density;
- Feature Recurrence;
- Cross-market Presence;
- Russia Gap;
- Trend Transfer;
- Supplier Availability.

---

## Этап 8 — Supplier Pipeline

- supplier query generation;
- Alibaba scout;
- Made-in-China scout;
- normalization;
- supplier matching;
- Supplier Score;
- preliminary / deep search.

---

## Этап 9 — Economics

- retail price range;
- supplier price;
- assumptions;
- preliminary margin;
- sensitivity;
- score impact.

---

## Этап 10 — Hermes Orchestration

Tools:

- start_research;
- get_research_status;
- expand_queries;
- collect_market;
- normalize_products;
- cluster_archetypes;
- calculate_signals;
- rank_candidates;
- probe_suppliers;
- calculate_economics;
- deep_supplier_search;
- get_evidence;
- build_report.

---

## Этап 11 — собственная история

Каждый run сохраняет snapshots.

После накопления данных:

- real momentum;
- acceleration;
- lead/lag;
- transfer history.

---

# 21. Что показываем работодателю

Demo-run:

**Вертикальные пылесосы**

```text
43 поисковых запроса
4 рынка
728 найденных страниц / карточек
214 полезных product records
37 архетипов
20 прошли market screening
18 имеют supplier signal
5 финальных opportunities
```

Финальный результат:

### №1
**Беспроводной пылесос со складной трубой и LED-подсветкой**

- Market Signal 88;
- Trend Transfer 94;
- Russia Gap 91;
- Supplier Availability 84;
- preliminary margin 31–38%;
- 17 supplier matches;
- рекомендация TEST.

Нажатие раскрывает evidence и TOP-5 suppliers.

---

# 22. Definition of Done V1

V1 готова, когда:

- пользователь может ввести произвольную категорию;
- Hermes строит query expansion;
- хотя бы один Market Scout делает реальный OpenRouter web research;
- raw evidence сохраняется;
- найденные товары нормализуются;
- формируются архетипы;
- рассчитываются собственные signals;
- выдаётся TOP-20;
- supplier probe делает реальный web research;
- выдаётся TOP-5;
- все неподтверждённые числа помечены как modelled;
- каждый сильный вывод имеет evidence;
- run укладывается в budget guard;
- fixture demo стабильно работает даже при недоступности внешних источников.