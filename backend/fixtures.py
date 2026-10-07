from __future__ import annotations

import re

DATASETS = {
    "generic": {
        "patterns": [],
        "stats": {
            "queries": 0,
            "pages": 0,
            "records": 0,
            "archetypes": 0,
            "candidates": 0,
            "supplier_matches": 0,
        },
        "cost": 0.0,
        "scouts": {
            "wb": {"records": 0, "queries": 0, "pages": 0},
            "ozon": {"records": 0, "queries": 0, "pages": 0},
            "amazon": {"records": 0, "queries": 0, "pages": 0},
            "lazada": {"records": 0, "queries": 0, "pages": 0},
        },
    },
    "vacuum": {
        "patterns": [r"пылесос", r"vacuum"],
        "stats": {
            "queries": 43,
            "pages": 728,
            "records": 214,
            "archetypes": 37,
            "candidates": 20,
            "supplier_matches": 63,
        },
        "cost": 0.74,
        "scouts": {
            "wb": {"records": 42, "queries": 9, "pages": 138},
            "ozon": {"records": 49, "queries": 10, "pages": 154},
            "amazon": {"records": 68, "queries": 13, "pages": 247},
            "lazada": {"records": 55, "queries": 11, "pages": 189},
        },
    },
    "bath": {
        "patterns": [r"коврик", r"bath mat", r"каменн"],
        "stats": {
            "queries": 37,
            "pages": 604,
            "records": 188,
            "archetypes": 31,
            "candidates": 18,
            "supplier_matches": 54,
        },
        "cost": 0.63,
        "scouts": {
            "wb": {"records": 44, "queries": 8, "pages": 127},
            "ozon": {"records": 46, "queries": 9, "pages": 139},
            "amazon": {"records": 53, "queries": 11, "pages": 181},
            "lazada": {"records": 45, "queries": 9, "pages": 157},
        },
    },
    "led": {
        "patterns": [r"лент", r"rgb", r"led", r"matter"],
        "stats": {
            "queries": 48,
            "pages": 812,
            "records": 246,
            "archetypes": 42,
            "candidates": 20,
            "supplier_matches": 71,
        },
        "cost": 0.81,
        "scouts": {
            "wb": {"records": 58, "queries": 11, "pages": 164},
            "ozon": {"records": 61, "queries": 12, "pages": 178},
            "amazon": {"records": 72, "queries": 14, "pages": 267},
            "lazada": {"records": 55, "queries": 11, "pages": 203},
        },
    },
}

STAGES = [
    {
        "key": "resolve_intent",
        "title": "Разбираем запрос",
        "description": "Определяем intent, категорию и основные характеристики",
        "progress": 8,
        "message": "resolve_intent завершён",
    },
    {
        "key": "expand_queries",
        "title": "Расширяем пространство поиска",
        "description": "Hermes строит RU/EN запросы и product hypotheses",
        "progress": 18,
        "message": "expand_queries сформировал поисковые гипотезы",
    },
    {
        "key": "collect_markets",
        "title": "Market Scouts исследуют рынки",
        "description": "WB, Ozon, Amazon и Lazada работают параллельно",
        "progress": 39,
        "message": "collect_markets завершил четыре market scout",
    },
    {
        "key": "normalize_products",
        "title": "Нормализуем product records",
        "description": "Извлекаем характеристики, убираем дубликаты и брендовую шумность",
        "progress": 53,
        "message": "normalize_products подготовил полезные product records",
    },
    {
        "key": "cluster_archetypes",
        "title": "Строим товарные архетипы",
        "description": "Embeddings + feature checks объединяют близкие товары",
        "progress": 66,
        "message": "cluster_archetypes сформировал товарные группы",
    },
    {
        "key": "probe_suppliers",
        "title": "Проверяем производство",
        "description": "Supplier Probe ищет похожие OEM/ODM предложения",
        "progress": 79,
        "message": "probe_suppliers завершил первичный sourcing",
    },
    {
        "key": "preliminary_economics",
        "title": "Считаем предварительную экономику",
        "description": "Retail range + supplier range + модельные assumptions",
        "progress": 90,
        "message": "calculate_preliminary_economics пересчитал shortlist",
    },
    {
        "key": "rank_top_5",
        "title": "Готово",
        "description": "TOP‑5 товарных возможностей сформирован",
        "progress": 100,
        "message": "rank_top_5 сформировал итоговый отчёт",
    },
]


def dataset_key_for(query: str) -> str:
    q = query.strip().lower()
    exact = {'вертикальные пылесосы':'vacuum','коврики для ванной':'bath','светодиодные ленты':'led'}
    if q in exact:
        return exact[q]
    return "generic"


def initial_stats() -> dict:
    return {
        "queries": 0,
        "pages": 0,
        "records": 0,
        "archetypes": 0,
        "candidates": 0,
        "supplier_matches": 0,
    }


def initial_scouts() -> dict:
    return {
        name: {"status": "waiting", "records": 0, "queries": 0, "pages": 0}
        for name in ("wb", "ozon", "amazon", "lazada")
    }