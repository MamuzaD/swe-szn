import json
from typing import Dict, Any, Optional, Union
from pathlib import Path

from openai import OpenAI

from swe_szn.config import settings
from swe_szn.services.cache import (
    md5_digest,
    hash_key,
    ensure_dir,
    load_json,
    save_json,
    strip_json_code_fence,
)
from swe_szn.prompts import load_prompt

MODEL_SUPPORTS_TEMPERATURE = {
    "gpt-5": False,
}

MODEL_PRICING = {
    # 3.5 and 4 family
    "gpt-4o": {"input": 0.0025, "output": 0.0100},  # $2.50 / $10.00 per 1K
    "gpt-4o-mini": {"input": 0.00060, "output": 0.00240},  # $0.60 / $2.40 per 1K
    "gpt-4-turbo": {"input": 0.0100, "output": 0.0300},  # $10 / $30 per 1K
    "gpt-4": {"input": 0.0300, "output": 0.0600},  # $30 / $60 per 1K
    "gpt-3.5-turbo": {"input": 0.00050, "output": 0.00150},  # $0.50 / $1.50 per 1K
    # GPT‑5 family
    "gpt-5": {"input": 0.00125, "output": 0.01000},  # $1.25 / $10.00 per 1K
    "gpt-5-mini": {"input": 0.00025, "output": 0.00200},  # $0.25 / $2.00 per 1K
    "gpt-5-nano": {"input": 0.00005, "output": 0.00040},  # $0.05 / $0.40 per 1K
    # GPT‑4.1 family
    "gpt-4.1": {"input": 0.00300, "output": 0.01200},  # $3.00 / $12.00 per 1K
    "gpt-4.1-mini": {"input": 0.00080, "output": 0.00320},  # $0.80 / $3.20 per 1K
    "gpt-4.1-nano": {"input": 0.00020, "output": 0.00080},  # $0.20 / $0.80 per 1K
}


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int
) -> Dict[str, Union[float, str]]:
    """Estimate the cost of an OpenAI API request"""
    pricing = MODEL_PRICING.get(
        model, MODEL_PRICING["gpt-4o-mini"]
    )  # default to mini pricing

    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "pricing_per_1k": pricing,
    }


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

    client = OpenAI(api_key=settings().require_openai_key())

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

    supports = MODEL_SUPPORTS_TEMPERATURE.get(use_model, False)
    if supports:
        kwargs["temperature"] = 0.2

    resp = client.chat.completions.create(**kwargs)
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
            "skills_match": int(
                scores.get("skills_match", parsed.get("match_score", 0))
            ),
            "experience_alignment": int(scores.get("experience_alignment", 0)),
            "keyword_coverage": int(scores.get("keyword_coverage", 0)),
        }
        parsed.setdefault("strong_matches", [])
        parsed.setdefault("gaps", [])
        parsed.setdefault("missing_keywords", [])

        # Bullets: prefer structured {achieved, targets}; keep legacy fallback
        bullets = parsed.get("bullets")
        if isinstance(bullets, dict):
            achieved = [
                b for b in (bullets.get("achieved") or []) if isinstance(b, str)
            ]
            targets = [b for b in (bullets.get("targets") or []) if isinstance(b, str)]
            parsed["bullets"] = {"achieved": achieved, "targets": targets}
            # also provide legacy flat list for current markdown export
            parsed["tailored_bullets"] = list(achieved) + [
                f"[Target] {t}" for t in targets
            ]
        else:
            tb = parsed.get("tailored_bullets") or []
            parsed["tailored_bullets"] = tb
            parsed["bullets"] = {
                "achieved": [b for b in tb if not str(b).startswith("[Target]")],
                "targets": [
                    b.replace("[Target] ", "")
                    for b in tb
                    if str(b).startswith("[Target]")
                ],
            }

        parsed["_meta"] = {
            "key": key,
            "model": use_model,
            "job_url": job_url,
            "cost_estimate": cost_estimate,
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
            "missing_keywords": [],
            "tailored_bullets": [],
            "_meta": {"key": key, "model": use_model, "job_url": job_url},
        }
        try:
            save_json(cache_file, fallback)
        except Exception:
            pass
        return fallback
