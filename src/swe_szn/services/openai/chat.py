import time
from typing import Any, Dict, Generator, Optional

from swe_szn.config import settings
from swe_szn.prompts import load_prompt

from .client import get_client
from .models import estimate_cost, pricing, supports_temperature


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

    if supports_temperature(use_model):
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
            "pricing_per_1k": pricing(use_model),
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
