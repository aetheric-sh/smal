"""Module defining the protocol for the SMAL REPL.

This is for command sets beneath the REPL main entrypoint to interact with the REPL without causing a circular dependency.
"""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from rich.console import Console

    from smal.repl.connection import DeviceConnection
    from smal.repl.target_module import TargetModule
    from smal.schemas.state_machine import StateMachine


@runtime_checkable
class REPLLike(Protocol):
    """Protocol defining the interface for a REPL-like object."""

    def get_console(self) -> Console:
        """Get the console for the REPL."""
        ...

    def set_active_machine(self, machine: StateMachine) -> None:
        """Set the active machine for the REPL."""
        ...

    def get_machine_by_name(self, name: str) -> StateMachine | None:
        """Get the machine object for the given name."""
        ...

    def get_machine_by_path(self, path: Path) -> StateMachine | None:
        """Get the machine object for the given path."""
        ...

    def get_active_connection(self) -> DeviceConnection | None:
        """Get the active device connection for the REPL."""
        ...

    def get_active_machine(self) -> StateMachine | None:
        """Get the active machine for the REPL."""
        ...

    def print_msg(self, message: str) -> None:
        """Print a message to the console."""
        ...

    def print_success(self, message: str, prefix: str | None = None, omit_heading: bool = False) -> None:
        """Print a success message to the console."""
        ...

    def print_error(self, message: str, prefix: str | None = None, omit_heading: bool = False) -> None:
        """Print an error message to the console."""
        ...

    def print_warning(self, message: str, prefix: str | None = None, omit_heading: bool = False) -> None:
        """Print a warning message to the console."""
        ...

    def set_active_module(self, module_file: Path) -> None:
        """Set the active module for the REPL."""
        ...

    def get_active_module(self) -> TargetModule | None:
        """Get the currently active module for the REPL.

        Returns:
            TargetModule | None: The currently active module, or None if no module is active.

        """
        ...

    def execute_statement(self, command: str) -> None:
        """Execute a command statement in the REPL.

        Args:
            command (str): The command statement to execute.

        """
        ...
