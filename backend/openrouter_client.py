from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from decimal import Decimal
from typing import Any

# backend.db loads /etc/product-hunter.env on import.
from . import db as _db  # noqa: F401


class OpenRouterError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        cost_usd: Decimal | float | str = 0,
        usage: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.cost_usd = Decimal(str(cost_usd or 0))
        self.usage = usage or {}


@dataclass
class OpenRouterResult:
    payload: dict[str, Any]
    products: list[dict[str, Any]]
    annotations: list[dict[str, Any]]
    usage: dict[str, Any]
    cost_usd: Decimal


@dataclass
class SupplierSearchResult:
    payload: dict[str, Any]
    offers: list[dict[str, Any]]
    annotations: list[dict[str, Any]]
    usage: dict[str, Any]
    cost_usd: Decimal


def _response_payload(response):
    """Accept JSON envelopes and harmless provider keep-alive comment lines."""
    raw=response.read().decode('utf-8-sig')
    raw='\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith(':'))
    try:
        payload=json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f'Provider returned an invalid or incomplete JSON envelope ({len(raw)} characters; prefix {raw[:24]!r})') from exc
    if not isinstance(payload,dict): raise OpenRouterError('Provider returned a non-object envelope')
    return payload


def _json_content(text: str) -> dict[str, Any]:
    value = (text or "").strip()
    value = re.sub(r"^\x60\x60\x60(?:json)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*\x60\x60\x60$", "", value)
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise OpenRouterError('Model returned a non-object JSON response')
        return parsed
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"Model did not return valid JSON: {value[:500]}") from exc


def _canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url)
    except Exception:
        return url
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _allowed_url(url: str, allowed_domains: list[str]) -> bool:
    try:
        host = (urlsplit(url).hostname or "").lower()
    except Exception:
        return False
    if urlsplit(url).scheme not in ("http","https") or not host:
        return False
    return any(host == domain or host.endswith("." + domain) for domain in allowed_domains)


def _looks_like_product_url(url: str) -> bool:
    path = (urlsplit(url).path or "").lower()
    if 'wildberries.' in (urlsplit(url).hostname or ''):
        return bool(re.search(r'/catalog/\d+/detail\.aspx',path))
    return any(token in path for token in (
        "/product/", "/products/", "/product-detail/", "/dp/", "/gp/product/",
        "/catalog/", "/detail.aspx", "/item/", "/itm/", "/ip/",
    ))

def _citation_urls(annotations):
    urls=set()
    for annotation in annotations or []:
        if not isinstance(annotation,dict): continue
        citation=annotation.get('url_citation') or {}
        if citation.get('url'): urls.add(_canonical_url(citation['url']))
        for url in re.findall(r'https?://[^\s)\]<>"]+',str(citation.get('content') or '')):
            urls.add(_canonical_url(url))
    return urls


def _annotation_products(
    annotations: list[dict[str, Any]],
    allowed_domains: list[str],
) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(title: str, url: str, summary: str = "") -> None:
        if not url or not _allowed_url(url, allowed_domains) or not _looks_like_product_url(url):
            return
        canonical = _canonical_url(url)
        if canonical in seen:
            return
        clean_title = (title or "").strip()
        if not clean_title or "temporary redirect" in clean_title.lower():
            clean_title = (summary or "").strip().splitlines()[0][:220] or "Marketplace product"
        seen.add(canonical)
        products.append({
            "title": clean_title[:300],
            "url": canonical,
            "price_text": None,
            "rating": None,
            "review_count": None,
            "feature_summary": (summary or "").strip()[:700],
            "brand": None,
        })

    link_re = re.compile(r"\[([^\]]{3,300})\]\((https?://[^)\s]+)\)")
    for annotation in annotations or []:
        if not isinstance(annotation, dict):
            continue
        citation = annotation.get("url_citation") or {}
        url = str(citation.get("url") or "")
        title = str(citation.get("title") or "")
        content = str(citation.get("content") or "")
        add(title, url, content)

        for match in link_re.finditer(content):
            add(match.group(1), match.group(2), content)

    return products[:10]


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


