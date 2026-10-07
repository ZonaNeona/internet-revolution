from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.openrouter_client import OpenRouterError, _json_content

ONTOLOGY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category_label_ru": {"type": "string"},
        "category_label_en": {"type": "string"},
        "product_family": {"type": "string"},
        "unit_kind": {
            "type": "string",
            "enum": ["piece", "set", "meter", "kg", "other"],
        },
        "logistics_class": {
            "type": "string",
            "enum": ["small", "medium", "bulky"],
        },
        "positive_keywords": {
            "type": "array",
            "minItems": 4,
            "maxItems": 16,
            "items": {"type": "string"},
        },
        "negative_keywords": {
            "type": "array",
            "maxItems": 12,
            "items": {"type": "string"},
        },
        "features": {
            "type": "array",
            "minItems": 4,
            "maxItems": 12,
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "label": {"type": "string"},
                    "aliases": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 12,
                        "items": {"type": "string"},
                    },
                },
                "required": ["key", "label", "aliases"],
                "additionalProperties": False,
            },
        },
        "market_queries": {
            "type": "object",
            "properties": {
                "wb": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "string"},
                },
                "ozon": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "string"},
                },
                "amazon": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "string"},
                },
                "lazada": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {"type": "string"},
                },
            },
            "required": ["wb", "ozon", "amazon", "lazada"],
            "additionalProperties": False,
        },
        "archetypes": {
            "type": "array",
            "minItems": 4,
            "maxItems": 7,
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "label": {"type": "string"},
                    "keywords": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 12,
                        "items": {"type": "string"},
                    },
                    "exclude_keywords": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {"type": "string"},
                    },
                    "supplier_query": {"type": "string"},
                },
                "required": [
                    "key",
                    "label",
                    "keywords",
                    "exclude_keywords",
                    "supplier_query",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "category_label_ru",
        "category_label_en",
        "product_family",
        "unit_kind",
        "logistics_class",
        "positive_keywords",
        "negative_keywords",
        "features",
        "market_queries",
        "archetypes",
    ],
    "additionalProperties": False,
}


def _slug(value: str, fallback: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return text[:48] or fallback


def _clean_ontology(data: dict[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    archetypes = []
    for index, item in enumerate(data.get("archetypes") or []):
        key = _slug(str(item.get("key") or ""), f"archetype_{index+1}")
        if key in seen:
            key = f"{key}_{index+1}"
        seen.add(key)
        archetypes.append({
            **item,
            "key": key,
            "label": str(item.get("label") or key).strip(),
            "keywords": [str(x).strip() for x in item.get("keywords") or [] if str(x).strip()],
            "exclude_keywords": [
                str(x).strip()
                for x in item.get("exclude_keywords") or []
                if str(x).strip()
            ],
            "supplier_query": str(item.get("supplier_query") or "").strip(),
        })
    data["archetypes"] = archetypes

    features = []
    seen_features: set[str] = set()
    for index, item in enumerate(data.get("features") or []):
        key = _slug(str(item.get("key") or ""), f"feature_{index+1}")
        if key in seen_features:
            key = f"{key}_{index+1}"
        seen_features.add(key)
        features.append({
            **item,
            "key": key,
            "label": str(item.get("label") or key).strip(),
            "aliases": [str(x).strip() for x in item.get("aliases") or [] if str(x).strip()],
        })
    data["features"] = features
    return data


def ensure_run_ontology(run_id: str, query: str) -> dict[str, Any]:
    from backend.marketplaces import ACTIVE, run_config
    from backend.structured import complete
    run = run_config(run_id)
    context = dict(mode=run['analysis_mode'], markets=run['selected_markets'], version=2)
    current = run.get('ontology') or {}
    if current.get('_context') == context:
        return current
    with connect() as conn:
        cached = conn.execute("""SELECT ontology FROM research_runs
            WHERE id<>%s AND lower(query)=lower(%s) AND pipeline_version=2
            AND ontology->'_context'=%s AND ontology_status IN ('done','cache')
            AND created_at>=now()-interval '30 days' ORDER BY created_at DESC LIMIT 1""",
            (run_id,query,Jsonb(context))).fetchone()
    if cached:
        ontology = {k:v for k,v in cached['ontology'].items() if k not in ('observed_clusters','clustering_method')}
        status = 'cache'
    else:
        schema = json.loads(json.dumps(ONTOLOGY_SCHEMA))
        schema['properties']['market_queries']['properties'] = {
            k:dict(type='array',minItems=2,maxItems=2,items=dict(type='string')) for k in run['selected_markets']}
        schema['properties']['market_queries']['required'] = run['selected_markets']
        schema['properties']['archetypes']['minItems'] = 1
        schema['properties']['features']['minItems'] = 1
        ontology = _clean_ontology(complete(run_id,'ontology',schema,
            'Design a product research ontology. Do not invent statistics. Two search queries per selected marketplace. '
            'Preserve all mandatory characteristics in product mode; search the original product plus close alternatives, '
            'never expand it to the entire category. Category mode explores commercially distinct variants. '
            'Russian queries for RU, English for US/SG. Supplier queries in English for Chinese OEM manufacturers. '
            'Every hypothesis is unverified. No sales estimates.',
            dict(query=query,analysis_mode=run['analysis_mode'],markets={k:ACTIVE[k] for k in run['selected_markets']})))
        ontology['_context'] = context
        status = 'done'
    with connect() as conn:
        conn.execute("UPDATE research_runs SET ontology=%s,ontology_status=%s,ontology_cost_usd=(SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM budget_calls WHERE run_id=%s AND kind='ontology'),updated_at=now() WHERE id=%s",
                     (Jsonb(ontology),status,run_id,run_id))
    return ontology

def get_run_ontology(run_id: str) -> dict[str, Any]:
    with connect() as conn:
        row=conn.execute('SELECT ontology FROM research_runs WHERE id=%s',(run_id,)).fetchone()
    return dict((row or {}).get('ontology') or {})
