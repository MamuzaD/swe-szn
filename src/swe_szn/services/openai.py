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

    resp = client.chat.completions.create(
        model=use_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = strip_json_code_fence(resp.choices[0].message.content or "{}")

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

        parsed["_meta"] = {"key": key, "model": use_model, "job_url": job_url}
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
