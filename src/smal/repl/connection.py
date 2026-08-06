"""Module defining the protocols for connecting/disconnecting from an arbitrary device using the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import cmd2

from smal.repl.helpers import import_external_fn_from_file

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class ConnectedDevice(Protocol):
    """Protocol defining an arbitrary connected device."""

    def get_name(self) -> str:
        """Get the name of the connected device."""
        ...

    def get_connection_details(self) -> dict[str, Any] | None:
        """Get the connection details of the connected device."""
        ...

    def disconnect(self, **kwargs: object) -> bool:
        """Disconnect from the device."""
        ...


class ConnectFn(Protocol):
    """Protocol for the connect function, which accepts arbitrary default params."""

    def __call__(self, **kwargs: object) -> ConnectedDevice | None:
        """Connect to an arbitrary device."""
        ...


@dataclass
class DeviceConnection:
    """Dataclass defining a connection (or lackthereof) to an arbitrary device."""

    _DEFAULT_NAME: str = "Unknown Device"

    name: str = _DEFAULT_NAME
    device: ConnectedDevice | None = None

    @classmethod
    def create(cls, fn_module_path: Path, **kwargs: Any) -> DeviceConnection | None:
        """Create a connection to an arbitrary device.

        Args:
            fn_module_path (Path): The path to the module containing the `connect` function.
            **kwargs (Any): Arbitrary keyword arguments to pass to the `connect` function.

        Raises:
            FileNotFoundError: If the module path does not exist or is not a file.
            ImportError: If the module cannot be imported or loaded.
            AttributeError: If the module does not have a 'connect' function.
            TypeError: If the 'connect' function is not callable or does not return a ConnectedDevice.
            RuntimeError: If the connection attempt fails.
            TypeError: If the returned object from the 'connect' function is not a ConnectedDevice.

        Returns:
            DeviceConnection | None: The established device connection if successful, otherwise None.

        """
        connect_fn: ConnectFn = import_external_fn_from_file(fn_module_path, "connect_module", "connect")
        try:
            connected_device = connect_fn(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to connect using {fn_module_path}: {e}") from e
        if connected_device is None:
            return None
        if not isinstance(connected_device, ConnectedDevice):
            raise TypeError(f"'connect' in module {fn_module_path} did not return a ConnectedDevice.")
        return cls(name=connected_device.get_name(), device=connected_device)

    def disconnect(self, **kwargs: Any) -> bool:
        """Disconnect from the active device connection.

        Args:
            **kwargs (Any): Arbitrary keyword arguments to pass to the device's `disconnect` method.

        Raises:
            RuntimeError: If the disconnection fails.

        Returns:
            bool: True if the disconnection was successful, False otherwise.

        """
        if self.device is None:
            # TODO: Log error
            return False
        try:
            result = self.device.disconnect(**kwargs)
            if result:
                # TODO: Log success
                self.device = None
                self.name = self._DEFAULT_NAME
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to disconnect from device {self.name}: {e}") from e

    @property
    def connection_info_str(self) -> str:
        """Get the string representing information about the active device connection, if any.

        Returns:
            str: The string representing information about the active device connection, if any.

        """
        if self.device is None:
            return cmd2.stylize("disconnected", "bold red")
        return cmd2.stylize(f"connected::{self.device.get_name()}", "bold green")

    @property
    def connection_details_str(self) -> str | None:
        """Get the string representing the connection details of the active device connection, if any.

        Returns:
            str | None: The string representing the connection details of the active device connection, if any.

        """
        if self.device is None:
            return None
        connection_details = self.device.get_connection_details()
        if connection_details is None:
            return cmd2.stylize("no details", "bold yellow")
        return ",\n".join(f"{k}:{v}" for k, v in connection_details.items())

    @property
    def is_connected(self) -> bool:
        """Check if there is an active device connection.

        Returns:
            bool: True if there is an active device connection, False otherwise.

        """
        return self.device is not None
