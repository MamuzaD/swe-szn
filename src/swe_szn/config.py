from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self, environment: Optional[dict[str, str]] = None) -> None:
        env = environment or os.environ  # do not copy; reflect live env
        self.openai_api_key: Optional[str] = env.get("OPENAI_API_KEY")
        self.firecrawl_api_key: Optional[str] = env.get("FIRECRAWL_API_KEY")
        self.openai_model: str = env.get("OPENAI_MODEL", "gpt-4o-mini")

        # default cache under project ./cache unless overridden
        self.cache_root: Path = Path(env.get("SWE_SZN_CACHE_DIR", "cache")).resolve()

    def require_openai_key(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        return self.openai_api_key

    def require_firecrawl_key(self) -> str:
        if not self.firecrawl_api_key:
            raise RuntimeError("FIRECRAWL_API_KEY not set")
        return self.firecrawl_api_key

    def cache_dir(self, *parts: str) -> Path:
        p = self.cache_root.joinpath(*parts)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


def _ensure_env_file() -> Path:
    env_file = Path(".env")
    example = Path(".env.example")
    if not env_file.exists():
        if example.exists():
            env_file.write_text(example.read_text())
        else:
            env_file.touch()
    return env_file


def _upsert(lines: List[str], key: str, value: str) -> None:
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")


def set_key(key: str, value: str) -> None:
    env_path = _ensure_env_file()
    lines = env_path.read_text().splitlines()
    _upsert(lines, key, value)
    env_path.write_text("\n".join(lines) + "\n")
    # ensure current process sees the latest value immediately
    os.environ[key] = value


def get_status() -> Dict[str, Optional[str]]:
    s = settings()
    return {
        "OPENAI_API_KEY": s.openai_api_key,
        "FIRECRAWL_API_KEY": s.firecrawl_api_key,
        "OPENAI_MODEL": s.openai_model,
        "SWE_SZN_CACHE_DIR": str(s.cache_root),
    }


def snapshot() -> Dict[str, object]:
    vals = get_status()
    missing = [k for k in ("OPENAI_API_KEY", "FIRECRAWL_API_KEY") if not vals.get(k)]
    return {"values": vals, "missing": missing}


def apply(updates: Dict[str, str]) -> None:
    for k, v in updates.items():
        set_key(k, v)
    refresh()


def refresh() -> None:
    load_dotenv(override=True)
    settings.cache_clear()
