import typer
from rich.align import Align
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from swe_szn.ui import rich as ui


def _banner() -> None:
    title = Text("swe-szn • setup wizard", justify="center", style="bold black on blue")
    subtitle = Text("configure API keys and defaults", justify="center", style="cyan")
    ui.console.print(
        Align.center(Panel.fit(subtitle, title=title, border_style="blue"))
    )
    ui.console.print()


def _mask(val: str | None) -> str:
    if not val:
        return "[red]Not set[/red]"
    return val[:8] + "..." + val[-4:]


def prompt_update(
    key: str,
    title: str,
    current: str | None,
    *,
    secret: bool = False,
    required: bool = False,
    default: str | None = None,
) -> str | None:
    msg = (
        f"{title} (leave blank to keep existing)"
        if current
        else f"{title} ({'required' if required else 'optional'})"
    )
    while True:
        value = typer.prompt(msg, default=default or "", hide_input=secret)
        value = value.strip()
        if not value:
            if required and not current:
                ui.console.print("[yellow]value required[/yellow]")
                continue
            return None  # keep existing
        ui.console.print(f"[green]✓ set {key}[/green]")
        return value


def setup(status: dict) -> dict[str, str]:
    _banner()
    values = status.get("values", {})
    ui.console.print(
        "press [bold]Enter[/bold] to keep existing values. secrets are hidden"
    )
    ui.console.print(Rule(style="blue"))

    updates: dict[str, str] = {}

    # -- openai --
    v = prompt_update(
        "OPENAI_API_KEY",
        "OpenAI API Key",
        values.get("OPENAI_API_KEY"),
        secret=True,
        required=True,
    )
    if v:
        updates["OPENAI_API_KEY"] = v

    # -- firecrawl --
    v = prompt_update(
        "FIRECRAWL_API_KEY",
        "Firecrawl API Key",
        values.get("FIRECRAWL_API_KEY"),
        secret=True,
        required=False,
    )
    if v:
        updates["FIRECRAWL_API_KEY"] = v

    # -- openai model --
    v = prompt_update(
        "OPENAI_MODEL",
        "OpenAI model",
        values.get("OPENAI_MODEL"),
        default=values.get("OPENAI_MODEL") or "gpt-4o-mini",
    )
    if v:
        updates["OPENAI_MODEL"] = v

    # -- cache dir --
    v = prompt_update(
        "SWE_SZN_CACHE_DIR",
        "Cache directory",
        values.get("SWE_SZN_CACHE_DIR"),
        default=values.get("SWE_SZN_CACHE_DIR") or "cache",
    )
    if v:
        updates["SWE_SZN_CACHE_DIR"] = v

    ui.console.print(Rule(style="blue"))
    ui.console.print(Panel.fit("✓ configuration saved", border_style="green"))

    return updates


def check(status: dict) -> None:
    vals = status.get("values", {})
    table = Table(title="Configuration Status", show_header=False, expand=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("OPENAI_API_KEY", _mask(vals.get("OPENAI_API_KEY")))
    table.add_row("FIRECRAWL_API_KEY", _mask(vals.get("FIRECRAWL_API_KEY")))
    table.add_row("OPENAI_MODEL", vals.get("OPENAI_MODEL") or "")
    table.add_row("SWE_SZN_CACHE_DIR", vals.get("SWE_SZN_CACHE_DIR") or "")
    ui.console.print(table)

    missing = status.get("missing", [])
    complete = not missing
    ui.console.print(
        "\n[green]✓ configuration is complete![/green]"
        if complete
        else "\n[yellow]⚠ some settings are missing. run `swe-szn config setup`.[/yellow]"
    )
