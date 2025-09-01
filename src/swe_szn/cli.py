import json
from pathlib import Path

import typer

from swe_szn.config import apply as config_apply
from swe_szn.config import snapshot
from swe_szn.ui import markdown, rich
from swe_szn.ui.config import check as config_check
from swe_szn.ui.config import setup as config_setup

app = typer.Typer(help="swe-szn CLI: analyze resumes vs job listings")
config_app = typer.Typer(help="configuration commands")
app.add_typer(config_app, name="config")


@app.command()
def analyze_job(
    resume_path: Path,
    url: str = typer.Argument(
        None, help="Job posting URL (will prompt if not provided)"
    ),
    export: str = typer.Option(
        "none", "--export", "-e", help="Export format: json|md|none"
    ),
    prompt: str = typer.Option(
        "swe_intern", "--prompt", "-p", help="Prompt template to use"
    ),
    model: str = typer.Option(None, "--model", "-m", help="OpenAI model override"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force re-run, ignore cache"
    ),
    chat_after: bool = typer.Option(
        False, "--chat", help="Chat about the analysis afterwards"
    ),
    chat_prompt: str = typer.Option(
        "swe_intern_chat",
        "--chat-prompt",
        "-cp",
        help="Prompt template to use for the chat",
    ),
):
    from swe_szn import analyze, chat

    # prompt for job url
    if not url:
        url = typer.prompt("Enter the job posting URL")

    result = analyze.run(
        url=str(url),
        resume_path=str(resume_path),
        prompt_name=prompt,
        model=model,
        force=force,
        chat_after=chat_after,
    )

    rich.print_overview(result)

    if export == "json":
        json_string = json.dumps(result, indent=2)
        rich.console.print_json(json=json_string)
    elif export == "md":
        md = markdown.tov_markdown(result)
        Path("outputs").mkdir(exist_ok=True)
        out_path = Path("outputs") / f"analysis_{result['_meta']['key']}.md"
        out_path.write_text(md, encoding="utf-8")
        rich.console.print(f"[blue]Exported Markdown to {out_path}[/blue]")

    if chat_after:
        chat.run(result, model, chat_prompt)


@config_app.command("setup")
def setup_config():
    st = snapshot()
    updates = config_setup(st)
    if updates:
        config_apply(updates)
    config_check(snapshot())


@config_app.command("check")
def check_config():
    config_check(snapshot())


@config_app.command("set")
def set_config(
    key: str = typer.Argument(help="Configuration key (e.g., OPENAI_API_KEY)"),
    value: str = typer.Argument(help="Configuration value"),
):
    config_apply({key: value})
    config_check(snapshot())


if __name__ == "__main__":
    app()
