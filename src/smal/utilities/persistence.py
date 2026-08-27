"""Module defining utilities for persistence of data."""

from __future__ import annotations  # Until Python 3.14

import json
import logging
import shutil
from contextvars import ContextVar
from pathlib import Path
from typing import ClassVar, TypeVar

from platformdirs import user_data_dir
from pydantic import BaseModel, Field, JsonValue

from smal.schemas.smal_script import SMALScript  # noqa: TC001 - Pydantic requires this at runtime for type validation
from smal.schemas.state_machine import StateMachine  # noqa: TC001 - Pydantic requires this at runtime for type validation
from smal.utilities.corrections import ALL_CORRECTIONS, Correction
from smal.utilities.rules import ALL_RULES, Rule

# Holds the rules/corrections settings while a persistence file is being deserialized, so that StateMachine
# objects cached under `SMALPersistence.machines` don't have to call `SMALPersistence.load()` (which would try to
# deserialize those same machines again) from their own `model_post_init`, causing infinite recursion.
_loading_settings: ContextVar[tuple[dict[str, bool], dict[str, bool]] | None] = ContextVar("_loading_settings", default=None)


T = TypeVar("T")


def get_loading_settings() -> tuple[dict[str, bool], dict[str, bool]] | None:
    """Get the rules/corrections settings of the persistence file currently being deserialized, if any.

    Returns:
        tuple[dict[str, bool], dict[str, bool]] | None: A tuple of (rules, corrections) settings if a persistence \
            file is currently being loaded, or None otherwise.

    """
    return _loading_settings.get()


