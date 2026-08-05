"""Package defining command sets for the SMAL REPL."""

import cmd2

from .code import CodeCmdSet
from .corrections import CorrectionsCmdSet
from .debug import DebugCmdSet
from .diagram import DiagramCmdSet
from .machine import MachineCmdSet
from .rules import RulesCmdSet
from .validation import ValidationCmdSet


def all_cmd_sets() -> list[cmd2.CommandSet]:
    """Get a list of all command sets for the SMAL REPL.

    Returns:
        list[cmd2.CommandSet]: A list of all command sets.

    """
    return [CodeCmdSet(), CorrectionsCmdSet(), DebugCmdSet(), DiagramCmdSet(), MachineCmdSet(), RulesCmdSet(), ValidationCmdSet()]
