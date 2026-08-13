"""Module defining constants used throughout the SMAL project."""

from __future__ import annotations  # Until Python 3.14

from enum import StrEnum
from pathlib import Path
from typing import Final

APP_NAME: Final[str] = "State Machine Abstraction Language"
APP_NAME_ABBREV: Final[str] = "SMAL"
APP_NAME_FULL: Final[str] = f"{APP_NAME} ({APP_NAME_ABBREV})"
REPL_NAME: Final[str] = f"{APP_NAME_ABBREV}".lower()

SMAL_FILE_EXTENSION: Final[str] = f".{APP_NAME_ABBREV.lower()}"
SMAL_SCRIPT_FILE_EXTENSION: Final[str] = f"{SMAL_FILE_EXTENSION}scr"
PYTHON_SCRIPT_FILE_EXTENSION: Final[str] = ".py"


class SupportedFileExtensions(StrEnum):
    """Enumeration of supported file extensions for SMAL files."""

    SMAL = SMAL_FILE_EXTENSION
    # YAML = ".yaml"
    # YML = ".yml"

    @classmethod
    def is_smal_file(cls, filepath: str | Path, check_exists: bool = False) -> bool:
        """Get whether the file at the given filepath is a valid SMAL file.

        Args:
            filepath (str | Path): The path to the file to check.
            check_exists (bool, optional): Whether to check if the file exists. Defaults to False.

        Raises:
            FileNotFoundError: If `check_exists` is True and the file does not exist.

        Returns:
            bool: True if the file is a valid SMAL file, False otherwise.

        """
        filepath = Path(filepath)
        if check_exists and not filepath.is_file():
            raise FileNotFoundError(f"SMAL file not found: {filepath}")
        return filepath.suffix in cls.all()

    @classmethod
    def all(cls) -> set[str]:
        """Get all valid SMAL file extensions.

        Returns:
            set[str]: The set of all valid SMAL file extensions.

        """
        return {sfe.value for sfe in cls}


class SupportedCodeLangs(StrEnum):
    """Enumeration of supported code generation languages for SMAL files."""

    C = "c"
    # CPP = "cpp"
    # RUST = "rust"

    @classmethod
    def is_supported_lang(cls, lang: str) -> bool:
        """Get whether the given language is supported for code generation by SMAL.

        Args:
            lang (str): The language to check.

        Returns:
            bool: True if the language is supported, False otherwise.

        """
        return lang in cls.all()

    @classmethod
    def all(cls) -> set[str]:
        """Get all supported code generation languages.

        Returns:
            set[str]: The set of all supported code generation languages.

        """
        return {scl.value for scl in cls}
