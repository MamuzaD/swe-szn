import json
import time
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Union

from openai import OpenAI

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


def get_client():
    global client
    if "client" not in globals() or client is None:
        client = OpenAI(api_key=settings().require_openai_key())
    return client


MODEL_SUPPORTS_TEMPERATURE = {
    "gpt-4o": True,
    "gpt-4o-mini": True,
    "gpt-4-turbo": True,
    "gpt-4": True,
    "gpt-3.5-turbo": True,
    "gpt-5": False,
    "gpt-5-mini": False,
    "gpt-5-nano": False,
    "gpt-4.1": True,
    "gpt-4.1-mini": True,
    "gpt-4.1-nano": True,
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
) -> Dict[str, Union[float, str, dict]]:
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

    supports = MODEL_SUPPORTS_TEMPERATURE.get(use_model, True)
    if supports:
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
            "jd": {
                "canonical": keywords.get("jd", {}).get("canonical", []),
                "by_phrase": keywords.get("jd", {}).get("by_phrase", {}),
            },
            "resume": {"canonical": keywords.get("resume", {}).get("canonical", [])},
            "must_have": keywords.get("must_have", []),
            "preferred": keywords.get("preferred", []),
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
                "jd": {"canonical": [], "by_phrase": {}},
                "resume": {"canonical": []},
                "must_have": [],
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


def chat_about_job_stream(
    question: str,
    *,
    jd_markdown: str,
    resume_text: str,
    model: Optional[str] = None,
    prompt_name: str = "swe_intern_chat",
    history: Optional[list] = None,
) -> Generator[str, None, Dict[str, Any]]:
    """Stream answer tokens for a user question about the job/resume context"""
    use_model = model or settings().openai_model
    client = get_client()

    if history is None:
        # first time build initial context with system prompt and static content
        PROMPT = load_prompt(prompt_name)
        SYSTEM_PROMPT = PROMPT["system"]
        USER_TEMPLATE = PROMPT["user_template"]
        user_prompt = USER_TEMPLATE.format(
            job=jd_markdown[:12000], resume=resume_text[:12000]
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "user", "content": question},
        ]
    else:
        messages = history + [{"role": "user", "content": question}]

    kwargs = {
        "model": use_model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    supports = MODEL_SUPPORTS_TEMPERATURE.get(use_model, True)
    if supports:
        kwargs["temperature"] = 0.5

    input_tokens = 0
    output_tokens = 0
    full_text = []

    start_time = time.perf_counter()
    stream = client.chat.completions.create(**kwargs)
    for chunk in stream:
        choice = (chunk.choices or [None])[0]
        delta = getattr(choice, "delta", None)
        if delta is not None:
            content = getattr(delta, "content", None)
            if content:
                full_text.append(content)
                yield content

        usage = getattr(chunk, "usage", None)
        if usage:
            input_tokens = getattr(usage, "prompt_tokens", input_tokens) or input_tokens
            output_tokens = (
                getattr(usage, "completion_tokens", output_tokens) or output_tokens
            )

    total_text = "".join(full_text)
    elapsed = int((time.perf_counter() - start_time) * 1000)

    cost = (
        estimate_cost(use_model, input_tokens, output_tokens)
        if (input_tokens or output_tokens)
        else {
            "model": use_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": 0.0,
            "pricing_per_1k": MODEL_PRICING.get(use_model, {}),
        }
    )
    updated_history = messages + [{"role": "assistant", "content": total_text}]

    return {
        "answer": total_text,
        "history": updated_history,
        "_meta": {
            "model": use_model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": cost.get("total_cost_usd", 0.0),
            "elapsed": elapsed,
        },
    }
