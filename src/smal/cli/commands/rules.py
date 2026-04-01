from __future__ import annotations  # Until Python 3.14

import typer
from rich.console import Console

from smal.cli.commands.helpers import echo_table
from smal.utilities.rules import ALL_RULES

console = Console()

rules_app = typer.Typer(help="Inspect and manage SMAL validation rules.")


@rules_app.callback(invoke_without_command=True)
def rules_root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_rules_cmd)


@rules_app.command("list", help="List all rules that SMAL can evaulate against state machines. Invoking `smal rules` invokes this as well.")
def list_rules_cmd() -> None:
    echo_table("SMAL Ruleset", ["Name", "Enabled", "Description"], [[rule.name, str(rule.enabled), rule.description] for rule in ALL_RULES])


@rules_app.command("disable", help="Disable 1 or more rules from being evaluated.")
def disable_rule_cmd(name: str = typer.Argument(..., help="The name of the rule to disable, or 'all' to disable all.")) -> None:
    if name.lower == "all":
        for r in ALL_RULES:
            r.enabled = False
    else:
        rule = next((r for r in ALL_RULES if r.name == name), None)
        if rule is None:
            typer.BadParameter(f"Unknown rule '{name}'. Run the `smal rules` command for list of valid rules.")
        else:
            rule.enabled = False


@rules_app.command("enable", help="Enable 1 or more rules to be evaluated.")
def enable_rule_cmd(name: str = typer.Argument(..., help="The name of the rule to enable, or 'all' to enable all.")) -> None:
    if name.lower == "all":
        for r in ALL_RULES:
            r.enabled = True
    else:
        rule = next((r for r in ALL_RULES if r.name == name), None)
        if rule is None:
            typer.BadParameter(f"Unknown rule '{name}'. Run the `smal rules` command for list of valid rules.")
        else:
            rule.enabled = True
