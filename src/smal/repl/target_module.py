"""Module defining a dataclass describing a target module for the SMAL REPL.

This is the python file that contains target-specific implementations for data harvesting and device connection.
"""

from __future__ import annotations  # Until Python 3.14

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from smal.repl.cmd_sets.debug import HarvestFn
    from smal.repl.connection import ConnectedDevice, ConnectFn


class SendMsgFn(Protocol):
    """Protocol describing a function that sends a message to the actively connected SMAL device."""

    def __call__(self, device: ConnectedDevice, content: str, **kwargs: Any) -> Any:
        """Send a message to the actively connected SMAL device.

        Args:
            device (ConnectedDevice): The actively connected SMAL device.
            content (str): The content of the message to send.
            **kwargs: Additional keyword arguments to pass to the send function.

        Returns:
            Any: The response from the device after sending the message, if any.

        """
        ...


@dataclass(frozen=True)
class TargetModule:
    """Dataclass describing a target module for the SMAL REPL."""

    filepath: Path
    connect_fn: ConnectFn
    harvest_fn: HarvestFn
    send_msg_fn: SendMsgFn | None = None
