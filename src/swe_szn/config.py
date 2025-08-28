from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

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
