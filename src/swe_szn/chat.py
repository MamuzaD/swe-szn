import re
from typing import Optional

import typer
from rich.align import Align
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from swe_szn.services.openai import chat_about_job_stream
from swe_szn.ui import rich

_ANSI_SEQ_RE = re.compile(
    r"(?:\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-Z\\-_]|\x1b\][0-?]*.*?(?:\x07|\x1b\\)|\x1b[P^_].*?\x1b\\|\^\[[0-?]*[ -/]*[@-~])",
    re.DOTALL,
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def validate_input(input: str) -> Optional[str]:
    cleaned = input.strip()
    if not cleaned:
        return None

    # strip ANSI/CSI/OSC/DC
    cleaned = _ANSI_SEQ_RE.sub("", cleaned).strip()
    # remove remaining control characters
    cleaned = _CONTROL_CHARS_RE.sub("", cleaned).strip()

    if not cleaned:
        return None

    return cleaned


def run(result, model, prompt):
    ctx = result.get("_context") or {}
    jd: str = ctx.get("jd_markdown", "")
    resume: str = ctx.get("resume_text", "")

    if not jd or not resume:
        rich.console.print("[red]Missing context for chat.[/red]")
        raise SystemExit(1)
    rich.console.print(
        "[magenta]Chat mode. Type your question ('exit' | 'q' to quit).[/magenta]\n"
        "[dim]Tip: Ask e.g., Why are you interested in this role? or How do I tailor a bullet?[/dim]"
    )

    conversation_history = None

    # chat prompt loop
    while True:
        q = typer.prompt("➜")
        q = validate_input(q)
        if not q:
            continue
        if q.strip().lower() in {"exit", "quit", "q"}:
            break

        gen = chat_about_job_stream(
            q,
            jd_markdown=jd,
            resume_text=resume,
            model=model or None,
            prompt_name=prompt,
            history=conversation_history,
        )

        panel = Panel(
            "",
            title="swe-eeper",
            subtitle="the swe-szn sweeper sweeping your jobs & resumes",
            width=120,
            expand=True,
            border_style="magenta",
            padding=(1, 2),
        )
        centered_panel = Align.center(panel)  # center the panel

        chunks = []
        current_text = ""
        # stream the answer using Rich live
        with Live(centered_panel, refresh_per_second=10):
            while True:
                try:
                    chunk = next(gen)
                    chunks.append(chunk)
                    current_text = "".join(chunks)
                    markdown_text = Markdown(current_text)
                    panel.renderable = markdown_text
                except StopIteration as e:
                    res = e.value or {}
                    conversation_history = res.get("history")
                    cost = (res.get("_meta") or {}).get("total_cost_usd")
                    elapsed = ((res.get("_meta") or {}).get("elapsed", 0)) / 1000.0
                    if cost:
                        # add cost before ending the live
                        cost_text = (
                            f"\n\n[dim]~ [cyan]${cost:.4f}[/cyan][/dim]\n"
                            f"[dim]~ [blue]{elapsed:.2f}s[/blue][/dim]"
                        )
                        markdown_text = Markdown(current_text)
                        panel.renderable = Group(markdown_text, cost_text)
                    break
