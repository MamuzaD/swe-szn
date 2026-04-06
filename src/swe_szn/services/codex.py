import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator, Optional

from swe_szn.config import settings
from swe_szn.prompts import load_prompt


def provider_name() -> str:
    return "codex"


def default_model() -> str:
    return settings().codex_model


def _exec(prompt: str, *, model: Optional[str] = None) -> tuple[str, int]:
    use_model = model or default_model()
    cmd = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check"]
    if use_model:
        cmd.extend(["--model", use_model])

    with tempfile.TemporaryDirectory(prefix="swe-szn-codex-") as tmp_dir:
        out_path = Path(tmp_dir) / "last-message.txt"
        cmd.extend(["--output-last-message", str(out_path), prompt])

        start_time = time.perf_counter()
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=Path.cwd(),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Codex CLI not found. Install it with `npm i -g @openai/codex` and sign in with your ChatGPT account."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            details = stderr or stdout or "unknown codex error"
            raise RuntimeError(f"Codex CLI request failed: {details}") from exc

        elapsed = int((time.perf_counter() - start_time) * 1000)
        if out_path.exists():
            return out_path.read_text(encoding="utf-8").strip(), elapsed

        fallback = (completed.stdout or "").strip()
        return fallback, elapsed


def compare_jd_vs_resume(
    jd_markdown: str,
    resume_text: str,
    *,
    prompt_name: str = "swe_intern",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = load_prompt(prompt_name)
    system_prompt = prompt["system"]
    user_prompt = prompt["user_template"].format(
        job=jd_markdown[:12000], resume=resume_text[:12000]
    )
    combined_prompt = (
        f"System instructions:\n{system_prompt}\n\nUser request:\n{user_prompt}\n"
    )
    content, elapsed = _exec(combined_prompt, model=model)

    return {
        "content": content,
        "elapsed": elapsed,
        "model": model or default_model(),
    }


def chat_about_job_stream(
    question: str,
    *,
    jd_markdown: str,
    resume_text: str,
    model: Optional[str] = None,
    prompt_name: str = "swe_intern_chat",
    history: Optional[list] = None,
) -> Generator[str, None, Dict[str, Any]]:
    prompt = load_prompt(prompt_name)
    system_prompt = prompt["system"]
    context_prompt = prompt["user_template"].format(
        job=jd_markdown[:12000], resume=resume_text[:12000]
    )

    transcript_lines = []
    if history:
        for message in history:
            role = message.get("role", "user").upper()
            content = message.get("content", "")
            transcript_lines.append(f"{role}:\n{content}")

    transcript_lines.append(f"USER:\n{question}")
    transcript = "\n\n".join(transcript_lines)
    combined_prompt = (
        f"System instructions:\n{system_prompt}\n\n"
        f"Static context:\n{context_prompt}\n\n"
        "Conversation so far:\n"
        f"{transcript}\n\n"
        "Answer the most recent user question in Markdown."
    )

    answer, elapsed = _exec(combined_prompt, model=model)
    updated_history = (history or []) + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]

    for chunk in re.findall(r"\S+\s*|\n", answer):
        yield chunk

    return {
        "answer": answer,
        "history": updated_history,
        "_meta": {
            "model": model or default_model(),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_cost_usd": 0.0,
            "elapsed": elapsed,
            "provider": provider_name(),
        },
    }
