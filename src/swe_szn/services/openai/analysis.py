import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from swe_szn.config import settings
from swe_szn.prompts import load_prompt
from swe_szn.services.cache import (
    ensure_dir,
    hash_key,
    load_json,
    md5_digest,
    save_json,
    strip_json_code_fence,
)

from .client import get_client
from .models import estimate_cost, supports_temperature


def compare_jd_vs_resume(
    jd_markdown: str,
    resume_text: str,
    model: Optional[str] = None,
    *,
    job_url: Optional[str] = None,
    cache_dir: Optional[Union[str, Path]] = None,
    force: bool = False,
    prompt_name: str = "swe_intern",
) -> Dict[str, Any]:
    """compare JD vs resume using OpenAI with caching"""
    use_model = model or settings().openai_model
    client = get_client()

    jd_digest = md5_digest(jd_markdown, limit=8000)
    res_digest = md5_digest(resume_text, limit=8000)
    key = hash_key(use_model, job_url or "", jd_digest, res_digest)

    cache_path = Path(cache_dir) if cache_dir else settings().cache_dir("openai")
    ensure_dir(cache_path)
    cache_file = cache_path / f"{key}.json"

    if not force and cache_file.exists():
        cached = load_json(cache_file)
        if cached is not None:
            return cached

    # load standard or user prompt
    PROMPT = load_prompt(prompt_name)
    SYSTEM_PROMPT = PROMPT["system"]
    USER_TEMPLATE = PROMPT["user_template"]
    user_prompt = USER_TEMPLATE.format(
        job=jd_markdown[:12000], resume=resume_text[:12000]
    )

    kwargs = {
        "model": use_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    if supports_temperature(use_model):
        kwargs["temperature"] = 0.2

    start_time = time.perf_counter()
    resp = client.chat.completions.create(**kwargs)
    elapsed = int((time.perf_counter() - start_time) * 1000)
    content = strip_json_code_fence(resp.choices[0].message.content or "{}")

    input_tokens = resp.usage.prompt_tokens if resp.usage else 0
    output_tokens = resp.usage.completion_tokens if resp.usage else 0
    cost_estimate = estimate_cost(use_model, input_tokens, output_tokens)

    print(
        f"API Cost: ${cost_estimate['total_cost_usd']:.6f} "
        f"({input_tokens} input + {output_tokens} output tokens)"
    )

    try:
        parsed = json.loads(content)
        parsed.setdefault("summary", "")
        parsed.setdefault("match_score", 0)
        scores = parsed.get("scores") or {}
        parsed["scores"] = {
            "skills_match": int(scores.get("skills_match", 0)),
            "experience_alignment": int(scores.get("experience_alignment", 0)),
            "keyword_coverage": int(scores.get("keyword_coverage", 0)),
        }
        parsed.setdefault("strong_matches", [])
        parsed.setdefault("gaps", [])

        keywords = parsed.get("keywords", {})
        parsed["keywords"] = {
            "matched": keywords.get("matched", []),
            "missing": keywords.get("missing", []),
            "quick_wins": keywords.get("quick_wins", []),
        }

        parsed["_meta"] = {
            "key": key,
            "model": use_model,
            "job_url": job_url,
            "cost_estimate": cost_estimate,
            "elapsed": elapsed,
        }
        try:
            save_json(cache_file, parsed)
        except Exception:
            pass
        return parsed
    except Exception:
        fallback = {
            "summary": content,
            "match_score": 0,
            "scores": {
                "skills_match": 0,
                "experience_alignment": 0,
                "keyword_coverage": 0,
            },
            "strong_matches": [],
            "gaps": [],
            "keywords": {
                "preferred": [],
                "matched": [],
                "missing": [],
                "quick_wins": [],
            },
            "_meta": {
                "key": key,
                "model": use_model,
                "job_url": job_url,
                "elapsed": elapsed,
            },
        }

        return fallback
