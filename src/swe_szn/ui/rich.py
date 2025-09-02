from typing import Optional

from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.segment import Segment
from rich.style import StyleType
from rich.table import Table
from rich.text import Text

console = Console()

# --- constants ---
MIN_PANEL_WIDTH = 40
PANEL_GAP = 2
PANEL_DIVIDER = 3


# equalize heights by measuring rendered lines
def _measure_height(panel: RenderableType, width: int) -> int:
    segments = console.render(panel, console.options.update(width=width))
    return len(list(Segment.split_lines(segments)))


def _get_width(total_width: int, divider: int, gap: int, min_width: int) -> int:
    width = max(min_width, total_width // divider - gap)
    return width


def _get_global_left_right() -> tuple[int, int]:
    left_width = _get_width(
        console.size.width, PANEL_DIVIDER, PANEL_GAP, MIN_PANEL_WIDTH
    )

    right_width = max(MIN_PANEL_WIDTH, console.size.width - left_width - PANEL_GAP)

    return left_width, right_width


def side_by_side(
    left: RenderableType,
    right: RenderableType,
    *,
    left_title: Optional[str] = None,
    right_title: Optional[str] = None,
    left_border_style: StyleType = "",
    right_border_style: StyleType = "",
    total_width: int,
    gap: int = 0,
    divider: int = 2,
    min_left_width: Optional[int] = None,
    min_right_width: Optional[int] = None,
) -> RenderableType:
    # get left and right widths
    left_width = _get_width(
        total_width, divider, gap, min_left_width or MIN_PANEL_WIDTH
    )
    # right side gets remaining space after left panel and gap
    right_width = max(
        min_right_width or MIN_PANEL_WIDTH, total_width - left_width - gap
    )

    target_height = (
        max(
            _measure_height(left, left_width),
            _measure_height(right, right_width),
        )
        + 2  # necessary to avoid cutoff
    )
    left_panel = Panel(
        renderable=left,
        title=left_title,
        padding=(0, 0),
        width=left_width,
        height=target_height,
        border_style=left_border_style,
    )
    right_panel = Panel(
        renderable=right,
        title=right_title,
        padding=(0, 0),
        width=right_width,
        height=target_height,
        border_style=right_border_style,
    )

    cols = Columns([left_panel, right_panel], equal=False, expand=False, padding=gap)

    return cols


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
    season = job.get("season", {}).get("time", "")

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    if title:
        table.add_row("Role", title)
    if company:
        table.add_row("Company", company)
    if location:
        table.add_row("Location", location)
    if season:
        table.add_row("Season", season)
    if url:
        table.add_row("URL", f"[link={url}]{url}[/link]")

    return Panel(table, title="Job", border_style="blue", padding=(0, 2), expand=True)


def _panel_keywords(result: dict):
    keywords = result.get("keywords", {}) or {}
    missing = keywords.get("missing", []) or []
    matched = keywords.get("matched", []) or []

    if not missing and not matched:
        return None

    must_have_missing = [
        m for m in missing if isinstance(m, dict) and m.get("priority") == "must_have"
    ]
    preferred_missing = [
        m for m in missing if isinstance(m, dict) and m.get("priority") == "preferred"
    ]

    matched_list = "\n".join([f"- {k}" for k in matched]) if matched else ""

    missing_list_parts = []
    if must_have_missing:
        missing_list_parts.append("Must haves:")
        missing_list_parts.extend(
            [f"- {m.get('token', '')}" for m in must_have_missing]
        )
    if preferred_missing:
        missing_list_parts.append("Preferred:")
        missing_list_parts.extend(
            [f"- {m.get('token', '')}" for m in preferred_missing]
        )
    missing_list = "\n".join(missing_list_parts) if missing_list_parts else ""

    # get the left side width
    left_side, _ = _get_global_left_right()

    return side_by_side(
        left=matched_list,
        right=missing_list,
        left_title="Matched",
        right_title="Missing",
        left_border_style="green",
        right_border_style="red",
        total_width=left_side - 4,
        gap=0,
        min_left_width=33,
        min_right_width=33,
    )


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
    strengths = result.get("strong_matches", []) or []
    gaps = result.get("gaps", []) or []

    # handle strengths
    strengths_list_parts = []
    for s in strengths:
        strengths_list_parts.append(f"- {s}\n")
    strengths_list = "".join(strengths_list_parts)

    # handle gaps
    gaps_list_parts = []
    for g in gaps:
        text_content = f"- {g}\n"
        gaps_list_parts.append(text_content)
    gaps_list = "".join(gaps_list_parts)

    # get the right side width
    _, right_side = _get_global_left_right()

    strengths_gaps = side_by_side(
        left=strengths_list,
        right=gaps_list,
        left_title="Strengths",
        right_title="Gaps",
        total_width=right_side - 2,
        min_left_width=50,
        min_right_width=50,
        left_border_style="green dim",
        right_border_style="red dim",
    )

    return strengths_gaps


def _panel_quick_wins(result: dict):
    keywords = result.get("keywords", {}) or {}
    quick_wins = keywords.get("quick_wins", []) or []

    if not quick_wins:
        return None

    quick_wins_list = "\n".join([f"- {w}" for w in quick_wins])
    content = Text(quick_wins_list, justify="left")
    return Panel(
        content, title="Quick Wins", border_style="yellow", padding=(0, 1), expand=True
    )


def _panel_cost(result: dict):
    meta = result.get("_meta", {}) or {}
    cost = meta.get("cost_estimate", {}) or {}

    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    total_cost = cost.get("total_cost_usd", 0)
    input_tokens = cost.get("input_tokens", 0)
    output_tokens = cost.get("output_tokens", 0)
    if input_tokens and output_tokens:
        cost_text = f"${total_cost:.4f} ({input_tokens} → {output_tokens} tokens)"
    else:
        cost_text = f"${total_cost:.4f}"
    table.add_row("Cost", cost_text)

    model = meta.get("model", "unknown")
    table.add_row("Model", model)

    elapsed = meta.get("elapsed")
    # elapsed time (ms) from _meta
    if isinstance(elapsed, (int, float)) and elapsed >= 0:
        time = elapsed / 1000.0
        elapsed_text = f"{time:.2f}s"
        table.add_row("Time", elapsed_text)

    return Panel(
        table,
        title="API Cost & Model",
        border_style="blue",
        padding=(0, 2),
        expand=True,
    )


def print_overview(result: dict):
    left_items = [
        _panel_job(result),
        _panel_scores(result),
    ]
    kws_panel = _panel_keywords(result)
    if kws_panel is not None:
        left_items.append(kws_panel)
    left_group = Group(*left_items, _panel_cost(result))

    right_items = []
    summary_panel = _panel_summary(result)
    if summary_panel is not None:
        right_items.append(summary_panel)

    strengths_gaps_table = _panel_strengths_gaps(result)
    right_items.append(strengths_gaps_table)

    quick_wins_panel = _panel_quick_wins(result)
    if quick_wins_panel is not None:
        right_items.append(quick_wins_panel)

    right_group = Group(*right_items)

    app = side_by_side(
        left=left_group,
        right=right_group,
        total_width=console.size.width,
        gap=PANEL_GAP,
        divider=PANEL_DIVIDER,
        left_border_style="blue",
        right_border_style="cyan",
        min_left_width=40,
        min_right_width=40,
    )

    console.print(app)
