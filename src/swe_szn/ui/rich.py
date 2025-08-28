from rich.console import Console, Group
from rich.columns import Columns
from rich.segment import Segment
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()


def _bar(value: int, width: int = 20) -> str:
    try:
        v = max(0, min(100, int(value)))
    except Exception:
        v = 0
    filled = int((v / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _panel_job(result: dict) -> Panel:
    job = result.get("job", {}) or {}
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    url = job.get("url") or (result.get("_meta", {}) or {}).get("job_url", "")

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    role_line = " ".join(
        x for x in [title, "@" if company and title else "", company] if x
    )
    if role_line:
        table.add_row("Role", role_line)
    if location:
        table.add_row("Location", location)
    if url:
        table.add_row("URL", f"[link={url}]{url}[/link]")

    return Panel(table, title="Job", border_style="blue", padding=(0, 2), expand=True)


def _panel_keywords(result: dict):
    kws = result.get("missing_keywords", []) or []
    if not kws:
        return None
    table = Table(
        title="Missing Keywords",
        show_header=False,
        expand=True,
        pad_edge=False,
        padding=(0, 0),
    )
    table.add_column("Keyword", style="yellow")
    for k in kws:
        table.add_row(k)
    return table


def _panel_scores(result: dict):
    scores = result.get("scores", {}) or {}
    match_score = result.get("match_score", 0)
    table = Table(title="Scores", show_header=True, expand=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="white", justify="right")
    table.add_column("Bar", style="green")
    rows = [
        ("overall", match_score),
        ("skills_match", scores.get("skills_match", 0)),
        ("experience_alignment", scores.get("experience_alignment", 0)),
        ("keyword_coverage", scores.get("keyword_coverage", 0)),
    ]
    for name, val in rows:
        try:
            sval = int(val)
        except Exception:
            sval = 0
        table.add_row(name, f"{sval}/100", _bar(sval))
    return table


def _panel_summary(result: dict):
    summary = result.get("summary", "")
    if not summary:
        return None
    left_aligned = Text(summary, justify="left")
    return Panel(
        left_aligned, title="Summary", border_style="cyan", padding=(0, 1), expand=True
    )


def _panel_strengths_gaps(result: dict):
    table = Table(title="Analysis Summary", expand=True, pad_edge=False, padding=(0, 0))
    table.add_column("Strengths", style="green")
    table.add_column("Gaps", style="red")
    strengths = result.get("strong_matches", []) or []
    gaps = result.get("gaps", []) or []
    max_len = max(len(strengths), len(gaps))
    for i in range(max_len):
        s = strengths[i] if i < len(strengths) else ""
        g = gaps[i] if i < len(gaps) else ""
        table.add_row(s, g)
    return table


def _panels_bullets(result: dict):
    bullets_struct = result.get("bullets") or {}
    achieved = (
        bullets_struct.get("achieved") if isinstance(bullets_struct, dict) else None
    )
    targets = (
        bullets_struct.get("targets") if isinstance(bullets_struct, dict) else None
    )
    renderables = []
    if isinstance(achieved, list) and achieved:
        t1 = Table(
            title="Tailored Bullets — Achieved",
            show_header=False,
            expand=True,
            pad_edge=False,
            padding=(0, 0),
        )
        t1.add_column("Bullet", style="white")
        for b in achieved:
            t1.add_row(str(b))
        renderables.append(t1)
    if isinstance(targets, list) and targets:
        t2 = Table(
            title="Tailored Bullets — Targets",
            show_header=False,
            expand=True,
            pad_edge=False,
            padding=(0, 0),
        )
        t2.add_column("Goal", style="yellow")
        for b in targets:
            t2.add_row(str(b))
        renderables.append(t2)
    if not renderables:
        bullets = result.get("tailored_bullets", []) or []
        if bullets:
            t = Table(
                title="Tailored Bullets",
                show_header=False,
                expand=True,
                pad_edge=False,
                padding=(0, 0),
            )
            t.add_column("Bullet", style="white")
            for b in bullets:
                t.add_row(b)
            renderables.append(t)
    return renderables


def print_overview(result: dict):
    left_items = [_panel_job(result), _panel_scores(result)]
    kws_panel = _panel_keywords(result)
    if kws_panel is not None:
        left_items.append(kws_panel)
    left_group = Group(*left_items)

    # Build right column (summary + strengths/gaps + bullets)
    right_items = []
    summary_panel = _panel_summary(result)
    if summary_panel is not None:
        right_items.append(summary_panel)
    right_items.append(_panel_strengths_gaps(result))
    right_items.extend(_panels_bullets(result))
    right_group = Group(*right_items)

    total_width = console.size.width
    gap = 2
    offset = 5
    left_width = max(40, total_width // 3 - gap)
    right_width = max(40, total_width - left_width - gap - offset)

    left_panel = Panel(
        left_group, padding=(0, 0), width=left_width, border_style="blue"
    )
    right_panel = Panel(
        right_group, padding=(0, 0), width=right_width, border_style="cyan"
    )

    # Equalize heights by measuring rendered lines
    def _measure_height(panel: Panel, width: int) -> int:
        segments = console.render(panel, console.options.update(width=width))
        return len(list(Segment.split_lines(segments)))

    target_height = max(
        _measure_height(left_panel, left_width),
        _measure_height(right_panel, right_width),
    )
    left_panel = Panel(
        left_group,
        padding=(0, 0),
        width=left_width,
        height=target_height,
        border_style="blue",
    )
    right_panel = Panel(
        right_group,
        padding=(0, 0),
        width=right_width,
        height=target_height,
        border_style="cyan",
    )

    cols = Columns([left_panel, right_panel], equal=False, expand=False, padding=gap)
    console.print(cols)
