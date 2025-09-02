def to_markdown(result: dict) -> str:
    scores = result.get("scores", {}) or {}
    meta = result.get("_meta", {}) or {}
    job = result.get("job", {})
    keywords = result.get("keywords", {})

    # header with job meta and overall score
    lines = [
        f"# {job.get('title', 'Job')} at {job.get('company', 'Company')}",
        f"**Location:** {job.get('location', 'Unknown')}",
        f"**Match Score:** {result.get('match_score', '?')}/100",
        "",
        "## Summary",
        result.get("summary", ""),
        "",
    ]

    # keywords section
    matched_keywords = keywords.get("matched", [])
    missing_keywords = keywords.get("missing", [])
    must_have_missing = [
        m
        for m in missing_keywords
        if isinstance(m, dict) and m.get("priority") == "must_have"
    ]
    preferred_missing = [
        m
        for m in missing_keywords
        if isinstance(m, dict) and m.get("priority") == "preferred"
    ]

    lines.extend(
        [
            "## Keywords",
            "",
            "### Matched",
            *[f"- {k}" for k in matched_keywords],
            "",
            "### Missing",
            *[f"- **{m.get('token', m)}** (must-have)" for m in must_have_missing],
            *[f"- {m.get('token', m)} (preferred)" for m in preferred_missing],
            "",
        ]
    )

    quick_wins = keywords.get("quick_wins", [])
    if quick_wins:
        lines.extend(
            [
                "### Quick Wins",
                *[f"- {w}" for w in quick_wins[:3]],
                "",
            ]
        )

    # Strong matches and gaps (max 5 each)
    strong_matches = result.get("strong_matches", [])[:5]
    gaps = result.get("gaps", [])[:5]

    if strong_matches:
        lines.extend(
            [
                "## Strong Matches",
                *[f"- {s}" for s in strong_matches],
                "",
            ]
        )

    if gaps:
        lines.extend(
            [
                "## Gaps",
                *[f"- {g}" for g in gaps],
                "",
            ]
        )

    # Meta information
    lines.extend(
        [
            "## Details",
            f"- **Skills Match:** {scores.get('skills_match', '?')}/100",
            f"- **Experience Alignment:** {scores.get('experience_alignment', '?')}/100",
            f"- **Keyword Coverage:** {scores.get('keyword_coverage', '?')}/100",
            f"- **Model:** {meta.get('model', '')}",
            f"- **Job URL:** {meta.get('job_url', '')}",
        ]
    )

    return "\n".join(lines)
