import importlib
from dataclasses import dataclass

from smal.smal_primitive import SMALPrimitive
from smal.utilities import constants as SMALConstants


@dataclass
class TargetPrimitive:
    name: str
    size_bytes: int


def get_target_primitive(smal_primitive: SMALPrimitive, lang: str) -> TargetPrimitive:
    if not SMALConstants.SupportedCodeLangs.is_supported_lang(lang):
        raise ValueError(f"Unsupported codegen language: {lang}. Supported languages are: {', '.join(SMALConstants.SupportedCodeLangs.all())}")
    module = importlib.import_module(f"smal.codegen.{lang}.primitives")
    if not hasattr(module, "SMAL_PRIMITIVE_DECODER_RING"):
        raise RuntimeError(f"Codegen language package '{lang}' does not properly define primitive decoder ring. This is a programmer error.")
    decoder_ring: dict[SMALPrimitive, str] = getattr(module, "SMAL_PRIMITIVE_DECODER_RING")
    if not isinstance(decoder_ring, dict):
        raise RuntimeError(f"Codegen language package '{lang}' improperly defines primitive decoder ring as a non-dict type. This is a programmer error.")
    decoded_primitive = decoder_ring.get(smal_primitive)
    if decoded_primitive is None:
        raise ValueError(f"Codegen language package '{lang}' does not define a primitive that maps to SMAL primitive '{smal_primitive.value}'")
    if not hasattr(module, "LOCAL_PRIMITIVE_SIZES_BYTES"):
        raise RuntimeError(f"Codegen language package '{lang}' does not properly define local primitive sizes. This is a programmer error.")
    local_primitive_sizes_bytes: dict[str, int] = getattr(module, "LOCAL_PRIMITIVE_SIZES_BYTES")
    if not isinstance(local_primitive_sizes_bytes, dict):
        raise RuntimeError(f"Codegen language package '{lang}' improperly defines local primitive sizes as a non-dict type. This is a programmer error.")
    local_primitive_size = local_primitive_sizes_bytes.get(decoded_primitive)
    if local_primitive_size is None:
        raise ValueError(f"Codegen language package '{lang}' does not define a size in bytes for local primitive that maps to SMAL primitive '{smal_primitive.value}'")
    return TargetPrimitive(decoded_primitive, local_primitive_size)