SUPPLIER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "offers": {
            "type": "array",
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "supplier_name": _nullable("string"),
                    "product_title": {"type": "string"},
                    "url": {"type": "string"},
                    "price_text": _nullable("string"),
                    "moq_text": _nullable("string"),
                    "lead_time_text": _nullable("string"),
                    "customization": _nullable("string"),
                    "feature_summary": {"type": "string"},
                    "country": _nullable("string"),
                },
                "required": [
                    "supplier_name",
                    "product_title",
                    "url",
                    "price_text",
                    "moq_text",
                    "lead_time_text",
                    "customization",
                    "feature_summary",
                    "country",
                ],
                "additionalProperties": False,
            },
        },
        "search_summary": {"type": "string"},
    },
    "required": ["offers", "search_summary"],
    "additionalProperties": False,
}


def scout_search(
    *,
    query: str,
    market: str,
    allowed_domains: list[str],
    max_results: int = 5,
    timeout: int = 75,
    engine: str = "exa",
) -> OpenRouterResult:
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get(
        "PRODUCT_HUNTER_SCOUT_MODEL",
        "qwen/qwen3-30b-a3b-instruct-2507",
    ).strip()

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
                    "engine": engine,
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
        "max_tokens": 1200,
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
    annotations = message.get("annotations") or []
    usage = payload.get("usage") or {}
    raw_cost = usage.get("cost")
    if raw_cost is None:
        raw_cost = 0
    cost = Decimal(str(raw_cost))

    parse_error: OpenRouterError | None = None
    try:
        parsed = _json_content(message.get("content") or "")
    except OpenRouterError as exc:
        parse_error = exc
        parsed = {}

    raw_products = parsed.get("products") or []
    fallback_products = _annotation_products(annotations, allowed_domains)

    products: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in [*raw_products, *fallback_products]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not _allowed_url(url, allowed_domains) or not _looks_like_product_url(url):
            continue
        canonical = _canonical_url(url)
        if canonical not in _citation_urls(annotations):
            continue
        if canonical in seen_urls:
            continue
        normalized = dict(item)
        normalized["url"] = canonical
        seen_urls.add(canonical)
        products.append(normalized)

    if not products and parse_error is not None:
        raise OpenRouterError(
            str(parse_error),
            cost_usd=cost,
            usage=usage,
        )

    return OpenRouterResult(
        payload=payload,
        products=products,
        annotations=annotations,
        usage=usage,
        cost_usd=cost,
    )

