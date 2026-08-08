"""Module defining the protocols for connecting/disconnecting from an arbitrary device using the SMAL REPL."""

from __future__ import annotations  # Until Python 3.14

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import cmd2

from smal.repl.repl_like import REPLLike  # noqa: TC001 - Pydantic requires this at runtime for type checking
from smal.repl.target_module import TargetModule  # noqa: TC001 - Pydantic requires this at runtime for type checking

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
    def create(cls, parent_app: REPLLike, target_module: TargetModule | None, fn_module_path: Path | None, **kwargs: Any) -> DeviceConnection | None:
        """Create a connection to an arbitrary device.

        Args:
            parent_app (REPLLike): The parent REPL application.
            target_module (TargetModule | None): The target module containing the `connect` function.
            fn_module_path (Path | None): The path to the module containing the `connect`
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
        if target_module is not None:
            connect_fn = target_module.connect_fn
        elif fn_module_path is not None:
            parent_app.set_active_module(fn_module_path)
            if parent_app.active_module is None:
                raise RuntimeError(f"Failed to set active module to {fn_module_path}.")
            connect_fn = parent_app.active_module.connect_fn
        else:
            raise ValueError(
                "Cannot create device connection without target module. "
                "Either set one using `module load` or provide a path to a module containing the `connect` function using `connect -m <PATH>`.",
            )
        try:
            connected_device = connect_fn(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to connect: {e}") from e
        if connected_device is None:
            return None
        if not isinstance(connected_device, ConnectedDevice):
            raise TypeError(
                f"'connect' in module {parent_app.active_module.filepath if parent_app.active_module else fn_module_path} did not return a ConnectedDevice."
            )
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
            return False
        try:
            result = self.device.disconnect(**kwargs)
            if result:
                self.device = None
                self.name = self._DEFAULT_NAME
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to disconnect from device {self.name}: {e}") from e

    @property
    def connection_info_str(self) -> str:
        """Get the stylized name of the actively connected device, or a placeholder if there is none.

        Returns:
            str: The stylized device name, or a stylized "none" placeholder if there is no active connection.

        """
        if self.device is None:
            return cmd2.stylize("disconnected", "bold red")
        return cmd2.stylize(self.device.get_name(), "bold green")

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
        return ",\n".join(f"{k}: {v}" for k, v in connection_details.items())

    @property
    def is_connected(self) -> bool:
        """Check if there is an active device connection.

        Returns:
            bool: True if there is an active device connection, False otherwise.

        """
        return self.device is not None
