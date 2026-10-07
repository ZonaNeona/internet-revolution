from __future__ import annotations

import json

from backend.openrouter_client import scout_search

result = scout_search(
    query="cordless stick vacuum bendable tube LED",
    market="Amazon",
    allowed_domains=["amazon.com", "amazon.de"],
    max_results=5,
)

print(json.dumps({
    "products": result.products,
    "annotations_count": len(result.annotations),
    "usage": {
        "prompt_tokens": result.usage.get("prompt_tokens"),
        "completion_tokens": result.usage.get("completion_tokens"),
        "total_tokens": result.usage.get("total_tokens"),
        "cost": result.usage.get("cost"),
    },
}, ensure_ascii=False, indent=2))