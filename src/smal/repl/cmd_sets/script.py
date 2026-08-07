"""Module defining the `script` command set for the SMAL REPL.

This allows users to construct and execute scripts (structured sequences of commands) within the REPL environment.
The `script` command set provides functionality to create, manage, and run scripts, enabling users to automate tasks and streamline their workflow.
"""

from __future__ import annotations  # Until Python 3.14

import argparse
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.repl.cmd_sets.msg import send_message
from smal.repl.completers import script_completer
from smal.repl.helpers import echo_table, get_parent_app, get_persistence, parse_key_value, parse_params
from smal.schemas.smal_script import SMALScript, SMALScriptCommand
from smal.utilities import constants as SMALConstants

if TYPE_CHECKING:
    from smal.repl.repl_like import REPLLike
    from smal.utilities.persistence import SMALPersistence

_script_parser = cmd2.Cmd2ArgumentParser()
_script_parser.add_subparsers(title="subcommand", help="subcommand help")

_load_parser = cmd2.Cmd2ArgumentParser()
_load_parser.add_argument("filepath", type=Path, completer=cmd2.Cmd.path_complete, help="The path to the script file to load.")
_load_parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite the existing script if it already exists in persistence.")


class LoadArgs(BaseModel):
    """Model describing the arguments to the load command."""

    filepath: Path
    overwrite: bool = False


_delete_parser = cmd2.Cmd2ArgumentParser()
_delete_parser.add_argument("script_name", type=str, completer=script_completer, help="The name of the script to delete, or all if 'all' is given.")


class DeleteArgs(BaseModel):
    """Model describing the arguments to the delete command."""

    script_name: str


_create_parser = cmd2.Cmd2ArgumentParser()
_create_parser.add_argument(
    "-o",
    "--output-file",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help="The filename to export the script to. If not specified, it will not be exported but saved to persistence.",
)


class CreateArgs(BaseModel):
    """Model describing the arguments to the create command."""

    output_file: Path | None = None


_run_parser = cmd2.Cmd2ArgumentParser()
_run_parser.add_argument("script_name", type=str, completer=script_completer, help="The name of the script to run.")


class RunArgs(BaseModel):
    """Model describing the arguments to the run command."""

    script_name: str


_list_parser = cmd2.Cmd2ArgumentParser()

_view_parser = cmd2.Cmd2ArgumentParser()
_view_parser.add_argument("script_name", type=str, completer=script_completer, help="The name of the script to view.")


class ViewArgs(BaseModel):
    """Model describing the arguments to the view command."""

    script_name: str


