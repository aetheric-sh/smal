from rich.console import Console
from rich.table import Table

console = Console()


def echo_list(header: str, items: list[str], tab_size: int = 2, bold_header: bool = True) -> None:
    if bold_header:
        console.print(f"[bold]{header.rstrip(': ')}:[/bold]")
    else:
        console.print(f"{header.rstrip(': ')}:")
    original_tab_size = console.tab_size
    console.tab_size = tab_size
    for item in items:
        console.print(f"\t• {item}")
    console.tab_size = original_tab_size


def echo_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)
