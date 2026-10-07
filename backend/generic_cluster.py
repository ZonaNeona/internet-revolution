from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from backend.db import connect
from backend.openrouter_client import OpenRouterError, _json_content

OBSERVED_CLUSTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "archetypes": {
            "type": "array",
            "minItems": 0,
            "maxItems": 12,
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "supplier_query": {"type": "string"},
                },
                "required": ["key", "label", "description", "supplier_query"],
                "additionalProperties": False,
            },
        },
        "assignments": {
            "type": "array",
            "minItems": 1,
            "maxItems": 80,
            "items": {
                "type": "object",
                "properties": {
                    "raw_product_id": {"type": "integer"},
                    "relevant": {"type": "boolean"},
                    "archetype_key": {"type": "string"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "reason": {"type": "string"},
                },
                "required": [
                    "raw_product_id",
                    "relevant",
                    "archetype_key",
                    "confidence",
                    "reason",
                ],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string"},
    },
    "required": ["archetypes", "assignments", "summary"],
    "additionalProperties": False,
}


def _slug(value: str, fallback: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return text[:48] or fallback


def _load_products(run_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id,market,title,brand,feature_summary,price_text,
                   rating,review_count
            FROM raw_products
            WHERE run_id=%s
            ORDER BY market,id
            """,
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _compact_products(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for row in rows:
        compact.append({
            "id": int(row["id"]),
            "market": row["market"],
            "title": str(row.get("title") or "")[:260],
            "brand": row.get("brand"),
            "features": str(row.get("feature_summary") or "")[:450],
            "price": row.get("price_text"),
            "rating": float(row["rating"]) if row.get("rating") is not None else None,
            "reviews": int(row["review_count"]) if row.get("review_count") is not None else None,
        })
    return compact


def validate_explicit_specs(observed,rows,mode,query):
    """Do not let a model label a 24 V card as 12 V (category-independent units)."""
    def specs(text):
        return {(float(n.replace(',','.')), 'v' if u in ('v','в','volt','volts','вольт') else 'w')
            for n,u in re.findall(r'(\d+(?:[.,]\d+)?)\s*-?\s*(volts?|вольт|v|в|watts?|w|вт)\b',str(text).lower())}
    records={int(r['id']):r for r in rows}
    groups={a['key']:a for a in observed.get('archetypes',[])}
    for assignment in observed.get('assignments',[]):
        row=records.get(assignment['raw_product_id'])
        if not row or not assignment['relevant']: continue
        key=assignment['archetype_key']
        required=specs(query if mode=='product' and key=='target_product' else groups.get(key,{}).get('label',''))
        supplied=specs(str(row.get('title') or '')+' '+str(row.get('feature_summary') or ''))
        if required and not required.issubset(supplied):
            assignment.update(relevant=False,archetype_key='__reject__',confidence=0,reason='Явные числовые характеристики группы не подтверждены исходной карточкой')
    return observed


def _clean_result(
    result: dict[str, Any],
    valid_ids: set[int],
    analysis_mode='category',
    query='',
) -> dict[str, Any]:
    archetypes: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    key_map: dict[str, str] = {}

    for index, item in enumerate(result.get("archetypes") or []):
        if not isinstance(item,dict): continue
        original = str(item.get("key") or "")
        key = _slug(original, f"observed_{index+1}")
        if key in seen_keys:
            key = f"{key}_{index+1}"
        seen_keys.add(key)
        key_map[original] = key
        archetypes.append({
            "key": key,
            "label": str(item.get("label") or key).strip(),
            "description": str(item.get("description") or "").strip(),
            "supplier_query": str(item.get("supplier_query") or "").strip(),
        })

    if analysis_mode=='product':
        archetypes=[a for a in archetypes if a['key']!='target_product']
        archetypes.append(dict(key='target_product',label=query,description='Соответствует явным требованиям исходного запроса',supplier_query=str(result.get('target_supplier_query') or query)))

    valid_keys = {item["key"] for item in archetypes}
    assignments = []
    seen_ids: set[int] = set()
    for item in result.get("assignments") or []:
        if not isinstance(item,dict): continue
        try:
            raw_id = int(item.get("raw_product_id"))
        except Exception:
            continue
        if raw_id not in valid_ids or raw_id in seen_ids:
            continue
        seen_ids.add(raw_id)
        relevant = item.get("relevant") is True
        raw_key = str(item.get("archetype_key") or "")
        key = key_map.get(raw_key, _slug(raw_key, "generic_dynamic"))
        if analysis_mode=='product':
            if item.get('matches_request') is True:
                key='target_product'
            elif key=='target_product':
                relevant=False
        if relevant and key not in valid_keys:
            relevant = False
            key = "__reject__"
        try:
            confidence = float(item.get('confidence') or 0)
        except (ValueError, TypeError):
            confidence = 0
        if not math.isfinite(confidence):
            confidence = 0
        assignments.append({
            "raw_product_id": raw_id,
            "relevant": relevant,
            "archetype_key": key if relevant else "__reject__",
            "confidence": max(0.0, min(1.0, confidence)),
            "reason": str(item.get("reason") or "").strip()[:500],
        })

    # Missing records are not silently promoted to relevant.
    for raw_id in sorted(valid_ids - seen_ids):
        assignments.append({
            "raw_product_id": raw_id,
            "relevant": False,
            "archetype_key": "__reject__",
            "confidence": 0.25,
            "reason": "No assignment returned by observed cluster model.",
        })

    return {
        "archetypes": archetypes,
        "assignments": assignments,
        "summary": str(result.get("summary") or "").strip(),
        "version": "observed_clusters_v1",
    }


def build_observed_clusters(run_id, query, ontology, timeout=90):
    from backend.structured import complete
    from backend.marketplaces import run_config
    rows = _load_products(run_id)
    valid_ids = {int(r['id']) for r in rows}
    existing = ontology.get('observed_clusters') or {}
    if {x['raw_product_id'] for x in existing.get('assignments',[])} == valid_ids and existing.get('version')=='observed_clusters_v3':
        return existing, Decimal('0')
    mode = run_config(run_id)['analysis_mode']
    combined = dict(archetypes=[], assignments=[], summary='', version='observed_clusters_v3')
    schema=json.loads(json.dumps(OBSERVED_CLUSTER_SCHEMA))
    context={k:v for k,v in ontology.items() if k not in ('observed_clusters','clustering_method')}
    if mode=='product':
        schema['properties']['target_supplier_query']=dict(type='string')
        schema['required'].append('target_supplier_query')
        assignment_schema=schema['properties']['assignments']['items']
        assignment_schema['properties']['matches_request']=dict(type='boolean')
        assignment_schema['required'].append('matches_request')
        context={k:v for k,v in context.items() if k not in ('archetypes','features')}
    for offset in range(0,len(rows),30):
        chunk = rows[offset:offset+30]
        schema['properties']['assignments']['minItems']=len(chunk)
        schema['properties']['assignments']['maxItems']=len(chunk)
        schema['properties']['assignments']['items']['properties']['raw_product_id']['enum']=[int(r['id']) for r in chunk]
        result = complete(run_id,'clustering',schema,
            'Classify observed ecommerce records. Reject accessories and unrelated products even if voltage or generic words match. '
            'Return exactly one assignment per supplied ID. Keep reasons under 120 characters. Confidence <0.65 is uncertain, do not promote it. '
            'Return zero to seven commercially distinct groups supported by these records, never invent groups. '
            'Reuse existing group keys where appropriate. In product mode reserve key target_product for records that match '
            'ALL explicit requested characteristics; alternatives must be close and labels/descriptions must state differences. '
            'Do not assign uncertain substitutes to target_product. In category mode use descriptive stable English keys. '
            'In product mode matches_request MUST be true for any relevant record that satisfies the user query exactly. '
            'Only explicit characteristics in the user query are required; extra unspecified capabilities are NOT differences. '
            'target_supplier_query must translate ONLY the explicit user product requirements into an English supplier search. '
            'Alternatives must have an actual difference or unconfirmed requested characteristic, explained in the reason and group description. '
            'Supplier query must preserve defining characteristics. Labels and reasons in Russian.',
            dict(query=query,analysis_mode=mode,ontology=context,existing_groups=combined['archetypes'],records=_compact_products(chunk)),max_tokens=6000)
        clean = _clean_result(result,{int(r['id']) for r in chunk},mode,query)
        known = {a['key'] for a in combined['archetypes']}
        combined['archetypes'].extend(a for a in clean['archetypes'] if a['key'] not in known)
        combined['assignments'].extend(clean['assignments'])
    with connect() as conn:
        ontology = dict(ontology,observed_clusters=combined,clustering_method='observed_v2')
        conn.execute("UPDATE research_runs SET ontology=%s,clustering_cost_usd=(SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM budget_calls WHERE run_id=%s AND kind='clustering') WHERE id=%s",
                     (Jsonb(ontology),run_id,run_id))
    return combined, Decimal('0')
