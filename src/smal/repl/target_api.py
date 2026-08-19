"""Module defining the APIs that can be implemented by target modules to interact with the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from smal.repl.cmd_sets.smal_cmd_set import SMALCmdSet
    from smal.repl.connection import ConnectedDevice
    from smal.repl.repl_logger import SMALLogger


@runtime_checkable
class SendMsgFn(Protocol):
    """Protocol describing a function that sends a message to the actively connected SMAL device."""

    def __call__(self, device: ConnectedDevice, content: str | dict | bytes, **kwargs: Any) -> Any:
        """Send a message to the actively connected SMAL device.

        Args:
            device (ConnectedDevice): The actively connected SMAL device.
            content (str | dict | bytes): The content of the message to send.
            **kwargs: Additional keyword arguments to pass to the send function.

        Returns:
            Any: The response from the device after sending the message, if any.

        """
        ...


@runtime_checkable
class ConnectFn(Protocol):
    """Protocol for the connect function, which accepts arbitrary default params."""

    def __call__(self, **kwargs: object) -> ConnectedDevice | None:
        """Connect to an arbitrary device."""
        ...


@runtime_checkable
class HarvestFn(Protocol):
    """Protocol for the harvest function, which accepts a machine name and arbitrary default params."""

    def __call__(self, name: str, connected_device: ConnectedDevice, **kwargs: Any) -> bytearray:
        """Harvest debug data for the given machine name."""
        ...


@runtime_checkable
class PythonScriptFn(Protocol):
    """Protocol for a Python-based SMAL script's entrypoint function."""

    def __call__(self, device: ConnectedDevice, logger: SMALLogger, *args: Any, **kwargs: Any) -> None:
        """Execute this script against the actively connected SMAL device."""
        ...


@runtime_checkable
class RegisterCmdSetFn(Protocol):
    """Protocol for a function that registers command sets with the actively connected SMAL device."""

    def __call__(self, **kwargs: Any) -> list[SMALCmdSet]:
        """Get a list of externally-provided command sets to register with SMAL.

        Returns:
            list[SMALCmdSet]: The list of externally-provided command sets to register with SMAL.

        """
        ...
