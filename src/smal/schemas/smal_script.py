"""Module defining the schema for SMAL scripts: structured sequences of messages and commands that can be executed within the SMAL REPL environment."""

from __future__ import annotations  # Until Python 3.14

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from smal.utilities import constants as SMALConstants


class SMALScriptCommand(BaseModel):
    """Model describing a singular command within a SMAL script in the SMAL REPL environment."""

    cmd: str = Field(..., description="The content of the command to be executed in the SMAL REPL.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional arbitrary metadata associated with the command.")
    pre_delay_ms: int = Field(default=0, description="Delay before command execution in milliseconds.")
    post_delay_ms: int = Field(default=0, description="Delay after command execution in milliseconds.")
    exc_count: int = Field(default=1, ge=1, description="Number of times to execute the command.")


class SMALScript(BaseModel):
    """Model describing a SMAL script file (`.smalscr`), which is a structured sequence of commands that can be executed in the SMAL REPL environment."""

    name: str
    cmds: list[SMALScriptCommand] = Field(default_factory=list, description="List of commands in the script.")

    @classmethod
    def from_file(cls, file_path: str | Path) -> SMALScript:
        """Parse a SMAL script from a `.smalscr` file.

        Args:
            file_path (str | Path): The path to the `.smalscr` file containing the script definition.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the specified file is not a file.
            ValueError: If there is an error parsing the YAML content.
            TypeError: If the YAML content is not a dictionary at the top level.
            ValueError: If there is an error validating the script data.

        Returns:
            SMALScript: The parsed SMAL script instance.

        """
        fp = Path(file_path)
        if not fp.exists():
            raise FileNotFoundError(f"Script file not found: {file_path}")
        if not fp.is_file():
            raise ValueError(f"Provided path is not a file: {file_path}")
        if fp.suffix.lower() != SMALConstants.SMAL_SCRIPT_FILE_EXTENSION:
            raise ValueError(f"Invalid file extension for SMAL script: {file_path}. Expected '{SMALConstants.SMAL_SCRIPT_FILE_EXTENSION}'")
        file_text = fp.read_text()
        try:
            yaml_data = yaml.safe_load(file_text)
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML from file {file_path}") from e
        if not isinstance(yaml_data, dict):
            raise TypeError(f"YAML content must be a dictionary at the top level in file: {file_path}")
        try:
            script = SMALScript.model_validate(yaml_data)
        except Exception as e:
            raise ValueError(f"Error validating script data from file {file_path}") from e
        return script

    def to_file(self, file_path: str | Path) -> None:
        """Export the SMAL script to a `.smalscr` file.

        Args:
            file_path (str | Path): The path to the file to which the script should be exported.

        """
        fp = Path(file_path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(yaml.safe_dump(self.model_dump(mode="json")))
