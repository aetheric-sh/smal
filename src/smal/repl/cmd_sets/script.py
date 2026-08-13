"""Module defining the `script` command set for the SMAL REPL.

This allows users to construct and execute scripts (structured sequences of commands) within the REPL environment.
The `script` command set provides functionality to create, manage, and run scripts, enabling users to automate tasks and streamline their workflow.
"""

from __future__ import annotations  # Until Python 3.14

import argparse
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Any

import cmd2
from pydantic import BaseModel

from smal.repl.cmd_sets.msg import send_message
from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.completers import script_completer
from smal.repl.helpers import echo_table, get_persistence, import_external_fn_from_file, parse_key_value, parse_params
from smal.schemas.smal_script import SMALScript, SMALScriptCommand
from smal.utilities import constants as SMALConstants

if TYPE_CHECKING:
    from smal.repl.repl_like import REPLLike
    from smal.repl.target_api import PythonScriptFn
    from smal.utilities.persistence import SMALPersistence


class SMALScriptLogger:
    """Logging facility passed to Python scripts so they can log to the same console as SMAL itself.

    Every call is also mirrored to the REPL's `SMALLogger` (unstyled, prefixed with the script name), so script
    activity is captured in the persistent log file alongside the rest of SMAL's logging, not just printed to
    the terminal.
    """

    def __init__(self, parent_app: REPLLike, script_name: str) -> None:
        """Initialize the logger for a given script.

        Args:
            parent_app (REPLLike): The parent REPL application whose console the script should log to.
            script_name (str): The name of the script, used as a prefix on logged messages.

        """
        self._parent_app = parent_app
        self._script_name = script_name
        self._prefix = f"[cyan]\\[{script_name}][/cyan]"

    def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message (str): The message to log.

        """
        self._parent_app.print_msg(f"{self._prefix} {message}")
        self._parent_app.logger.info("[%s] %s", self._script_name, message)

    def success(self, message: str) -> None:
        """Log a success message.

        Args:
            message (str): The message to log.

        """
        self._parent_app.print_success(message, prefix=self._prefix)
        self._parent_app.logger.info("[%s] %s", self._script_name, message)

    def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message (str): The message to log.

        """
        self._parent_app.print_warning(message, prefix=self._prefix)
        self._parent_app.logger.warning("[%s] %s", self._script_name, message)

    def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message (str): The message to log.

        """
        self._parent_app.print_error(message, prefix=self._prefix)
        self._parent_app.logger.error("[%s] %s", self._script_name, message)


_script_parser = cmd2.Cmd2ArgumentParser()
_script_parser.add_subparsers(title="subcommand", help="subcommand help")

_load_parser = cmd2.Cmd2ArgumentParser()
_load_parser.add_argument(
    "filepath",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help=(
        f"The path to a {SMALConstants.SMAL_SCRIPT_FILE_EXTENSION} script file, a Python script defining "
        "`smal_script(device, logger, ...)`, or a directory containing either."
    ),
)
_load_parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite the existing script if it already exists in persistence.")


class LoadArgs(BaseModel):
    """Model describing the arguments to the load command."""

    filepath: Path
    overwrite: bool = False


_delete_parser = cmd2.Cmd2ArgumentParser()
_delete_parser.add_argument("script_name", type=str, completer=script_completer, help="The name of the script to delete, or all if 'all' is given.")
_delete_parser.add_argument(
    "-y",
    "--yes",
    action="store_true",
    help="Automatically confirm deletion of all scripts without prompting for confirmation. Only relevant when deleting 'all'.",
)


class DeleteArgs(BaseModel):
    """Model describing the arguments to the delete command."""

    script_name: str
    yes: bool = False


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
_run_parser.add_argument(
    "-p",
    "--param",
    action="append",
    type=parse_key_value,
    help=(
        "Repeatable key=value pair (e.g., -p key1=value1 -p key2=value2) to pass as keyword arguments to a Python "
        "script's `smal_script` function. Ignored for SMAL (.smalscr) scripts."
    ),
)


class RunArgs(BaseModel):
    """Model describing the arguments to the run command."""

    script_name: str
    param: list[tuple[str, Any]] | None = None


_list_parser = cmd2.Cmd2ArgumentParser()

_view_parser = cmd2.Cmd2ArgumentParser()
_view_parser.add_argument("script_name", type=str, completer=script_completer, help="The name of the script to view.")


class ViewArgs(BaseModel):
    """Model describing the arguments to the view command."""

    script_name: str


class ScriptCmdSet(SMALCmdSet):
    """Command set for the `script` command."""

    @cmd2.with_argparser(_script_parser)
    def do_script(self, args: argparse.Namespace) -> None:
        """Manage SMAL scripts.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = getattr(args, "cmd2_subcommand_func", None)
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("script")

    @cmd2.as_subcommand_to("script", "load", _load_parser, help="Load a SMAL or Python script from a file.")
    def script_load(self, args: argparse.Namespace) -> None:
        """Load a SMAL (`.smalscr`) or Python script from a file, or a directory containing either.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = LoadArgs.model_validate(vars(args))
        parent_app = self.parent_app
        if not parsed_args.filepath.exists():
            parent_app.print_error(f"Script file '{parsed_args.filepath}' does not exist.")
            return
        persistence = get_persistence()
        if parsed_args.filepath.is_dir():
            with parent_app.console.status(f"[bold blue]Searching for SMAL and Python scripts under {parsed_args.filepath}...[/bold blue]"):
                script_extensions = (SMALConstants.SMAL_SCRIPT_FILE_EXTENSION, SMALConstants.PYTHON_SCRIPT_FILE_EXTENSION)
                script_files = sorted(p for ext in script_extensions for p in parsed_args.filepath.rglob(f"*{ext}") if p.is_file())
            if not script_files:
                parent_app.print_warning(
                    f"No scripts (`{SMALConstants.SMAL_SCRIPT_FILE_EXTENSION}` or `{SMALConstants.PYTHON_SCRIPT_FILE_EXTENSION}`) found under directory:"
                    f" {parsed_args.filepath}",
                )
                return
            for script_file in script_files:
                self._load_any_script_from_file(script_file, parsed_args.overwrite, persistence, parent_app)
        else:
            self._load_any_script_from_file(parsed_args.filepath, parsed_args.overwrite, persistence, parent_app)

    def _load_any_script_from_file(self, filepath: Path, overwrite: bool, persistence: SMALPersistence, parent_app: REPLLike) -> None:
        """Load either a SMAL or Python script from a file, dispatching on its extension.

        Args:
            filepath (Path): The path to the script file.
            overwrite (bool): Whether to overwrite an existing script of the same name in persistence.
            persistence (SMALPersistence): The persistence object to save the script (or its path) to.
            parent_app (REPLLike): The parent REPL application for printing messages.

        """
        if filepath.suffix == SMALConstants.SMAL_SCRIPT_FILE_EXTENSION:
            self._load_script_from_file(filepath, overwrite, persistence, parent_app)
        elif filepath.suffix == SMALConstants.PYTHON_SCRIPT_FILE_EXTENSION:
            self._load_python_script_from_file(filepath, overwrite, persistence, parent_app)
        else:
            parent_app.print_error(
                f"Unsupported script file type '{filepath.suffix}' for '{filepath}'."
                f" Expected '{SMALConstants.SMAL_SCRIPT_FILE_EXTENSION}' or '{SMALConstants.PYTHON_SCRIPT_FILE_EXTENSION}'.",
            )

    @cmd2.as_subcommand_to("script", "delete", _delete_parser, help="Delete a script from persistence by name, or all if 'all' is given.")
    def script_delete(self, args: argparse.Namespace) -> None:
        """Delete a script from persistence by name, or all if 'all' is given.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = DeleteArgs.model_validate(vars(args))
        parent_app = self.parent_app
        persistence = get_persistence()
        if parsed_args.script_name.lower() == "all":
            total = len(persistence.scripts) + len(persistence.python_scripts)
            if not total:
                parent_app.print_warning("No scripts found in persistence.")
                return
            if not parsed_args.yes:
                confirmation = self._cmd.read_input(
                    cmd2.stylize(f"Are you sure you want to delete all {total} script(s) from persistence? [y/N] ", "bold yellow"),
                )
                if confirmation.strip().lower() not in {"y", "yes"}:
                    parent_app.print_warning("Cancelled — no scripts were deleted.")
                    return
            persistence.scripts.clear()
            persistence.python_scripts.clear()
            persistence.save()
            parent_app.print_success("All scripts have been deleted from persistence.", omit_heading=True)
        elif parsed_args.script_name in persistence.scripts or parsed_args.script_name in persistence.python_scripts:
            if parsed_args.script_name in persistence.scripts:
                persistence.delete_script(parsed_args.script_name, save=True)
            if parsed_args.script_name in persistence.python_scripts:
                persistence.delete_python_script(parsed_args.script_name, save=True)
            parent_app.print_success(f"Script '{parsed_args.script_name}' has been deleted from persistence.", omit_heading=True)
        else:
            parent_app.print_error(f"No script found with the name '{parsed_args.script_name}'.")

    @cmd2.as_subcommand_to("script", "create", _create_parser, help="Create a new script dynamically from within the REPL.")
    def script_create(self, args: argparse.Namespace) -> None:
        """Create a new script dynamically from within the REPL.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = CreateArgs.model_validate(vars(args))
        parent_app = self.parent_app
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

    @cmd2.as_subcommand_to("script", "run", _run_parser, help="Run a SMAL or Python script by name.")
    def script_run(self, args: argparse.Namespace) -> None:
        """Run a SMAL (`.smalscr`) or Python script by name.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = RunArgs.model_validate(vars(args))
        parent_app = self.parent_app
        extra_kwargs = parse_params(parsed_args.param or [])
        persistence = get_persistence()
        script = persistence.scripts.get(parsed_args.script_name)
        if script is not None:
            if extra_kwargs:
                parent_app.print_warning("The `-p`/`--param` option is ignored for SMAL (.smalscr) scripts.")
            self._run_smal_script(script, parent_app)
            return
        python_script_path = persistence.python_scripts.get(parsed_args.script_name)
        if python_script_path is not None:
            self._run_python_script(parsed_args.script_name, python_script_path, parent_app, **extra_kwargs)
            return
        parent_app.print_error(f"No script found with the name '{parsed_args.script_name}'.")

    def _run_smal_script(self, script: SMALScript, parent_app: REPLLike) -> None:
        """Run a `.smalscr`-based script by sending each of its commands to the actively connected device.

        Args:
            script (SMALScript): The script to run.
            parent_app (REPLLike): The parent REPL application.

        """
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

    def _run_python_script(self, name: str, filepath: Path, parent_app: REPLLike, **extra_kwargs: Any) -> None:
        """Run a Python-based script by calling its `smal_script` entrypoint with the actively connected device.

        Args:
            name (str): The name the script is cached under, for messaging purposes.
            filepath (Path): The path to the Python script file defining `smal_script(device, logger, ...)`.
            parent_app (REPLLike): The parent REPL application.
            **extra_kwargs (Any): Additional keyword arguments to pass to the script's `smal_script` function.

        """
        if parent_app.active_connection is None or not parent_app.active_connection.is_connected:
            parent_app.print_error("No active connection found. Please connect to a device first using the `connect` command.")
            return
        try:
            script_fn: PythonScriptFn = import_external_fn_from_file(filepath, "smal_script_module", "smal_script")
        except Exception as e:  # noqa: BLE001 - Catching blind exceptions here to provide a user-friendly error message in the REPL.
            parent_app.print_error(f"Failed to load Python script '{name}' from '{filepath}': {e}")
            return
        parent_app.print_success(f"Running Python script '{name}' from '{filepath}'.", omit_heading=True)
        logger = SMALScriptLogger(parent_app, name)
        try:
            script_fn(parent_app.active_connection.device, logger, **extra_kwargs)
        except Exception as e:  # noqa: BLE001 - Catching blind exceptions here to provide a user-friendly error message in the REPL.
            parent_app.print_error(f"Error while running Python script '{name}': {e}")

    @cmd2.as_subcommand_to("script", "list", _list_parser, help="List all scripts currently stored in persistence.")
    def script_list(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused method argument
        """List all scripts currently stored in persistence.

        Args:
            args (argparse.Namespace): The parsed command-line arguments. Unused.

        """
        parent_app = self.parent_app
        persistence = get_persistence()
        if not persistence.scripts and not persistence.python_scripts:
            parent_app.print_warning("No scripts found in persistence.")
            return
        script_data = [[script.name, "SMAL"] for script in persistence.scripts.values()]
        script_data += [[name, "Python"] for name in persistence.python_scripts]
        echo_table(
            "Stored SMAL Scripts",
            ["Name", "Type"],
            sorted(script_data),
            col_metadata={
                "Name": {"style": "cyan"},
                "Type": {"style": "yellow"},
            },
        )

    @cmd2.as_subcommand_to("script", "view", _view_parser, help="View the details of a script by name.")
    def script_view(self, args: argparse.Namespace) -> None:
        """View the details of a script by name.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = ViewArgs.model_validate(vars(args))
        parent_app = self.parent_app
        persistence = get_persistence()
        script = persistence.scripts.get(parsed_args.script_name)
        if script is not None:
            self._view_smal_script(script, parent_app)
            return
        python_script_path = persistence.python_scripts.get(parsed_args.script_name)
        if python_script_path is not None:
            parent_app.print_msg(f"Script Name: {parsed_args.script_name}")
            parent_app.print_msg("Type: Python")
            parent_app.print_msg(f"Path: {python_script_path}")
            return
        parent_app.print_error(f"No script found with the name '{parsed_args.script_name}'.")

    def _view_smal_script(self, script: SMALScript, parent_app: REPLLike) -> None:
        """Print the details of a `.smalscr`-based script.

        Args:
            script (SMALScript): The script to display.
            parent_app (REPLLike): The parent REPL application.

        """
        parent_app.print_msg(f"Script Name: {script.name}")
        parent_app.print_msg("Type: SMAL")
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

    def _load_python_script_from_file(self, filepath: Path, overwrite: bool, persistence: SMALPersistence, parent_app: REPLLike) -> str | None:
        """Load a Python-based SMAL script from a file, caching its path in persistence under its filename stem.

        Args:
            filepath (Path): The path to the Python script file. Must define a `smal_script(device, logger, ...)` function.
            overwrite (bool): Whether to overwrite an existing cached Python script with the same name.
            persistence (SMALPersistence): The persistence object to save the script's path to.
            parent_app (REPLLike): The parent REPL application for printing messages.

        Returns:
            str | None: The name the script was cached under, or None if loading failed.

        """
        name = filepath.stem
        try:
            import_external_fn_from_file(filepath, "smal_script_module", "smal_script")
        except Exception as e:  # noqa: BLE001 - Catching blind exceptions here to provide a user-friendly error message in the REPL.
            parent_app.print_error(f"Failed to load Python script from file '{filepath}': {e}")
            return None
        try:
            persistence.add_python_script(name, filepath, overwrite=overwrite, save=True)
        except ValueError as e:
            parent_app.print_error(str(e))
            return None
        parent_app.print_success(f"Python script '{name}' loaded successfully from '{filepath}' and saved to persistence.", omit_heading=True)
        return name
