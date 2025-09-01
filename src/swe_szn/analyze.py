from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from swe_szn.config import settings
from swe_szn.services import firecrawl, resume
from swe_szn.services.openai import compare_jd_vs_resume


def run(
    url: str,
    resume_path: str,
    *,
    prompt_name: str,
    model: str,
    force: bool,
    chat_after: bool,
) -> dict:
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        transient=True,
        expand=True,
    ) as progress:
        scrape_task = progress.add_task(
            "[yellow]swe-eping the job posting...", total=None
        )
        jd_markdown = firecrawl.scrape_job(url)
        progress.update(scrape_task, completed=1, total=1)

        parse_task = progress.add_task("[yellow]swe-eping the resume...", total=None)
        resume_text = resume.parse_resume(resume_path)
        progress.update(parse_task, completed=1, total=1)

        # AI analysis
        ai_task = progress.add_task("[cyan]summoning the swe-eeper...", total=None)
        result = compare_jd_vs_resume(
            jd_markdown=jd_markdown,
            resume_text=resume_text,
            model=model,
            job_url=url,
            cache_dir=settings().cache_dir("openai"),
            force=force,
            prompt_name=prompt_name,
        )
        progress.update(ai_task, completed=1, total=1)

    # attach context for optional chat follow-up
    if chat_after:
        result.setdefault("_context", {})
        result["_context"]["jd_markdown"] = jd_markdown
        result["_context"]["resume_text"] = resume_text

    return result
