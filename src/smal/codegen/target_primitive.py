"""Module defining the TargetPrimitive dataclass and utility functions for mapping SMAL primitives to target language primitives."""

# ruff: noqa: E501 - Line too long

from __future__ import annotations  # Until Python 3.14

import importlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from smal.utilities import constants as SMALConstants

if TYPE_CHECKING:
    from smal.utilities.smal_primitive import SMALPrimitive


@dataclass
class TargetPrimitive:
    """Dataclass representing an arbitrary primitive datatype on an arbitrary Target device."""

    name: str
    size_bytes: int


def get_target_primitive(smal_primitive: SMALPrimitive, lang: str) -> TargetPrimitive:
    """Get the target primitive corresponding to the given SMAL primitive for the given language.

    Args:
        smal_primitive (SMALPrimitive): The SMAL primitive to map to a target primitive.
        lang (str): The programming language for which to retrieve the target primitive.

    Raises:
        ValueError: If the specified language is not supported or if the SMAL primitive does not have a corresponding target primitive defined in the language's codegen package.
        RuntimeError: If the codegen language package does not properly define the primitive decoder ring or local primitive sizes, or if they are defined with incorrect types. This indicates a programmer error in the codegen package.
        TypeError: If the primitive decoder ring or local primitive sizes are defined with incorrect types in the codegen language package. This indicates a programmer error in the codegen package.
        ValueError: If the SMAL primitive does not have a corresponding target primitive defined in the codegen language package. This indicates a programmer error in the codegen package.
        RuntimeError: If the codegen language package does not properly define the local primitive sizes, or if they are defined with incorrect types. This indicates a programmer error in the codegen package.
        TypeError: If the local primitive sizes are defined with incorrect types in the codegen language package. This indicates a programmer error in the codegen package.
        ValueError: If the local primitive size for the target primitive is not defined in the codegen language package. This indicates a programmer error in the codegen package.

    Returns:
        TargetPrimitive: The target primitive corresponding to the given SMAL primitive for the specified language.

    """
    if not SMALConstants.SupportedCodeLangs.is_supported_lang(lang):
        raise ValueError(f"Unsupported codegen language: {lang}. Supported languages are: {', '.join(SMALConstants.SupportedCodeLangs.all())}")
    module = importlib.import_module(f"smal.codegen.{lang}.primitives")
    if not hasattr(module, "SMAL_PRIMITIVE_DECODER_RING"):
        raise RuntimeError(f"Codegen language package '{lang}' does not properly define primitive decoder ring. This is a programmer error.")
    decoder_ring: dict[SMALPrimitive, str] = module.SMAL_PRIMITIVE_DECODER_RING
    if not isinstance(decoder_ring, dict):
        raise TypeError(f"Codegen language package '{lang}' improperly defines primitive decoder ring as a non-dict type. This is a programmer error.")
    decoded_primitive = decoder_ring.get(smal_primitive)
    if decoded_primitive is None:
        raise ValueError(f"Codegen language package '{lang}' does not define a primitive that maps to SMAL primitive '{smal_primitive.value}'")
    if not hasattr(module, "LOCAL_PRIMITIVE_SIZES_BYTES"):
        raise RuntimeError(f"Codegen language package '{lang}' does not properly define local primitive sizes. This is a programmer error.")
    local_primitive_sizes_bytes: dict[str, int] = module.LOCAL_PRIMITIVE_SIZES_BYTES
    if not isinstance(local_primitive_sizes_bytes, dict):
        raise TypeError(f"Codegen language package '{lang}' improperly defines local primitive sizes as a non-dict type. This is a programmer error.")
    local_primitive_size = local_primitive_sizes_bytes.get(decoded_primitive)
    if local_primitive_size is None:
        raise ValueError(
            f"Codegen language package '{lang}' does not define a size in bytes for local primitive that maps to SMAL primitive '{smal_primitive.value}'"
        )
    return TargetPrimitive(decoded_primitive, local_primitive_size)
