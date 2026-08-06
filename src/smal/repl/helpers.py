"""Module defining helper functions for CLI commands to use."""

from __future__ import annotations  # Until Python 3.14

import argparse
import importlib
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

import cmd2
from rich.console import Console
from rich.table import Table

from smal.repl.repl_like import REPLLike
from smal.utilities.persistence import SMALPersistence

if TYPE_CHECKING:
    from pathlib import Path

console = Console()

_active_statuses: ContextVar[tuple[Any, ...]] = ContextVar("_active_statuses", default=())


@contextmanager
def prefer_inner_rich_statuses() -> Any:
    """Temporarily patch Rich so nested statuses pause their parents.

    This lets an inner ``Console.status(...)`` own the live area while it is active,
    which prevents flicker when imported code opens its own status spinner.

    Yields:
        Iterator[None]: A context in which nested status calls prefer the innermost status.

    """
    original_console_status = Console.status

    @contextmanager
    def prioritized_status(self: Console, *args: Any, **kwargs: Any) -> Any:
        active_statuses = _active_statuses.get()
        parent_status = active_statuses[-1] if active_statuses else None
        status = original_console_status(self, *args, **kwargs)
        token = _active_statuses.set((*active_statuses, status))

        if parent_status is not None:
            parent_status.stop()

        try:
            with status as current_status:
                yield current_status
        finally:
            _active_statuses.reset(token)
            if parent_status is not None:
                parent_status.start()

    Console.status = prioritized_status
    try:
        yield
    finally:
        Console.status = original_console_status


def echo_list(header: str, items: list[str], tab_size: int = 2, bold_header: bool = True) -> None:
    """Echo a rich list of items with pretty formatting.

    Args:
        header (str): The header to print above the list of items.
        items (list[str]): The list of items to print under the header.
        tab_size (int, optional): The number of spaces to use for indentation. Defaults to 2.
        bold_header (bool, optional): Whether to print the header in bold. Defaults to True.

    """
    if bold_header:
        console.print(f"[bold]{header.rstrip(': ')}:[/bold]")
    else:
        console.print(f"{header.rstrip(': ')}:")
    original_tab_size = console.tab_size
    console.tab_size = tab_size
    for item in items:
        console.print(f"\t• {item}")
    console.tab_size = original_tab_size


def echo_table(title: str, columns: list[str], rows: list[list[str]], col_metadata: dict[str, dict[str, Any]] | None = None) -> None:
    """Echo a rich table to stdout with the given title, columns and rows.

    Args:
        title (str): The title of the table.
        columns (list[str]): The column headers of the table.
        rows (list[list[str]]): The rows of the table, where each row is a list of cell values.
        col_metadata (dict[str, dict[str, Any]], optional): Optional metadata for columns, \
            where keys are column names and values are dictionaries of keyword arguments to pass to Table.add_column(). Defaults to None.

    """
    table = Table(title=title)
    for col in columns:
        col_md = col_metadata.get(col, {}) if col_metadata else {}
        table.add_column(col, **col_md)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def get_persistence() -> SMALPersistence:
    """Get the SMAL persistence file, which contains the enabled status of corrections.

    Returns:
        SMALPersistence: The SMAL persistence object.

    """
    try:
        return SMALPersistence.load()
    except FileNotFoundError:
        console.print("[yellow]No existing persistence data found. Creating new persistence with default settings.[/yellow]")
        persistence = SMALPersistence()
        persistence.save()
        return persistence


def get_parent_app(cmd_set: cmd2.CommandSet) -> REPLLike:
    """Get the parent application of a command set.

    Args:
        cmd_set (cmd2.CommandSet): The command set for which to retrieve the parent application.

    Raises:
        AttributeError: If the command set does not have a '_cmd' attribute, indicating it is not registered to a parent application.
        RuntimeError: If the command set is not attached to a parent application.
        TypeError: If the parent application is not of type REPLLike.

    Returns:
        REPLLike: The parent application of the command set.

    """
    if not hasattr(cmd_set, "_cmd"):
        raise AttributeError("Unable to access parent application; '_cmd' attribute is missing.")
    try:
        parent_app = cmd_set._cmd  # noqa: SLF001 - Accessing protected member _cmd is necessary to get the parent application of a cmd2.CommandSet.
    except cmd2.exceptions.CommandSetRegistrationError as e:
        raise RuntimeError("CommandSet is not attached to a parent application.") from e
    if not isinstance(parent_app, REPLLike):
        raise TypeError(f"Expected parent application to be of type REPLLike, but got {type(parent_app).__name__}.")
    return parent_app


def import_external_fn_from_file(module_path: Path, module_name: str, fn_name: str) -> object:
    """Import an external function from a given file path.

    Args:
        module_path (Path): The file path to the module containing the function.
        module_name (str): The name to assign to the imported module.
        fn_name (str): The name of the function to import.

    Raises:
        FileNotFoundError: If the module path does not exist or is not a file.
        ImportError: If the module cannot be imported or loaded.
        AttributeError: If the module does not have the specified function.
        TypeError: If the specified function is not callable.

    Returns:
        object: The imported function.

    """
    if not module_path.is_file():
        raise FileNotFoundError(f"Module path {module_path} does not exist or is not a file.")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}.")
    fn_module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = fn_module
    try:
        spec.loader.exec_module(fn_module)
    except ModuleNotFoundError as e:
        raise ImportError(f"Could not load module from {module_path}: {e}") from e
    except ImportError as e:
        raise ImportError(f"Could not load module from {module_path}: {e}") from e
    if not hasattr(fn_module, fn_name):
        raise AttributeError(f"Module {module_path} does not have a '{fn_name}' function.")
    extern_fn = getattr(fn_module, fn_name)
    if not callable(extern_fn):
        raise TypeError(f"'{fn_name}' in module {module_path} is not callable.")
    # TODO: Validate the signature of the function
    return extern_fn


def parse_params(params: list[tuple[str, Any]]) -> dict[str, Any]:
    """Parse arbitrary keyword argument params from a command line command.

    Args:
        params (list[tuple[str, Any]]): The list of keyword argument params in the format (key, value).

    Returns:
        dict[str, Any]: The parsed keyword arguments as a dictionary.

    """
    return {param[0]: param[1] for param in params}


def parse_key_value(item: str) -> tuple[str, Any]:
    """Parse a key-value pair from a string in the format key=value.

    Args:
        item (str): The input string to parse.

    Returns:
        tuple[str, Any]: A tuple containing the key and the parsed value.

    """
    if "=" not in item:
        raise argparse.ArgumentTypeError(f"Invalid argument format: {item}. Expected format is key=value.")
    k, v = item.split("=", 1)
    k = k.strip().lstrip("-")  # Remove leading dashes if present
    if not k:
        raise argparse.ArgumentTypeError(f"Invalid argument key in: {item}. Key cannot be empty.")
    v = v.strip()
    if v.lower() in {"true", "false"}:
        v = v.lower() == "true"
    elif v.isdigit():
        v = int(v)
    return k, v
