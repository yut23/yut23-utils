# SPDX-FileCopyrightText: 2024-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for working with floating-point numbers."""

from __future__ import annotations

import enum
import math
import struct
from dataclasses import dataclass
from functools import cached_property
from typing import cast


class Precision(enum.Enum):
    BINARY16 = 16
    BINARY32 = 32
    BINARY64 = 64
    HALF = BINARY16
    SINGLE = BINARY32
    DOUBLE = BINARY64

    @cached_property
    def total_bits(self) -> int:
        return self.value

    @cached_property
    def exp_bits(self) -> int:
        return {
            Precision.BINARY16: 5,
            Precision.BINARY32: 8,
            Precision.BINARY64: 11,
        }[self]

    @cached_property
    def mant_bits(self) -> int:
        return {
            Precision.BINARY16: 10,
            Precision.BINARY32: 23,
            Precision.BINARY64: 52,
        }[self]

    @cached_property
    def float_struct_fmt(self) -> str:
        return {
            Precision.BINARY16: "e",
            Precision.BINARY32: "f",
            Precision.BINARY64: "d",
        }[self]

    @cached_property
    def uint_struct_fmt(self) -> str:
        return {
            Precision.BINARY16: "H",
            Precision.BINARY32: "L",
            Precision.BINARY64: "Q",
        }[self]

    @cached_property
    def int_struct_fmt(self) -> str:
        return self.uint_struct_fmt.lower()

    @cached_property
    def bias(self) -> int:
        return (1 << (self.exp_bits - 1)) - 1


def float_to_uint(x: float, /, prec: Precision = Precision.DOUBLE) -> int:
    return cast(
        int,
        struct.unpack(
            "<" + prec.uint_struct_fmt, struct.pack("<" + prec.float_struct_fmt, x)
        )[0],
    )


def float_to_sint(x: float, /, prec: Precision = Precision.DOUBLE) -> int:
    return cast(
        int,
        struct.unpack(
            "<" + prec.int_struct_fmt, struct.pack("<" + prec.float_struct_fmt, x)
        )[0],
    )


float_to_int = float_to_uint


def uint_to_float(q: int, /, prec: Precision = Precision.DOUBLE) -> float:
    return cast(
        float,
        struct.unpack(
            "<" + prec.float_struct_fmt, struct.pack("<" + prec.uint_struct_fmt, q)
        )[0],
    )


def sint_to_float(q: int, /, prec: Precision = Precision.DOUBLE) -> float:
    return cast(
        float,
        struct.unpack(
            "<" + prec.float_struct_fmt, struct.pack("<" + prec.int_struct_fmt, q)
        )[0],
    )


int_to_float = uint_to_float


def ulp_diff(
    a: float,
    b: float,
    /,
    prec: Precision = Precision.DOUBLE,
    *,
    include_sign: bool = False,
) -> int:
    """Return the number of representable `prec` values in the range [a, b)."""
    if not math.isfinite(a) or not math.isfinite(b):
        msg = "only finite values can be compared"
        raise ValueError(msg)
    if a == b:
        # this case also covers 0.0 vs -0.0, which compare equal but have
        # different representations
        return 0
    if a > b:
        # pylint: disable-next=arguments-out-of-order
        ulps = ulp_diff(b, a, prec)
        if include_sign:
            ulps *= -1
        return ulps
    # b is now greater than a in value
    if math.copysign(1.0, a) != math.copysign(1.0, b):
        # different signs: split the interval at zero
        return ulp_diff(a, -0.0, prec=prec) + ulp_diff(0.0, b, prec)
    # subtract the smaller in magnitude from the larger
    smaller, larger = sorted((a, b), key=abs)
    return float_to_uint(larger, prec) - float_to_uint(smaller, prec)


def compare_ulp(
    a: float, b: float, /, ulps: int, prec: Precision = Precision.DOUBLE
) -> bool:
    """Check if two numbers match to within a specified number of `prec` ULPs."""
    if ulps < 0:
        msg = "ulps must be non-negative"
        raise ValueError(msg)
    return ulp_diff(a, b, prec, include_sign=False) <= ulps


def _make_mask(bits: int) -> int:
    return (1 << bits) - 1


def nextafter(x: float, y: float, /, prec: Precision = Precision.DOUBLE) -> float:
    # based on glibc implementation
    hx = float_to_uint(x, prec)
    hy = float_to_uint(y, prec)
    # mask out the sign bit
    ix = hx & _make_mask(prec.total_bits - 1)
    # check for NaN
    if math.isnan(x) or math.isnan(y):
        return x + y
    if x == y:
        return y
    if ix == 0:
        # return +/- minsubnormal
        # 0x4010_0000_0000_0001
        return uint_to_float(hy & (1 << (prec.total_bits - 1)) | 1, prec)
    if x >= 0:  # x > 0
        if x > y:  # x > y, x -= ulp
            hx -= 1
        else:  # x < y, x += ulp
            hx += 1
    else:  # x < 0, hx has the opposite sign  # noqa: PLR5501
        if x < y:  # x < y, x -= ulp
            hx -= 1
        else:  # x > y, x += ulp
            hx += 1
    return uint_to_float(hx, prec)


@dataclass(frozen=True)
class FloatInspector:
    float_val: float
    int_val: int
    prec: Precision = Precision.DOUBLE

    def __init__(
        self,
        float_val: float | None = None,
        *,
        int_val: int | None = None,
        prec: Precision = Precision.DOUBLE,
    ):
        object.__setattr__(self, "prec", prec)
        if (float_val is None) == (int_val is None):
            msg = "exactly one of float_val and int_val must be specified"
            raise TypeError(msg)
        if float_val is not None:
            int_val = float_to_uint(float_val, self.prec)
        assert int_val is not None  # noqa: S101
        # cast back to a float to get the exact value for the given precision
        float_val = uint_to_float(int_val, self.prec)
        object.__setattr__(self, "float_val", float_val)
        object.__setattr__(self, "int_val", int_val)

    @cached_property
    def raw_sign(self) -> int:
        return (self.int_val >> (self.prec.exp_bits + self.prec.mant_bits)) & 1

    @cached_property
    def raw_exponent(self) -> int:
        return (self.int_val >> self.prec.mant_bits) & _make_mask(self.prec.exp_bits)

    @cached_property
    def raw_mantissa(self) -> int:
        return self.int_val & _make_mask(self.prec.mant_bits)

    def __str__(self) -> str:
        return (
            f"FloatData({float(self)} = "
            f"{self.raw_sign} * 2^{self.exponent} * {self.mantissa}; "
            f"s={self.raw_sign}, "
            f"e={self.raw_exponent:0{self.prec.exp_bits}b}, "
            f"m=(1){self.raw_mantissa:0{self.prec.mant_bits}b})"
        )

    def __repr__(self) -> str:
        f = float(self)
        return f"FloatData({f}; {f.hex()})"

    def __float__(self) -> float:
        return self.float_val

    @cached_property
    def exponent(self) -> int:
        return self.raw_exponent - ((1 << (self.prec.exp_bits - 1)) - 1)

    @cached_property
    def mantissa(self) -> float:
        frac = self.raw_mantissa / (1 << self.prec.mant_bits)
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
        return (
            self.raw_exponent == _make_mask(self.prec.exp_bits)
            and self.raw_mantissa == 0
        )

    def is_nan(self) -> bool:
        return (
            self.raw_exponent == _make_mask(self.prec.exp_bits)
            and self.raw_mantissa != 0
        )

    def is_subnormal(self) -> bool:
        return self.raw_exponent == 0 and self.raw_mantissa != 0
