"""Module defining the `msg` command set for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path  # noqa: TC003 - Pydantic requires this at runtime for type validation
from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.repl.helpers import get_parent_app, parse_key_value, parse_params
from smal.repl.target_module import TargetModule

if TYPE_CHECKING:
    import argparse

_msg_parser = cmd2.Cmd2ArgumentParser()
_msg_parser.add_subparsers(title="subcommand", help="subcommand help")

_send_parser = cmd2.Cmd2ArgumentParser()
_send_parser.add_argument("content", type=str, help="The content of the message to send to the actively connected SMAL device.")
_send_parser.add_argument("-m", "--module", type=TargetModule, help="The target module to use for sending the message.")
_send_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help="Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass additional parameters to the send function.",
)


class SendArgs(BaseModel):
    """Model describing the arguments to the send command."""

    content: str
    module: Path | None = None
    param: list[tuple[str, str]] | None = None


class MsgCmdSet(cmd2.CommandSet):
    """Command set for the `msg` command."""

    @cmd2.with_argparser(_msg_parser)
    def do_msg(self, args: argparse.Namespace) -> None:
        """Manage SMAL messages.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("msg")

    @cmd2.as_subcommand_to("msg", "send", _send_parser, help="Send a message to the actively connected SMAL device.")
    def msg_send(self, args: argparse.Namespace) -> None:
        """Send a message to the actively connected SMAL device.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = SendArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        active_connection = parent_app.get_active_connection()
        if active_connection is None:
            parent_app.print_error("No active connection found. Please connect to a device first using the `connect` command.")
            return
        if parsed_args.module is not None:
            parent_app.set_active_module(parsed_args.module)
        active_module = parent_app.get_active_module()
        if active_module is None:
            parent_app.print_error(
                "No active module found. Please load a module first using the `module load` command or provide one to this command with the `-m` option.",
            )
            return
        send_msg_fn = active_module.send_msg_fn
        if send_msg_fn is None:
            parent_app.print_error(f"The active module '{active_module.filepath}' does not support a sending messages.")
            return
        extra_kwargs = parse_params(parsed_args.param or [])
        retval = send_msg_fn(active_connection.device, parsed_args.content, **extra_kwargs)
        if retval is not None:
            parent_app.print_msg(f"{retval}")
