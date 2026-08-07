"""Module defining the SMALCmdSet, a base class for command sets in the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING

import cmd2

from smal.repl.helpers import get_parent_app

if TYPE_CHECKING:
    from smal.repl.repl_like import REPLLike


class SMALCmdSet(cmd2.CommandSet):
    """Base class for command sets in the SMAL REPL.

    Provides a `parent_app` property so subcommand handlers don't each need to repeat the
    boilerplate of fetching and validating the parent REPL application via `get_parent_app`.
    """

    @property
    def parent_app(self) -> REPLLike:
        """Get the parent REPL application that this command set is registered to.

        Raises:
            RuntimeError: If the parent REPL application cannot be accessed, e.g. because this
                command set is not registered to a parent application, or its parent is not a
                REPLLike application.

        Returns:
            REPLLike: The parent REPL application.

        """
        try:
            return get_parent_app(self)
        except Exception as e:
            raise RuntimeError("Failed to get parent REPL application.") from e
