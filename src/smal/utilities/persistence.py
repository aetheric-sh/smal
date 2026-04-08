"""Module defining utilities for persistence of data."""

from __future__ import annotations  # Until Python 3.14

import shutil
from pathlib import Path
from typing import ClassVar

from platformdirs import user_data_dir
from pydantic import BaseModel, Field

from smal.utilities.corrections import ALL_CORRECTIONS, Correction
from smal.utilities.rules import ALL_RULES, Rule


class SMALPersistence(BaseModel):
    """Model representing the persistence of SMAL data, including rules and corrections."""

    DEFAULT_PATH: ClassVar[Path] = Path(user_data_dir(appname="smal", appauthor=False)) / "persistence.json"

    rules: dict[str, bool] = Field(
        default_factory=lambda: dict.fromkeys(ALL_RULES, True),
        description="A dictionary mapping rule names to their enabled/disabled status.",
    )
    corrections: dict[str, bool] = Field(
        default_factory=lambda: dict.fromkeys(ALL_CORRECTIONS, True),
        description="A dictionary mapping correction names to their enabled/disabled status.",
    )

    def save(self, path: Path | str = DEFAULT_PATH) -> None:
        """Save the persistence data to a JSON file.

        Args:
            path (Path | str): The path to the JSON file where the data will be saved. Defaults to DEFAULT_PATH.

        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=4))

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
            return cls.model_validate_json(f.read())

    @staticmethod
    def clean() -> None:
        """Clean the persistence data by deleting the persistence file and its application directory."""
        app_dir = SMALPersistence.DEFAULT_PATH.parent
        if app_dir.exists():
            shutil.rmtree(app_dir)

    def enable_rule(self, rule: str | Rule, enabled: bool) -> None:
        """Enable or disable a specific rule.

        Args:
            rule (str | Rule): The name of the rule to enable or disable, or a Rule object.
            enabled (bool): Whether to enable (True) or disable (False) the rule.

        """
        rule_name = rule if isinstance(rule, str) else rule.name
        if rule_name not in self.rules:
            raise ValueError(f"Rule '{rule_name}' is not recognized.")
        self.rules[rule_name] = enabled

    def enable_correction(self, correction: str | Correction, enabled: bool) -> None:
        """Enable or disable a specific correction.

        Args:
            correction (str | Correction): The name of the correction to enable or disable, or a Correction object.
            enabled (bool): Whether to enable (True) or disable (False) the correction.

        """
        correction_name = correction if isinstance(correction, str) else correction.name
        if correction_name not in self.corrections:
            raise ValueError(f"Correction '{correction_name}' is not recognized.")
        self.corrections[correction_name] = enabled
