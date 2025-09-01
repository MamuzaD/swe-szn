from swe_szn.services import firecrawl, resume
from swe_szn.services.openai import compare_jd_vs_resume
from swe_szn.config import settings


def run(
    url: str,
    resume_path: str,
    *,
    export: str = "md",
    prompt_name: str,
    model: str,
    force: bool,
    chat_after: bool,
) -> dict:
    jd_markdown = firecrawl.scrape_job(url)
    resume_text = resume.parse_resume(resume_path)

    result = compare_jd_vs_resume(
        jd_markdown=jd_markdown,
        resume_text=resume_text,
        model=model,
        job_url=url,
        cache_dir=settings().cache_dir("openai"),
        force=force,
        prompt_name=prompt_name,
    )

    # attach context for optional chat follow-up
    if chat_after:
        result.setdefault("_context", {})
        result["_context"]["jd_markdown"] = jd_markdown
        result["_context"]["resume_text"] = resume_text

    return result
