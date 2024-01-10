# SPDX-FileCopyrightText: 2023-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for working with floating-point numbers."""

import math
import struct
from dataclasses import dataclass, field
from functools import cached_property
from typing import cast


def float_to_int(x: float, /) -> int:
    return cast(int, struct.unpack("<Q", struct.pack("<d", x))[0])


def int_to_float(q: int, /) -> float:
    return cast(float, struct.unpack("<d", struct.pack("<Q", q))[0])


def ulp_diff(a: float, b: float, /, *, include_sign: bool = False) -> int:
    """Return the number of representable FP64 values in the range [a, b)."""
    if not math.isfinite(a) or not math.isfinite(b):
        msg = "only finite values can be compared"
        raise ValueError(msg)
    if a == b:
        return 0
    if a > b:
        # pylint: disable-next=arguments-out-of-order
        ulps = ulp_diff(b, a)
        if include_sign:
            ulps *= -1
        return ulps
    if math.copysign(1.0, a) != math.copysign(1.0, b):
        # different signs: split the interval at zero
        return ulp_diff(a, -0.0) + ulp_diff(0.0, b)
    return abs(float_to_int(a) - float_to_int(b))


def compare_ulp(a: float, b: float, /, ulps: int) -> bool:
    """Check if two numbers match to within a specified number of FP64 ULPs."""
    if ulps < 0:
        msg = "ulps must be non-negative"
        raise ValueError(msg)
    return ulp_diff(a, b, include_sign=False) <= ulps


def _make_mask(bits: int) -> int:
    return (1 << bits) - 1


@dataclass(frozen=True)
class FloatInspector:
    float_val: float
    int_val: int = field(init=False)

    EXP_BITS = 11
    MANT_BITS = 52

    def __post_init__(self):
        object.__setattr__(self, "int_val", float_to_int(self.float_val))

    @cached_property
    def raw_sign(self) -> int:
        return (self.int_val >> (self.EXP_BITS + self.MANT_BITS)) & 1

    @cached_property
    def raw_exponent(self) -> int:
        return (self.int_val >> self.MANT_BITS) & _make_mask(self.EXP_BITS)

    @cached_property
    def raw_mantissa(self) -> int:
        return self.int_val & _make_mask(self.MANT_BITS)

    def __str__(self) -> str:
        return (
            f"FloatData({float(self)} = "
            f"{self.raw_sign} * 2^{self.exponent} * {self.mantissa}; "
            f"s={self.raw_sign}, "
            f"e={self.raw_exponent:011b}, "
            f"m={self.raw_mantissa:052b})"
        )

    def __repr__(self) -> str:
        f = float(self)
        return f"FloatData({f}; {f.hex()})"

    def __float__(self) -> float:
        return self.float_val

    @cached_property
    def exponent(self) -> int:
        return self.raw_exponent - 1023

    @cached_property
    def mantissa(self) -> float:
        frac = self.raw_mantissa / (1 << 52)
        if self.raw_exponent == 0:
            # zero and subnormals
            frac *= 2
        else:
            frac += 1
        if self.raw_sign == 1:
            frac *= -1
        return frac

    def is_negative(self) -> bool:
        return bool(self.raw_sign)

    def is_inf(self) -> bool:
        return self.raw_exponent == _make_mask(self.EXP_BITS) and self.raw_mantissa == 0

    def is_nan(self) -> bool:
        return self.raw_exponent == _make_mask(self.EXP_BITS) and self.raw_mantissa != 0

    def is_subnormal(self) -> bool:
        return self.raw_exponent == 0 and self.raw_mantissa != 0
