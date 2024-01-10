# SPDX-FileCopyrightText: 2023-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

import math
import sys

import pytest
from hypothesis import assume, example, given, note
from hypothesis import strategies as st

from yut23_utils.fp import (
    FloatInspector,
    compare_ulp,
    float_to_int,
    int_to_float,
    ulp_diff,
)


@given(st.floats())
def test_float_to_int(x_flt: float) -> None:
    x_int = float_to_int(x_flt)
    assert isinstance(x_int, int)
    assert 0 <= x_int < 1 << 64
    x_flt_2 = int_to_float(x_int)
    if math.isnan(x_flt):
        assert math.isnan(x_flt_2)
    else:
        assert x_flt_2 == x_flt


@given(st.integers(min_value=0, max_value=(1 << 64) - 1))
def test_int_to_float(x_int: int) -> None:
    x_flt = int_to_float(x_int)
    assert float_to_int(x_flt) == x_int


@st.composite
def float_pairs(draw: st.DrawFn, max_ulps: int) -> tuple[float, float, int]:
    a = draw(st.floats(allow_nan=False, allow_infinity=False))
    ulps = draw(st.integers(min_value=-max_ulps, max_value=max_ulps))

    b = a
    direction = math.copysign(math.inf, ulps)
    for _ in range(abs(ulps)):
        b = math.nextafter(b, direction)
        assume(not math.isinf(b))

    note(f"a = {FloatInspector(a)}\nb = {FloatInspector(b)}")
    return a, b, ulps


@given(float_pairs(max_ulps=100))
@example((0.0, -5e-324, -1))
@example((5e-324, 0.0, -1))
@example((5e-324, -0.0, -1))
@example((-5e-324, 5e-324, 2))
def test_ulp_diff(args: tuple[float, float, int]) -> None:
    a, b, ulps = args
    assert ulp_diff(a, b) == abs(ulps)
    assert ulp_diff(a, b, include_sign=True) == ulps


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (math.inf, 3.14),
        (math.inf, math.inf),
        (-math.inf, math.inf),
        (math.nan, -2.718),
        (math.nan, math.nan),
    ],
)
def test_ulp_diff_errors(a: float, b: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        ulp_diff(a, b)
    with pytest.raises(ValueError, match="finite"):
        ulp_diff(b, a)  # pylint: disable=arguments-out-of-order
    with pytest.raises(ValueError, match="finite"):
        ulp_diff(a, b, include_sign=True)
    with pytest.raises(ValueError, match="finite"):
        ulp_diff(b, a, include_sign=True)


@given(float_pairs(max_ulps=100))
@example((-5e-324, 5e-324, 2))
def test_compare_ulp(args: tuple[float, float, int]) -> None:
    a, b, ulps = args
    assert compare_ulp(a, b, abs(ulps))
    if abs(ulps) > 0:
        assert not compare_ulp(a, b, abs(ulps) - 1)
    assert compare_ulp(a, b, abs(ulps) + 1)


def test_compare_ulp_errors() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        compare_ulp(1.0, 1.0, -1)


@given(st.floats())
def test_float_inspector(x: float) -> None:
    fi = FloatInspector(x)
    note(f"fi={fi} (subnormal: {fi.is_subnormal()})")
    if not math.isnan(x):
        assert float(fi) == x
    # convert to an int to check raw NaN representation
    assert float_to_int(float(fi)) == float_to_int(x)

    # try manually reconstructing the value from the mantissa and exponent
    if math.isfinite(x):
        reconstructed = math.ldexp(fi.mantissa, fi.exponent)
        assert reconstructed == x

    # check interrogator methods
    # need to use copysign rather than `x < 0.0` to handle -0.0 properly
    is_negative = math.copysign(1.0, x) == -1.0
    assert fi.is_negative() == is_negative
    assert fi.is_inf() == math.isinf(x)
    assert fi.is_nan() == math.isnan(x)
    is_subnormal = 0 < abs(x) < sys.float_info.min
    assert fi.is_subnormal() == is_subnormal
