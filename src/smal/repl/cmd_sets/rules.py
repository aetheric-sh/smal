"""Module defining the `rules` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING

import cmd2

from smal.repl.helpers import echo_table, get_parent_app, get_persistence
from smal.utilities.rules import ALL_RULES

if TYPE_CHECKING:
    import argparse

_rules_parser = cmd2.Cmd2ArgumentParser()
_rules_parser.add_subparsers(title="subcommand", help="subcommand help")

_list_parser = cmd2.Cmd2ArgumentParser()

_enable_parser = cmd2.Cmd2ArgumentParser()
_enable_parser.add_argument("name", type=str, help="The name of the rule to enable, or 'all' to enable all.")

_disable_parser = cmd2.Cmd2ArgumentParser()
_disable_parser.add_argument("name", type=str, help="The name of the rule to disable, or 'all' to disable all.")


class RulesCmdSet(cmd2.CommandSet):
    """Command set for handling rules in the SMAL REPL."""

    @cmd2.with_argparser(_rules_parser)
    def do_rules(self, args: argparse.Namespace) -> None:
        """Manage SMAL state machine rules.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("rules")

    @cmd2.as_subcommand_to("rules", "enable", _enable_parser, help="Enable 1 or more rules to be evaluated.")
    def rules_enable(self, args: argparse.Namespace) -> None:
        """Enable 1 or more rules to be evaluated against the active SMAL machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `RulesCmdSet` is not registered with a parent cmd2 application.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        persistence = get_persistence()
        if args.name.lower() == "all":
            for r in ALL_RULES:
                persistence.enable_rule(r.name, True, write_to_file=False)
            console.print("[green]All rules have been enabled.[/green]")
        else:
            rule = next((r for r in ALL_RULES if r.name == args.name), None)
            if rule is None:
                console.print(f"[bold red]Error: Unknown rule '{args.name}'. Run the `smal rules` command for list of valid rules.[/bold red]")
                return
            persistence.enable_rule(rule.name, True, write_to_file=False)
            console.print(f"[green]Rule '{rule.name}' has been enabled.[/green]")
        persistence.save()

    @cmd2.as_subcommand_to("rules", "disable", _disable_parser, help="Disable 1 or more rules from being evaluated.")
    def rules_disable(self, args: argparse.Namespace) -> None:
        """Disable 1 or more rules to be evaluated against the active SMAL machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `RulesCmdSet` is not registered with a parent cmd2 application.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        console = parent_app.get_console()
        persistence = get_persistence()
        if args.name.lower() == "all":
            for r in ALL_RULES:
                persistence.enable_rule(r.name, False, write_to_file=False)
            console.print("[green]All rules have been disabled.[/green]")
        else:
            rule = next((r for r in ALL_RULES if r.name == args.name), None)
            if rule is None:
                console.print(f"[bold red]Error: Unknown rule '{args.name}'. Run the `smal rules` command for list of valid rules.[/bold red]")
                return
            persistence.enable_rule(rule.name, False, write_to_file=False)
            console.print(f"[green]Rule '{rule.name}' has been disabled.[/green]")
        persistence.save()

    @cmd2.as_subcommand_to("rules", "list", _list_parser, help="List all rules that SMAL can evaluate against state machines. Invoking `smal rules` invokes this as well.")
    def rules_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """List all available rules in the SMAL ruleset and their statuses.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        persistence = get_persistence()
        # Persistence should always have all rules in its rules dict
        rules = [next(r for r in ALL_RULES if r.name == rule_name) for rule_name in persistence.rules]
        rules_data = [(r.name, str(persistence.is_rule_enabled(r)), r.description) for r in rules]
        echo_table("SMAL Ruleset", ["Name", "Enabled", "Description"], rules_data)
