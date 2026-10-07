from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ENV_PATH = Path(os.environ.get("PRODUCT_HUNTER_ENV_FILE", "/etc/product-hunter.env"))


def _load_env_file() -> None:
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()
DATABASE_URL = os.environ["DATABASE_URL"]


def connect(*, autocommit: bool = False):
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        autocommit=autocommit,
        connect_timeout=5,
        application_name="product-hunter",
    )