class ScriptCmdSet(cmd2.CommandSet):
    """Command set for the `script` command."""

    @cmd2.with_argparser(_script_parser)
    def do_script(self, args: argparse.Namespace) -> None:
        """Manage SMAL scripts.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("script")

    @cmd2.as_subcommand_to("script", "load", _load_parser, help="Load a script from a file.")
    def script_load(self, args: argparse.Namespace) -> None:
        """Load a script from a file.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = LoadArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        if not parsed_args.filepath.exists():
            parent_app.print_error(f"Script file '{parsed_args.filepath}' does not exist.")
            return
        console = parent_app.get_console()
        if parsed_args.filepath.is_dir():
            with console.status(f"[bold blue]Searching for SMAL machine definitions under {parsed_args.filepath}...[/bold blue]"):
                script_files = sorted(p for p in parsed_args.filepath.rglob(f"*{SMALConstants.SMAL_SCRIPT_FILE_EXTENSION}") if p.is_file())
            if not script_files:
                parent_app.print_warning(f"No SMAL script (`{SMALConstants.SMAL_SCRIPT_FILE_EXTENSION}`) files found under directory: {parsed_args.filepath}")
                return
            persistence = get_persistence()
            for script_file in script_files:
                script_from_file = self._load_script_from_file(script_file, parsed_args.overwrite, persistence, parent_app)
                if script_from_file is None:
                    parent_app.print_error(f"Failed to load script from file '{script_file}'.")
                    continue
        else:
            _ = self._load_script_from_file(parsed_args.filepath, parsed_args.overwrite, get_persistence(), parent_app)

    @cmd2.as_subcommand_to("script", "delete", _delete_parser, help="Delete a script from persistence by name, or all if 'all' is given.")
    def script_delete(self, args: argparse.Namespace) -> None:
        """Delete a script from persistence by name, or all if 'all' is given.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = DeleteArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if parsed_args.script_name.lower() == "all":
            persistence.scripts.clear()
            persistence.save()
            parent_app.print_success("All scripts have been deleted from persistence.", omit_heading=True)
        else:
            persistence.delete_script(parsed_args.script_name, save=True)
            parent_app.print_success(f"Script '{parsed_args.script_name}' has been deleted from persistence.", omit_heading=True)

    @cmd2.as_subcommand_to("script", "create", _create_parser, help="Create a new script dynamically from within the REPL.")
    def script_create(self, args: argparse.Namespace) -> None:
        """Create a new script dynamically from within the REPL.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = CreateArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        name = self._cmd.read_input("Script name: ").strip()
        while not name:
            parent_app.print_warning("Script name cannot be empty.")
            name = self._cmd.read_input("Script name: ").strip()
        parent_app.print_msg("Enter each command in the script. Type 'done' as the command body when finished.")
        commands: list[SMALScriptCommand] = []
        while True:
            cmd_body = self._cmd.read_input(f"Command {len(commands) + 1} (or 'done'): ").strip()
            if cmd_body.lower() == "done":
                break
            if not cmd_body:
                parent_app.print_warning("Command body cannot be empty.")
                continue
            metadata_input = self._cmd.read_input("Metadata as space-separated key=value pairs (optional): ").strip()
            try:
                metadata = parse_params([parse_key_value(item) for item in metadata_input.split()]) if metadata_input else {}
            except argparse.ArgumentTypeError as e:
                parent_app.print_error(f"Invalid metadata, command discarded: {e}")
                continue
            pre_delay_input = self._cmd.read_input("Pre-delay in ms (default 0): ").strip()
            post_delay_input = self._cmd.read_input("Post-delay in ms (default 0): ").strip()
            try:
                pre_delay_ms = int(pre_delay_input) if pre_delay_input else 0
                post_delay_ms = int(post_delay_input) if post_delay_input else 0
            except ValueError:
                parent_app.print_error("Pre-delay and post-delay must be integers, command discarded.")
                continue
            commands.append(SMALScriptCommand(cmd=cmd_body, metadata=metadata, pre_delay_ms=pre_delay_ms, post_delay_ms=post_delay_ms))
        if not commands:
            parent_app.print_warning("No commands were added; script creation cancelled.")
            return
        script = SMALScript(name=name, cmds=commands)
        persistence = get_persistence()
        persistence.add_script(script, overwrite=True, save=True)
        parent_app.print_success(f"Script '{name}' created with {len(commands)} command(s) and saved to persistence.", omit_heading=True)
        if parsed_args.output_file is not None:
            script.to_file(parsed_args.output_file)
            parent_app.print_success(f"Script '{name}' exported to '{parsed_args.output_file}'.", omit_heading=True)

    @cmd2.as_subcommand_to("script", "run", _run_parser, help="Run a script by name.")
    def script_run(self, args: argparse.Namespace) -> None:
        """Run a script by name.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = RunArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        script = persistence.scripts.get(parsed_args.script_name)
        if script is None:
            parent_app.print_error(f"No script found with the name '{parsed_args.script_name}'.")
            return
        parent_app.print_success(f"Running script '{script.name}' with {len(script.cmds)} command(s).", omit_heading=True)
        # Execute the script's commands in order. `send_message` is called directly (rather than building and
        # re-parsing a `msg send ...` statement) so message content and metadata containing quotes or other
        # shell-like special characters round-trip correctly.
        for command in script.cmds:
            for _ in range(command.exc_count):
                if command.pre_delay_ms > 0:
                    sleep(command.pre_delay_ms / 1000.0)
                parent_app.print_msg(f"[bold magenta]CMD> msg send {command.cmd!r} {command.metadata}[/bold magenta]")
                retval = send_message(parent_app, command.cmd, **command.metadata)
                if retval is not None:
                    parent_app.print_msg(f"{retval}")
                if command.post_delay_ms > 0:
                    sleep(command.post_delay_ms / 1000.0)

    @cmd2.as_subcommand_to("script", "list", _list_parser, help="List all scripts currently stored in persistence.")
    def script_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """List all scripts currently stored in persistence.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        if not persistence.scripts:
            parent_app.print_warning("No scripts found in persistence.")
            return
        script_data = [[script.name] for script in persistence.scripts.values()]
        echo_table(
            "Stored SMAL Scripts",
            ["Name"],
            script_data,
            col_metadata={
                "Name": {"style": "cyan"},
            },
        )

    @cmd2.as_subcommand_to("script", "view", _view_parser, help="View the details of a script by name.")
    def script_view(self, args: argparse.Namespace) -> None:
        """View the details of a script by name.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = ViewArgs.model_validate(vars(args))
        try:
            parent_app = get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
        persistence = get_persistence()
        script = persistence.scripts.get(parsed_args.script_name)
        if script is None:
            parent_app.print_error(f"No script found with the name '{parsed_args.script_name}'.")
            return
        # Display the script's details
        parent_app.print_msg(f"Script Name: {script.name}")
        cmd_count = sum(command.exc_count for command in script.cmds)
        parent_app.print_msg(f"Number of Commands: {cmd_count}")
        for idx, command in enumerate(script.cmds, start=1):
            for i in range(1, command.exc_count + 1):
                parent_app.print_msg(f"Command {idx} (Execution Iteration {i}): {command.cmd}")
                parent_app.print_msg(f"  Pre-delay (ms): {command.pre_delay_ms}")
                parent_app.print_msg(f"  Post-delay (ms): {command.post_delay_ms}")
                if command.metadata:
                    parent_app.print_msg("  Metadata:")
                    for k, v in command.metadata.items():
                        parent_app.print_msg(f"    {k}: {v}")

    def _load_script_from_file(self, filepath: Path, overwrite: bool, persistence: SMALPersistence, parent_app: REPLLike) -> SMALScript | None:
        """Load a script from a file.

        Args:
            filepath (Path): The path to the script file.
            overwrite (bool): Whether to overwrite an existing script in persistence.
            persistence (SMALPersistence): The persistence object to save the script to.
            parent_app (REPLLike): The parent REPL application for printing messages.

        Returns:
            SMALScript | None: The loaded script object, or None if loading failed.

        """
        try:
            script = SMALScript.from_file(filepath)
        except Exception as e:  # noqa: BLE001 - Catching blind exceptions here to provide a user-friendly error message in the REPL.
            parent_app.print_error(f"Failed to load script from file '{filepath}': {e}")
            return None
        persistence.add_script(script, overwrite=overwrite, save=True)
        parent_app.print_success(f"Script '{script.name}' loaded successfully from '{filepath}' and saved to persistence.", omit_heading=True)
        return script
