from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Optional, Union


def ensure_dir(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def md5_digest(text: str, limit: Optional[int] = None) -> str:
    s = text if limit is None else text[:limit]
    return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()


def hash_key(*parts: str) -> str:
    m = hashlib.md5()
    for p in parts:
        m.update(p.encode("utf-8", errors="ignore"))
    return m.hexdigest()


def load_json(path: Union[str, Path]) -> Optional[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(path: Union[str, Path], data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def strip_json_code_fence(content: str) -> str:
    s = (content or "").strip()
    if s.startswith("```"):
        s = s.strip("`\n")
        if s.startswith("json"):
            s = s[4:].strip()
    return s
