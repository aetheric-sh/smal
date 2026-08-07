"""Module defining completers to provide tab-completion for the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING, Any

from smal.repl.cmd_sets.code import TemplateRegistry
from smal.repl.helpers import get_persistence

if TYPE_CHECKING:
    import cmd2


def module_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    """Get the list of module names that start with the given text for tab-completion of the SMAL REPL.

    Args:
        cmd (cmd2.Cmd): The command instance that is invoking the completer.
        text (str): The text that the user has typed so far for which tab-completion is being requested.
        line (str): The entire line of input that the user has typed so far.
        begidx (int): The beginning index of the text being completed in the line.
        endidx (int): The ending index of the text being completed in the line.
        *args: Additional positional arguments passed to the completer.
        **kwargs: Additional keyword arguments passed to the completer.

    Returns:
        list[str]: A list of module names that start with the given text.

    """
    persistence = get_persistence()
    return [module_name for module_name in persistence.modules if module_name.startswith(text)]


def machine_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    """Get the list of machine names that start with the given text for tab-completion of the SMAL REPL.

    Args:
        cmd (cmd2.Cmd): The command instance that is invoking the completer.
        text (str): The text that the user has typed so far for which tab-completion is being requested.
        line (str): The entire line of input that the user has typed so far.
        begidx (int): The beginning index of the text being completed in the line.
        endidx (int): The ending index of the text being completed in the line.
        *args: Additional positional arguments passed to the completer.
        **kwargs: Additional keyword arguments passed to the completer.

    Returns:
        list[str]: A list of machine names that start with the given text.

    """
    persistence = get_persistence()
    return [machine_name for machine_name in persistence.machines if machine_name.startswith(text)]


def template_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    """Get the list of template names that start with the given text for tab-completion of the SMAL REPL.

    Args:
        cmd (cmd2.Cmd): The command instance that is invoking the completer.
        text (str): The text that the user has typed so far for which tab-completion is being requested.
        line (str): The entire line of input that the user has typed so far.
        begidx (int): The beginning index of the text being completed in the line.
        endidx (int): The ending index of the text being completed in the line.
        *args: Additional positional arguments passed to the completer.
        **kwargs: Additional keyword arguments passed to the completer.

    Returns:
        list[str]: A list of template names that start with the given text.

    """
    return [tmpl.name for tmpl in TemplateRegistry.list_templates() if tmpl.name.startswith(text)]


def correction_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    """Get the list of correction names that start with the given text for tab-completion of the SMAL REPL.

    Args:
        cmd (cmd2.Cmd): The command instance that is invoking the completer.
        text (str): The text that the user has typed so far for which tab-completion is being requested.
        line (str): The entire line of input that the user has typed so far.
        begidx (int): The beginning index of the text being completed in the line.
        endidx (int): The ending index of the text being completed in the line.
        *args: Additional positional arguments passed to the completer.
        **kwargs: Additional keyword arguments passed to the completer.

    Returns:
        list[str]: A list of correction names that start with the given text.

    """
    persistence = get_persistence()
    return [correction_name for correction_name in persistence.corrections if correction_name.startswith(text)]


def rule_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    """Get the list of rule names that start with the given text for tab-completion of the SMAL REPL.

    Args:
        cmd (cmd2.Cmd): The command instance that is invoking the completer.
        text (str): The text that the user has typed so far for which tab-completion is being requested.
        line (str): The entire line of input that the user has typed so far.
        begidx (int): The beginning index of the text being completed in the line.
        endidx (int): The ending index of the text being completed in the line.
        *args: Additional positional arguments passed to the completer.
        **kwargs: Additional keyword arguments passed to the completer.

    Returns:
        list[str]: A list of rule names that start with the given text.

    """
    persistence = get_persistence()
    return [rule_name for rule_name in persistence.rules if rule_name.startswith(text)]


def script_completer(cmd: cmd2.Cmd, text: str, line: str, begidx: int, endidx: int, *args: Any, **kwargs: Any) -> list[str]:  # noqa: ARG001 - Unused arguments
    """Get the list of script names that start with the given text for tab-completion of the SMAL REPL.

    Args:
        cmd (cmd2.Cmd): The command instance that is invoking the completer.
        text (str): The text that the user has typed so far for which tab-completion is being requested.
        line (str): The entire line of input that the user has typed so far.
        begidx (int): The beginning index of the text being completed in the line.
        endidx (int): The ending index of the text being completed in the line.
        *args: Additional positional arguments passed to the completer.
        **kwargs: Additional keyword arguments passed to the completer.

    Returns:
        list[str]: A list of script names that start with the given text.

    """
    persistence = get_persistence()
    all_names = set(persistence.scripts) | set(persistence.python_scripts)
    return [script_name for script_name in all_names if script_name.startswith(text)]