def supplier_search(
    *,
    query: str,
    source: str,
    allowed_domains: list[str],
    max_results: int = 6,
    timeout: int = 75,
    engine: str = "exa",
) -> SupplierSearchResult:
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get(
        "PRODUCT_HUNTER_SCOUT_MODEL",
        "qwen/qwen3-30b-a3b-instruct-2507",
    ).strip()

    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured")

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a sourcing research scout. Use web search before answering. "
                    "Find only supplier or manufacturer product listings supported by search evidence. "
                    "Never invent price, MOQ, lead time, customization, company names or URLs. "
                    "Use null when a field is not visible. Return the requested JSON schema only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Supplier source: {source}. Search query: {query}. "
                    "Find up to six relevant OEM/ODM supplier product offers. "
                    "Prefer actual supplier product pages over category or editorial pages."
                ),
            },
        ],
        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "engine": engine,
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
                "name": "supplier_scout_result",
                "strict": True,
                "schema": SUPPLIER_SCHEMA,
            },
        },
        "temperature": 0.1,
        "max_tokens": 1600,
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
            "X-Title": "Product Hunter Supplier Scout",
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
    annotations = message.get("annotations") or []
    usage = payload.get("usage") or {}
    cost = Decimal(str(usage.get("cost") or 0))

    parse_error: OpenRouterError | None = None
    try:
        parsed = _json_content(message.get("content") or "")
    except OpenRouterError as exc:
        parse_error = exc
        parsed = {}

    raw_offers = parsed.get("offers") or parsed.get("products") or []
    fallback = _annotation_products(annotations, allowed_domains)

    offers: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in [*raw_offers, *fallback]:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if not _allowed_url(url, allowed_domains) or not _looks_like_product_url(url):
            continue
        canonical = _canonical_url(url)
        if canonical not in _citation_urls(annotations):
            continue
        if canonical in seen_urls:
            continue

        features = (
            item.get("feature_summary")
            or item.get("features")
            or item.get("description")
            or ""
        )
        if isinstance(features, list):
            features = "; ".join(str(x) for x in features if x is not None)

        customization = (
            item.get("customization")
            or item.get("customization_text")
            or item.get("customization_options")
        )
        if isinstance(customization, list):
            customization = "; ".join(str(x) for x in customization if x is not None)

        normalized = {
            "supplier_name": (
                item.get("supplier_name")
                or item.get("manufacturer")
                or item.get("brand")
            ),
            "product_title": str(
                item.get("product_title")
                or item.get("title")
                or item.get("name")
                or "Supplier offer"
            ).strip(),
            "url": canonical,
            "price_text": item.get("price_text", item.get("price")),
            "moq_text": item.get("moq_text", item.get("moq")),
            "lead_time_text": item.get("lead_time_text", item.get("lead_time")),
            "customization": customization,
            "feature_summary": str(features or "").strip(),
            "country": item.get("country") or item.get("place_of_origin"),
            "raw": item,
        }
        seen_urls.add(canonical)
        offers.append(normalized)

    if not offers and parse_error is not None:
        raise OpenRouterError(
            str(parse_error),
            cost_usd=cost,
            usage=usage,
        )

    return SupplierSearchResult(
        payload=payload,
        offers=offers,
        annotations=annotations,
        usage=usage,
        cost_usd=cost,
    )

def supplier_fetch(
    *,
    url: str,
    source: str,
    allowed_domains: list[str],
    timeout: int = 60,
    engine: str = "openrouter",
) -> SupplierSearchResult:
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get(
        "PRODUCT_HUNTER_SCOUT_MODEL",
        "qwen/qwen3-30b-a3b-instruct-2507",
    ).strip()

    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is not configured")

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a sourcing data extractor. Fetch the exact supplier page the user gives you. "
                    "Extract only fields visible on that page. Never invent price, MOQ, lead time, "
                    "customization or supplier name. Use null when unavailable. Return JSON schema only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Supplier source: {source}. Fetch this exact URL and extract one supplier offer: {url}"
                ),
            },
        ],
        "tools": [
            {
                "type": "openrouter:web_fetch",
                "parameters": {
                    "engine": engine,
                    "max_content_tokens": 12000,
                    "allowed_domains": allowed_domains,
                },
            }
        ],
        "tool_choice": "required",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "supplier_fetch_result",
                "strict": True,
                "schema": SUPPLIER_SCHEMA,
            },
        },
        "temperature": 0.0,
        "max_tokens": 1400,
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
            "X-Title": "Product Hunter Supplier Fetch",
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
    usage = payload.get("usage") or {}
    cost = Decimal(str(usage.get("cost") or 0))
    annotations = message.get("annotations") or []

    try:
        parsed = _json_content(message.get("content") or "")
    except OpenRouterError as exc:
        raise OpenRouterError(str(exc), cost_usd=cost, usage=usage) from exc

    raw_offers = parsed.get("offers") or []
    offers = [item for item in raw_offers if isinstance(item, dict)]

    return SupplierSearchResult(
        payload=payload,
        offers=offers,
        annotations=annotations,
        usage=usage,
        cost_usd=cost,
    )
