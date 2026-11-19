"""Package defining the per-language naming conventions for SMAL code generation."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from smal.utilities import constants as SMALConstants

if TYPE_CHECKING:
    from smal.codegen.naming.language_naming_layer import LanguageNamingLayer


def get_naming_layer(lang: str) -> type[LanguageNamingLayer]:
    """Get the naming layer for the given language.

    Each language package `smal.codegen.naming.<lang>` must define a module-level `NAMING_LAYER`.

    Args:
        lang (str): The language to get the naming layer for.

    Raises:
        ValueError: If the language is not supported.
        RuntimeError: If the language's naming module does not define `NAMING_LAYER`. This is a programmer error.

    Returns:
        type[LanguageNamingLayer]: The language's naming layer.

    """
    if not SMALConstants.SupportedCodeLangs.is_supported_lang(lang):
        raise ValueError(f"Unsupported codegen language: {lang}. Supported languages are: {', '.join(sorted(SMALConstants.SupportedCodeLangs.all()))}")
    module = importlib.import_module(f"smal.codegen.naming.{lang}")
    layer = getattr(module, "NAMING_LAYER", None)
    if layer is None:
        raise RuntimeError(f"Naming module for '{lang}' does not define NAMING_LAYER. This is a programmer error.")
    return layer


def available_naming_layers() -> dict[str, type[LanguageNamingLayer]]:
    """Get the naming layer of every supported language that has one yet.

    Returns:
        dict[str, type[LanguageNamingLayer]]: The naming layers, keyed by language.

    """
    layers: dict[str, type[LanguageNamingLayer]] = {}
    for lang in sorted(SMALConstants.SupportedCodeLangs.all()):
        try:
            layers[lang] = get_naming_layer(lang)
        except ModuleNotFoundError as exc:
            if exc.name != f"smal.codegen.naming.{lang}":  # A language without a naming module yet is fine. Anything else is a real error.
                raise
    return layers
