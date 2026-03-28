from __future__ import annotations  # Until Python 3.14

from enum import Enum
from pathlib import Path


class SupportedFileExtensions(str, Enum):
    SMAL = ".smal"
    YAML = ".yaml"
    YML = ".yml"

    @classmethod
    def is_smal_file(cls, filepath: str | Path, check_exists: bool = False) -> bool:
        filepath = Path(filepath)
        if check_exists and not filepath.is_file():
            raise FileNotFoundError(f"SMAL file not found: {filepath}")
        return filepath.suffix in cls.all()

    @classmethod
    def all(cls) -> set[str]:
        return {sfe.value for sfe in cls}


class SupportedCodeLangs(str, Enum):
    C = "c"
    # CPP = "cpp"
    # RUST = "rust"

    @classmethod
    def is_supported_lang(cls, lang: str) -> bool:
        return lang in cls.all()

    @classmethod
    def all(cls) -> set[str]:
        return {scl.value for scl in cls}
