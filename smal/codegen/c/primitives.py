
from typing import Final
from smal.smal_primitive import SMALPrimitive

SMAL_PRIMITIVE_DECODER_RING: Final[dict[SMALPrimitive, str]] = {
    SMALPrimitive.BOOL: "uint8_t",
    SMALPrimitive.CHAR8: "uint8_t",
    SMALPrimitive.FLOAT32: "float",
    SMALPrimitive.FLOAT64: "double",
    SMALPrimitive.UINT8: "uint8_t",
    SMALPrimitive.INT8: "int8_t",
    SMALPrimitive.UINT16: "uint16_t",
    SMALPrimitive.INT16: "int16_t",
    SMALPrimitive.UINT32: "uint32_t",
    SMALPrimitive.INT32: "int32_t",
    SMALPrimitive.UINT64: "uint64_t",
    SMALPrimitive.INT64: "int64_t",
    SMALPrimitive.BYTE: "uint8_t",
    SMALPrimitive.BYTES: "uint8_t[]"  # Fixed arrays only
}

LOCAL_PRIMITIVE_SIZES_BYTES: Final[dict[str, int]] = {
    "uint8_t": 1,
    "int8_t": 1,
    "uint16_t": 2,
    "int16_t": 2,
    "uint32_t": 4,
    "int32_t": 4,
    "float": 4,
    "double": 8,
    "uint64_t": 8,
    "int64_t": 8,
}
