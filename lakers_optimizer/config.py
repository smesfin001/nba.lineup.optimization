from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _normalize_database_url(database_url: str) -> str:
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return database_url
    sqlite_path = database_url[len(sqlite_prefix) :]
    if sqlite_path.startswith("/") or sqlite_path == ":memory:":
        return database_url
    return "{}{}".format(sqlite_prefix, Path(sqlite_path).resolve())


@dataclass(frozen=True)
class Settings:
    database_url: str = _normalize_database_url(os.getenv("LAKERS_DB_URL", "sqlite:///./lakers_optimizer.db"))
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def get_settings() -> Settings:
    return Settings()
