"""Module defining a dataclass describing a target module for the SMAL REPL.

This is the python file that contains target-specific implementations for data harvesting and device connection.
"""

from __future__ import annotations  # Until Python 3.14

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from smal.repl.target_api import ConnectFn, HarvestFn, RegisterCmdSetFn, SendMsgFn


@dataclass(frozen=True)
class TargetModule:
    """Dataclass describing a target module for the SMAL REPL."""

    filepath: Path
    connect_fn: ConnectFn
    harvest_fn: HarvestFn
    send_msg_fn: SendMsgFn | None = None
    register_cmdsets_fn: RegisterCmdSetFn | None = None
    utilities_state_machines: bool = True  # Derived from _SMAL_UTILIZES_STATE_MACHINES variable defined within module.

    @property
    def info(self) -> list[list[str]]:
        """Get all information about the target module.

        Returns:
            list[list[str]]: The information about the target module as a list of lists, where each inner list contains the hook name, signature, and address.

        """
        return [
            [fn.__name__, _format_signature_multiline(_get_callable_signature(fn)), str(fn)]
            for fn in [self.connect_fn, self.harvest_fn, self.send_msg_fn, self.register_cmdsets_fn]
            if fn is not None
        ]


def _get_callable_signature(fn: object) -> inspect.Signature | None:
    """Get a callable's runtime signature, if available."""
    try:
        # unwrap() follows decorators so we can inspect the original callable signature.
        return inspect.signature(inspect.unwrap(fn))
    except (TypeError, ValueError):
        return None


def _annotation_to_str(annotation: object) -> str:
    """Render an annotation in a readable form."""
    if annotation is inspect.Signature.empty:
        return ""
    if isinstance(annotation, str):
        return annotation
    return str(annotation)


def _format_signature_multiline(signature: inspect.Signature | None, max_single_line_len: int = 100) -> str:
    """Format signatures so long ones are easier to read in table output."""
    if signature is None:
        return "signature unavailable"

    raw = str(signature)
    if len(raw) <= max_single_line_len:
        return raw

    params = [str(param) for param in signature.parameters.values()]
    if params:
        args_block = "(\n  " + ",\n  ".join(params) + "\n)"
    else:
        args_block = "()"

    ret = _annotation_to_str(signature.return_annotation)
    if not ret:
        return args_block
    return f"{args_block}\n-> {ret}"
