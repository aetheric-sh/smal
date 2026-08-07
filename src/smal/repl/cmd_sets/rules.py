"""Module defining the `rules` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.repl.completers import rule_completer
from smal.repl.helpers import echo_table, get_parent_app, get_persistence
from smal.utilities.rules import ALL_RULES

if TYPE_CHECKING:
    import argparse

_rules_parser = cmd2.Cmd2ArgumentParser()
_rules_parser.add_subparsers(title="subcommand", help="subcommand help")

_list_parser = cmd2.Cmd2ArgumentParser()

_enable_parser = cmd2.Cmd2ArgumentParser()
_enable_parser.add_argument("name", type=str, completer=rule_completer, help="The name of the rule to enable, or 'all' to enable all.")


class EnableArgs(BaseModel):
    """Model describing the arguments to the enable command."""

    name: str


_disable_parser = cmd2.Cmd2ArgumentParser()
_disable_parser.add_argument("name", type=str, completer=rule_completer, help="The name of the rule to disable, or 'all' to disable all.")


class DisableArgs(BaseModel):
    """Model describing the arguments to the disable command."""

    name: str


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
        parsed_args = EnableArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if parsed_args.name.lower() == "all":
            for r in ALL_RULES:
                persistence.enable_rule(r.name, True, write_to_file=False)
            parent_app.print_success("All rules have been enabled.")
        else:
            rule = next((r for r in ALL_RULES if r.name == parsed_args.name), None)
            if rule is None:
                parent_app.print_error(f"Unknown rule '{parsed_args.name}'. Run the `rules list` command for list of valid rules.")
                return
            persistence.enable_rule(rule.name, True, write_to_file=False)
            parent_app.print_success(f"Rule '{rule.name}' has been enabled.")
        persistence.save()

    @cmd2.as_subcommand_to("rules", "disable", _disable_parser, help="Disable 1 or more rules from being evaluated.")
    def rules_disable(self, args: argparse.Namespace) -> None:
        """Disable 1 or more rules to be evaluated against the active SMAL machine.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        Raises:
            RuntimeError: If the `RulesCmdSet` is not registered with a parent cmd2 application.

        """
        parsed_args = DisableArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if parsed_args.name.lower() == "all":
            for r in ALL_RULES:
                persistence.enable_rule(r.name, False, write_to_file=False)
            parent_app.print_success("All rules have been disabled.")
        else:
            rule = next((r for r in ALL_RULES if r.name == parsed_args.name), None)
            if rule is None:
                parent_app.print_error(f"Unknown rule '{parsed_args.name}'. Run the `rules list` command for list of valid rules.")
                return
            persistence.enable_rule(rule.name, False, write_to_file=False)
            parent_app.print_success(f"Rule '{rule.name}' has been disabled.")
        persistence.save()

    @cmd2.as_subcommand_to(
        "rules",
        "list",
        _list_parser,
        help="List all rules that SMAL can evaluate against state machines. Invoking `smal rules` invokes this as well.",
    )
    def rules_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """List all available rules in the SMAL ruleset and their statuses.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        persistence = get_persistence()
        # Persistence should always have all rules in its rules dict
        rules = [next(r for r in ALL_RULES if r.name == rule_name) for rule_name in persistence.rules]
        rules_data = [[r.name, str(persistence.is_rule_enabled(r)), r.description] for r in rules]
        echo_table(
            "SMAL Ruleset",
            ["Name", "Enabled", "Description"],
            rules_data,
            col_metadata={
                "Name": {"style": "cyan"},
                "Enabled": {"style": "green"},
                "Description": {"style": "yellow"},
            },
        )
