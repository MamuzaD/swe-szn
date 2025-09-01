def to_markdown(result: dict) -> str:
    scores = result.get("scores", {}) or {}
    meta = result.get("_meta", {}) or {}
    lines = [
        "# Job Match Analysis",
        f"**Score:** {result.get('match_score', '?')}/100",
        "",
        "## Scores",
        f"- skills_match: {scores.get('skills_match', '?')}/100",
        f"- experience_alignment: {scores.get('experience_alignment', '?')}/100",
        f"- keyword_coverage: {scores.get('keyword_coverage', '?')}/100",
        "",
        "## Summary",
        result.get("summary", ""),
        "",
        "## Strengths",
        *[f"- {s}" for s in result.get("strong_matches", [])],
        "",
        "## Gaps",
        *[f"- {g}" for g in result.get("gaps", [])],
        "",
        "## Missing Keywords",
        *[f"- {k}" for k in result.get("missing_keywords", [])],
        "",
        "## Tailored Bullets",
        *[f"- {b}" for b in result.get("bullets", {}).get("achieved", [])],
        "",
        "## Meta",
        f"- Job URL: {meta.get('job_url', '')}",
        f"- Model: {meta.get('model', '')}",
        f"- Cache Key: {meta.get('key', '')}",
    ]
    return "\n".join(lines)