class SMALPersistence(BaseModel):
    """Model representing the persistence of SMAL data, including rules and corrections."""

    DEFAULT_PATH: ClassVar[Path] = Path(user_data_dir(appname="smal", appauthor=False)) / "persistence.json"

    aliases: dict[str, list[str]] = Field(
        default_factory=dict,
        description="A dictionary mapping command alias names to their corresponding values.",
    )
    rules: dict[str, bool] = Field(
        default_factory=lambda: dict.fromkeys([r.name for r in ALL_RULES], True),
        description="A dictionary mapping rule names to their enabled/disabled status.",
    )
    corrections: dict[str, bool] = Field(
        default_factory=lambda: dict.fromkeys([c.name for c in ALL_CORRECTIONS], False),
        description="A dictionary mapping correction names to their enabled/disabled status.",
    )
    scripts: dict[str, SMALScript] = Field(
        default_factory=dict,
        description="A dictionary mapping script names to their corresponding SMALScript objects.",
    )
    modules: dict[str, Path] = Field(
        default_factory=dict,
        description="A dictionary mapping module names to their corresponding file paths.",
    )
    python_scripts: dict[str, Path] = Field(
        default_factory=dict,
        description="A dictionary mapping Python script names to their corresponding file paths.",
    )
    machines: dict[str, StateMachine] = Field(
        default_factory=dict,
        description="A dictionary mapping machine names to their corresponding StateMachine objects.",
    )
    machine_paths: dict[str, Path] = Field(
        default_factory=dict,
        description="A dictionary mapping machine names to their corresponding file paths.",
    )
    user_persistence: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="A dictionary for storing user-specific persistence data.",
    )

    @staticmethod
    def clean(del_dir: bool = False, exclude: set[str] | None = None) -> None:
        """Clean the persistence data by deleting all files in the application directory, and optionally the directory itself.

        Args:
            del_dir (bool): Whether to also remove the application directory itself after clearing its contents. Defaults to False.
            exclude (set[str] | None): Names of entries directly within the application directory to leave untouched (e.g. an
                actively open log file the caller wants to preserve). Ignored when del_dir is True, since the directory itself
                is removed regardless. Defaults to None.

        """
        app_dir = SMALPersistence.DEFAULT_PATH.parent
        exclude = exclude if exclude and not del_dir else set()
        if app_dir.exists():
            for item in app_dir.iterdir():
                if item.name in exclude:
                    continue
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logging.debug("Persistence data cleaned by removing files in directory %s", app_dir)
            if del_dir:
                app_dir.rmdir()
                logging.debug("Persistence data cleaned by removing directory %s", app_dir)

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> SMALPersistence:
        """Load the persistence data from a JSON file.

        Args:
            path (Path | str): The path to the JSON file from which to load the data. Defaults to DEFAULT_PATH.

        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Persistence file not found at {path}. Please save the persistence data first.")
        with path.open("r", encoding="utf-8") as f:
            raw = f.read()
        raw_data = json.loads(raw)
        token = _loading_settings.set((raw_data.get("rules", {}), raw_data.get("corrections", {})))
        try:
            return cls.model_validate_json(raw)
        finally:
            _loading_settings.reset(token)

    def enable_correction(self, correction: str | Correction, enabled: bool, write_to_file: bool = True) -> None:
        """Enable or disable a specific correction.

        Args:
            correction (str | Correction): The name of the correction to enable or disable, or a Correction object.
            enabled (bool): Whether to enable (True) or disable (False) the correction.
            write_to_file (bool): Whether to save the updated persistence data to file after changing the correction status. Defaults to True.

        """
        correction_name = correction if isinstance(correction, str) else correction.name
        if correction_name not in self.corrections:
            raise ValueError(f"Correction '{correction_name}' is not recognized.")
        self.corrections[correction_name] = enabled
        logging.debug("Correction '%s' set to %s.", correction_name, enabled)
        if write_to_file:
            self.save()

    def enable_rule(self, rule: str | Rule, enabled: bool, write_to_file: bool = True) -> None:
        """Enable or disable a specific rule.

        Args:
            rule (str | Rule): The name of the rule to enable or disable, or a Rule object.
            enabled (bool): Whether to enable (True) or disable (False) the rule.
            write_to_file (bool): Whether to save the updated persistence data to file after changing the rule status. Defaults to True.

        """
        rule_name = rule if isinstance(rule, str) else rule.name
        if rule_name not in self.rules:
            raise ValueError(f"Rule '{rule_name}' is not recognized.")
        self.rules[rule_name] = enabled
        logging.debug("Rule '%s' set to %s.", rule_name, enabled)
        if write_to_file:
            self.save()

    def add_script(self, script: SMALScript, overwrite: bool = False, save: bool = False) -> None:
        """Add a script to the persistence data.

        Args:
            script (SMALScript): The SMALScript object to add.
            overwrite (bool): Whether to overwrite an existing script with the same name. Defaults to False.
            save (bool): Whether to save the updated persistence data to file after adding the script. Defaults to False.

        Raises:
            ValueError: If a script with the same name already exists and overwrite is False.

        """
        if script.name in self.scripts and not overwrite:
            raise ValueError(f"A script with the name '{script.name}' already exists. Use overwrite=True to replace it.")
        self.scripts[script.name] = script
        logging.debug("Script '%s' added to persistence.", script.name)
        if save:
            self.save()

    def delete_script(self, script_name: str, save: bool = False) -> None:
        """Delete a script from the persistence data.

        Args:
            script_name (str): The name of the script to delete.
            save (bool): Whether to save the updated persistence data to file after deleting the script. Defaults to False.

        """
        if script_name in self.scripts:
            del self.scripts[script_name]
            logging.debug("Script '%s' deleted from persistence.", script_name)
            if save:
                self.save()
        else:
            logging.warning("Attempted to delete non-existent script '%s'.", script_name)

    def add_module(self, module_name: str, module_path: Path, overwrite: bool = False, save: bool = False) -> None:
        """Add a module to the persistence data.

        Args:
            module_name (str): The name of the module to add.
            module_path (Path): The file path of the module to add.
            overwrite (bool): Whether to overwrite an existing module with the same name. Defaults to False.
            save (bool): Whether to save the updated persistence data to file after adding the module. Defaults to False.

        Raises:
            ValueError: If a module with the same name already exists and overwrite is False.

        """
        if module_name in self.modules and not overwrite:
            raise ValueError(f"A module with the name '{module_name}' already exists. Use overwrite=True to replace it.")
        self.modules[module_name] = module_path
        logging.debug("Module '%s' added to persistence at path '%s'.", module_name, module_path)
        if save:
            self.save()

    def delete_module(self, module_name: str, save: bool = False) -> None:
        """Delete a module from the persistence data.

        Args:
            module_name (str): The name of the module to delete.
            save (bool): Whether to save the updated persistence data to file after deleting the module. Defaults to False.

        """
        if module_name in self.modules:
            del self.modules[module_name]
            logging.debug("Module '%s' deleted from persistence.", module_name)
            if save:
                self.save()
        else:
            logging.warning("Attempted to delete non-existent module '%s'.", module_name)

    def add_python_script(self, script_name: str, script_path: Path, overwrite: bool = False, save: bool = False) -> None:
        """Add a Python script to the persistence data.

        Args:
            script_name (str): The name of the Python script to add.
            script_path (Path): The file path of the Python script to add.
            overwrite (bool): Whether to overwrite an existing Python script with the same name. Defaults to False.
            save (bool): Whether to save the updated persistence data to file after adding the Python script. Defaults to False.

        Raises:
            ValueError: If a Python script with the same name already exists and overwrite is False.

        """
        if script_name in self.python_scripts and not overwrite:
            raise ValueError(f"A Python script with the name '{script_name}' already exists. Use overwrite=True to replace it.")
        self.python_scripts[script_name] = script_path
        logging.debug("Python script '%s' added to persistence at path '%s'.", script_name, script_path)
        if save:
            self.save()

    def delete_python_script(self, script_name: str, save: bool = False) -> None:
        """Delete a Python script from the persistence data.

        Args:
            script_name (str): The name of the Python script to delete.
            save (bool): Whether to save the updated persistence data to file after deleting the Python script. Defaults to False.

        """
        if script_name in self.python_scripts:
            del self.python_scripts[script_name]
            logging.debug("Python script '%s' deleted from persistence.", script_name)
            if save:
                self.save()
        else:
            logging.warning("Attempted to delete non-existent Python script '%s'.", script_name)

    def add_machine(self, machine: StateMachine, overwrite: bool = False, save: bool = False) -> None:
        """Add a machine to the persistence data.

        Args:
            machine (StateMachine): The StateMachine object to add.
            overwrite (bool): Whether to overwrite an existing machine with the same name. Defaults to False.
            save (bool): Whether to save the updated persistence data to file after adding the machine. Defaults to False.

        Raises:
            ValueError: If a machine with the same name already exists and overwrite is False.

        """
        if machine.name in self.machines and not overwrite:
            raise ValueError(f"A machine with the name '{machine.name}' already exists. Use overwrite=True to replace it.")
        self.machines[machine.name] = machine
        logging.debug("Machine '%s' added to persistence.", machine.name)
        if save:
            self.save()

    def delete_machine(self, machine_name: str, save: bool = False) -> None:
        """Delete a machine from the persistence data.

        Args:
            machine_name (str): The name of the machine to delete.
            save (bool): Whether to save the updated persistence data to file after deleting the machine. Defaults to False.

        """
        if machine_name in self.machines:
            del self.machines[machine_name]
            logging.debug("Machine '%s' deleted from persistence.", machine_name)
            if save:
                self.save()
        else:
            logging.warning("Attempted to delete non-existent machine '%s'.", machine_name)

    def add_machine_path(self, machine_name: str, machine_path: Path, overwrite: bool = False, save: bool = False) -> None:
        """Add a machine path to the persistence data.

        Args:
            machine_name (str): The name of the machine.
            machine_path (Path): The file path of the machine.
            overwrite (bool): Whether to overwrite an existing machine path with the same name. Defaults to False.
            save (bool): Whether to save the updated persistence data to file after adding the machine path. Defaults to False.

        Raises:
            ValueError: If a machine path with the same name already exists and overwrite is False.

        """
        if machine_name in self.machine_paths and not overwrite:
            raise ValueError(f"A machine path with the name '{machine_name}' already exists. Use overwrite=True to replace it.")
        self.machine_paths[machine_name] = machine_path
        logging.debug("Machine path for '%s' added to persistence at path '%s'.", machine_name, machine_path)
        if save:
            self.save()

    def delete_machine_path(self, machine_name: str, save: bool = False) -> None:
        """Delete a machine path from the persistence data.

        Args:
            machine_name (str): The name of the machine whose path to delete.
            save (bool): Whether to save the updated persistence data to file after deleting the machine path. Defaults to False.

        """
        if machine_name in self.machine_paths:
            del self.machine_paths[machine_name]
            logging.debug("Machine path for '%s' deleted from persistence.", machine_name)
            if save:
                self.save()
        else:
            logging.warning("Attempted to delete non-existent machine path for '%s'.", machine_name)

    def is_correction_enabled(self, correction: str | Correction) -> bool:
        """Check if a specific correction is enabled.

        Args:
            correction (str | Correction): The name of the correction to check, or a Correction object.

        Returns:
            bool: True if the correction is enabled, False otherwise.

        """
        correction_name = correction if isinstance(correction, str) else correction.name
        if correction_name not in self.corrections:
            raise ValueError(f"Correction '{correction_name}' is not recognized.")
        return self.corrections[correction_name]

    def is_rule_enabled(self, rule: str | Rule) -> bool:
        """Check if a specific rule is enabled.

        Args:
            rule (str | Rule): The name of the rule to check, or a Rule object.

        Returns:
            bool: True if the rule is enabled, False otherwise.

        """
        rule_name = rule if isinstance(rule, str) else rule.name
        if rule_name not in self.rules:
            raise ValueError(f"Rule '{rule_name}' is not recognized.")
        return self.rules[rule_name]

    def save(self, path: Path | str = DEFAULT_PATH) -> None:
        """Save the persistence data to a JSON file.

        Args:
            path (Path | str): The path to the JSON file where the data will be saved. Defaults to DEFAULT_PATH.

        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=4))
        logging.debug("Persistence data saved to %s", path)

    def set_user_data(self, key: str, user_data: JsonValue | BaseModel, save: bool = False) -> None:
        """Set user-specific persistence data in the persistence layer.

        Args:
            key (str): The key under which to store the user-specific data.
            user_data (JsonValue | BaseModel): The user-specific data to set: a JSON-compatible value
                (dicts, lists, strings, numbers, bools, or None), or a pydantic model. A model is stored
                via its `.model_dump(mode="json")`, as plain data -- :meth:`get_user_data` always returns
                a JsonValue, not a reconstructed model instance, so re-validate it against your model type
                yourself (e.g. `MyModel.model_validate(persistence.get_user_data(key))`) if you need it back.
            save (bool): Whether to save the updated persistence data to file after storing the data. Defaults to False.

        Raises:
            TypeError: If `user_data` isn't JSON-round-trippable.

        """
        if isinstance(user_data, BaseModel):
            user_data = user_data.model_dump(mode="json")
        try:
            round_tripped = json.loads(json.dumps(user_data))
        except TypeError as e:
            raise TypeError(f"User data for key '{key}' must be JSON-serializable (dicts, lists, strings, numbers, bools, or None): {e}") from e
        if round_tripped != user_data:
            raise TypeError(
                f"User data for key '{key}' does not round-trip through JSON unchanged; "
                "store a JSON-safe equivalent instead (e.g. a dict via `.model_dump(mode='json')` instead of a model instance).",
            )
        self.user_persistence[key] = user_data
        logging.debug("User-specific persistence data stored under key '%s'.", key)
        if save:
            self.save()

    def get_user_data(self, key: str, expected_type: type[T] | None = None, default: T = None) -> T:
        """Get user-specific persistence data.

        Args:
            key (str): The key under which the user-specific data is stored.
            expected_type (type[T] | None): If given, a pydantic model type to validate the stored data
                against, returning a reconstructed model instance. If None (the default), the raw stored
                JsonValue is returned as-is.
            default (T): The value to return if no data is stored under `key`. Defaults to None.

        Raises:
            TypeError: If `expected_type` is given but isn't a BaseModel subclass.

        Returns:
            T: The stored user-specific data (validated against `expected_type` if given), or
                `default` if `key` isn't present.

        """
        if key not in self.user_persistence:
            return default
        raw = self.user_persistence[key]
        if expected_type is None:
            return raw
        if not (isinstance(expected_type, type) and issubclass(expected_type, BaseModel)):
            raise TypeError(f"expected_type must be a BaseModel subclass, got {expected_type!r}.")
        return expected_type.model_validate(raw)

    def delete_user_data(self, key: str, save: bool = False) -> None:
        """Delete user-specific persistence data.

        Args:
            key (str): The key under which the user-specific data is stored.
            save (bool): Whether to save the updated persistence data to file after deleting the data. Defaults to False.

        """
        if key in self.user_persistence:
            del self.user_persistence[key]
            logging.debug("User-specific persistence data deleted for key '%s'.", key)
            if save:
                self.save()
        else:
            logging.warning("Attempted to delete non-existent user-specific persistence data for key '%s'.", key)
