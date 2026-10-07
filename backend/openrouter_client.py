from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

# backend.db loads /etc/product-hunter.env on import.
from . import db as _db  # noqa: F401


class OpenRouterError(RuntimeError):
    pass


@dataclass
class OpenRouterResult:
    payload: dict[str, Any]
    products: list[dict[str, Any]]
    annotations: list[dict[str, Any]]
    usage: dict[str, Any]
    cost_usd: Decimal


def _json_content(text: str) -> dict[str, Any]:
    value = (text or "").strip()
    value = re.sub(r"^\x60\x60\x60(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*\x60\x60\x60$", "", value)
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"Model did not return valid JSON: {value[:500]}") from exc


def _nullable(kind: str) -> dict[str, Any]:
    return {"anyOf": [{"type": kind}, {"type": "null"}]}


PRODUCT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "price_text": _nullable("string"),
                    "rating": _nullable("number"),
                    "review_count": _nullable("integer"),
                    "feature_summary": {"type": "string"},
                    "brand": _nullable("string"),
                },
                "required": [
                    "title",
                    "url",
                    "price_text",
                    "rating",
                    "review_count",
                    "feature_summary",
                    "brand",
                ],
                "additionalProperties": False,
            },
        },
        "search_summary": {"type": "string"},
    },
    "required": ["products", "search_summary"],
    "additionalProperties": False,
}


def scout_search(
    *,
    query: str,
    market: str,
    allowed_domains: list[str],
    max_results: int = 5,
    timeout: int = 75,
) -> OpenRouterResult:
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("PRODUCT_HUNTER_SCOUT_MODEL", "qwen/qwen3-30b-a3b").strip()

    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured")

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a product-market research scout. "
                    "Use web search before answering. Extract only products supported by search evidence. "
                    "Never invent price, rating, reviews, URLs or brands. Use null when unavailable. "
                    "Return the requested JSON schema only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Market: {market}. Search query: {query}. "
                    "Find up to five distinct relevant marketplace product examples. "
                    "Prefer actual product/listing pages over editorial pages."
                ),
            },
        ],
        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "engine": "exa",
                    "max_results": max_results,
                    "search_context_size": "low",
                    "allowed_domains": allowed_domains,
                },
            }
        ],
        "tool_choice": "required",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "market_scout_result",
                "strict": True,
                "schema": PRODUCT_SCHEMA,
            },
        },
        "temperature": 0.1,
        "usage": {"include": True},
    }

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "HTTP-Referer": "https://product-hunter.shvarev-demo.ru",
            "X-Title": "Product Hunter Market Scout",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise OpenRouterError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

    choices = payload.get("choices") or []
    if not choices:
        raise OpenRouterError(f"OpenRouter response has no choices: {str(payload)[:1000]}")

    message = choices[0].get("message") or {}
    parsed = _json_content(message.get("content") or "")
    products = parsed.get("products") or []
    annotations = message.get("annotations") or []
    usage = payload.get("usage") or {}

    raw_cost = usage.get("cost")
    if raw_cost is None:
        raw_cost = 0
    cost = Decimal(str(raw_cost))

    return OpenRouterResult(
        payload=payload,
        products=products,
        annotations=annotations,
        usage=usage,
        cost_usd=cost,
    )