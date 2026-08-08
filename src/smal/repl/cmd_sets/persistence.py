"""Module defining the `persistence` command set for the SMAL REPL, for backing up and restoring SMAL's application data."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import cmd2
from pydantic import BaseModel

from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
from smal.repl.helpers import get_persistence, reset_persistence_cache
from smal.utilities.persistence import SMALPersistence

if TYPE_CHECKING:
    import argparse

_persistence_parser = cmd2.Cmd2ArgumentParser()
_persistence_parser.add_subparsers(title="subcommand", help="subcommand help")

_export_parser = cmd2.Cmd2ArgumentParser()
_export_parser.add_argument(
    "filepath",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help="The file to export SMAL's application data (machines, modules, scripts, rules, corrections, aliases) to.",
)
_export_parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite the destination file if it already exists.")


class ExportArgs(BaseModel):
    """Model describing the arguments to the export command."""

    filepath: Path
    overwrite: bool = False


_import_parser = cmd2.Cmd2ArgumentParser()
_import_parser.add_argument(
    "filepath",
    type=Path,
    completer=cmd2.Cmd.path_complete,
    help="The file to import SMAL's application data from. Replaces the current application data entirely.",
)
_import_parser.add_argument("-y", "--yes", action="store_true", help="Automatically confirm replacing the current application data without prompting.")


class ImportArgs(BaseModel):
    """Model describing the arguments to the import command."""

    filepath: Path
    yes: bool = False


_open_parser = cmd2.Cmd2ArgumentParser()


class PersistenceCmdSet(SMALCmdSet):
    """Command set for backing up and restoring SMAL's application data (machines, modules, scripts, rules, corrections, and aliases)."""

    @cmd2.with_argparser(_persistence_parser)
    def do_persistence(self, args: argparse.Namespace) -> None:
        """Manage backups of SMAL's application data.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        handler = args.cmd2_handler.get()
        if handler is not None:
            handler(args)
        else:
            self._cmd.poutput("No subcommand given.")
            self._cmd.do_help("persistence")

    @cmd2.as_subcommand_to("persistence", "export", _export_parser, help="Export SMAL's application data to a file.")
    def persistence_export(self, args: argparse.Namespace) -> None:
        """Export SMAL's application data (machines, modules, scripts, rules, corrections, aliases) to a file.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = ExportArgs.model_validate(vars(args))
        parent_app = self.parent_app
        if parsed_args.filepath.exists() and not parsed_args.overwrite:
            parent_app.print_error(f"File '{parsed_args.filepath}' already exists. Use `-o`/`--overwrite` to replace it.")
            return
        get_persistence().save(parsed_args.filepath)
        parent_app.print_success(f"Exported application data to '{parsed_args.filepath}'.", omit_heading=True)

    @cmd2.as_subcommand_to("persistence", "import", _import_parser, help="Import SMAL's application data from a file, replacing the current data.")
    def persistence_import(self, args: argparse.Namespace) -> None:
        """Import SMAL's application data from a file, replacing the current in-memory and on-disk data entirely.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parsed_args = ImportArgs.model_validate(vars(args))
        parent_app = self.parent_app
        if not parsed_args.filepath.is_file():
            parent_app.print_error(f"File '{parsed_args.filepath}' does not exist.")
            return
        try:
            imported = SMALPersistence.load(parsed_args.filepath)
        except Exception as e:  # noqa: BLE001 - Broad exception caught for user-facing error handling
            parent_app.print_error(f"Failed to import application data from '{parsed_args.filepath}': {e}")
            return
        if not parsed_args.yes:
            confirmation = self._cmd.read_input(
                cmd2.stylize(
                    f"This will replace all of SMAL's current application data (machines, modules, scripts, rules, corrections, aliases) with "
                    f"the contents of '{parsed_args.filepath}'. Continue? [y/N] ",
                    "bold yellow",
                ),
            )
            if confirmation.strip().lower() not in {"y", "yes"}:
                parent_app.print_warning("Cancelled — application data was not imported.")
                return
        imported.save()
        reset_persistence_cache()
        # Aliases are loaded into `self._cmd.aliases` once at REPL startup (see SMALREPL.__init__), so they need to
        # be refreshed here too, or the import would silently appear to do nothing for aliases until next restart.
        self._cmd.aliases.clear()
        for name, tokens in imported.aliases.items():
            self._cmd.aliases[name] = " ".join(tokens)
        parent_app.print_success(f"Imported application data from '{parsed_args.filepath}'.", omit_heading=True)

    @cmd2.as_subcommand_to("persistence", "open", _open_parser, help="Open SMAL's application data directory in the OS file explorer.")
    def persistence_open(self, args: argparse.Namespace) -> None:  # noqa: ARG002 - Unused argument
        """Open SMAL's application data directory in the OS's native file explorer.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.

        """
        parent_app = self.parent_app
        app_dir = SMALPersistence.DEFAULT_PATH.parent
        app_dir.mkdir(parents=True, exist_ok=True)
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(app_dir)  # noqa: S606 - Fixed, non-user-controlled application data path.
            elif system == "Darwin":
                subprocess.run(["open", str(app_dir)], check=True)
            else:
                subprocess.run(["xdg-open", str(app_dir)], check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            parent_app.print_error(f"Failed to open a file explorer at {app_dir}: {e}")
            return
        parent_app.print_success(f"Opened application data directory: {app_dir}", omit_heading=True)
