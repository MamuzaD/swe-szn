import typer
from pathlib import Path
from swe_szn import analyze
from swe_szn.ui import markdown, rich
import json

app = typer.Typer(help="swe-szn CLI: analyze resumes vs job listings")

@app.command()
def analyze_job(
    resume_path: Path,
    url: str = typer.Argument(None, help="Job posting URL (will prompt if not provided)"),
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
):
    # prompt for job url
    if not url:
        url = typer.prompt("Enter the job posting URL")
    
    result = analyze.run(
        url=str(url),
        resume_path=str(resume_path),
        export=export,
        prompt_name=prompt,
        model=model,
        force=force,
    )

    rich.print_overview(result)

    if export == "json":
        print(json.dumps(result, indent=2))
    elif export == "md":
        md = markdown.to_markdown(result)
        Path("outputs").mkdir(exist_ok=True)
        out_path = Path("outputs") / f"analysis_{result['_meta']['key']}.md"
        out_path.write_text(md, encoding="utf-8")
        rich.console.print(f"[blue]Exported Markdown to {out_path}[/blue]")

if __name__ == "__main__":
    app()