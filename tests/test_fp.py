# SPDX-FileCopyrightText: 2024-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

import math

import pytest
from hypothesis import assume, example, given, note
from hypothesis import strategies as st

from yut23_utils.fp import (
    FloatInspector,
    Precision,
    compare_ulp,
    float_to_int,
    int_to_float,
    nextafter,
    ulp_diff,
)


@st.composite
def floats_with_prec(draw: st.DrawFn, *args, **kwargs) -> tuple[float, Precision]:
    prec = draw(st.sampled_from(Precision))
    if "width" in kwargs:
        msg = "floats_with_prec() got an unexpected keyword argument 'width'"
        raise TypeError(msg)
    kwargs["width"] = prec.total_bits
    x = draw(st.floats(*args, **kwargs))
    return x, prec


@st.composite
def integers_with_prec(draw: st.DrawFn) -> tuple[int, Precision]:
    prec = draw(st.sampled_from(Precision))
    x = draw(st.integers(min_value=0, max_value=(1 << prec.total_bits) - 1))
    return x, prec


@given(floats_with_prec())
@example((float("nan"), Precision.BINARY64))
@example((float("nan"), Precision.BINARY32))
@example((float("nan"), Precision.BINARY16))
def test_float_to_int(entry: tuple[float, Precision]) -> None:
    x_flt, prec = entry
    x_int = float_to_int(x_flt, prec=prec)
    assert isinstance(x_int, int)
    assert 0 <= x_int < 1 << prec.total_bits
    x_flt_2 = int_to_float(x_int, prec=prec)
    if math.isnan(x_flt):
        assert math.isnan(x_flt_2)
    else:
        assert x_flt_2 == x_flt


@given(integers_with_prec())
def test_int_to_float(entry: tuple[int, Precision]) -> None:
    x_int, prec = entry
    x_flt = int_to_float(x_int, prec=prec)
    # binary16 NaNs aren't round-tripped correctly
    assume(not (prec is Precision.BINARY16 and math.isnan(x_flt)))
    assert float_to_int(x_flt, prec=prec) == x_int


@given(st.floats(width=64), st.floats(width=64))
def test_nextafter(x: float, y: float) -> None:
    expected = math.nextafter(x, y)
    actual = nextafter(x, y, prec=Precision.BINARY64)
    # compare hex representations to handle NaN and signed zeros
    assert actual.hex() == expected.hex()


@st.composite
def float_pairs(draw: st.DrawFn, max_ulps: int) -> tuple[float, float, int, Precision]:
    prec = draw(st.sampled_from(Precision))
    a = draw(st.floats(allow_nan=False, allow_infinity=False, width=prec.total_bits))
    ulps = draw(st.integers(min_value=-max_ulps, max_value=max_ulps))

    b = a
    direction = math.copysign(math.inf, ulps)
    for _ in range(abs(ulps)):
        b = nextafter(b, direction, prec=prec)
        assume(not math.isinf(b))

    note(f"a = {FloatInspector(a, prec=prec)}\nb = {FloatInspector(b, prec=prec)}")
    return a, b, ulps, prec


@given(float_pairs(max_ulps=100))
@example((0.0, -5e-324, -1, Precision.BINARY64))
@example((5e-324, 0.0, -1, Precision.BINARY64))
@example((-5e-324, 5e-324, 2, Precision.BINARY64))
@example((1, 2, 1 << 52, Precision.BINARY64))
@example((2, 4, 1 << 52, Precision.BINARY64))
@example((0, 1, 0x3FF << 52, Precision.BINARY64))
@example((0.0, -1.4e-45, -1, Precision.BINARY32))
@example((1.4e-45, 0.0, -1, Precision.BINARY32))
@example((-1.4e-45, 1.4e-45, 2, Precision.BINARY32))
@example((1, 2, 1 << 23, Precision.BINARY32))
@example((2, 4, 1 << 23, Precision.BINARY32))
@example((0, 1, 0x7F << 23, Precision.BINARY32))
@example((0.0, -5.9e-8, -1, Precision.BINARY16))
@example((5.9e-8, 0.0, -1, Precision.BINARY16))
@example((-5.9e-8, 5.9e-8, 2, Precision.BINARY16))
@example((1, 2, 1 << 10, Precision.BINARY16))
@example((2, 4, 1 << 10, Precision.BINARY16))
@example((0, 1, 0xF << 10, Precision.BINARY16))
def test_ulp_diff(args: tuple[float, float, int, Precision]) -> None:
    a, b, ulps, prec = args
    assert ulp_diff(a, b, prec=prec) == abs(ulps)
    assert ulp_diff(b, a, prec=prec) == abs(ulps)  # pylint: disable=arguments-out-of-order
    assert ulp_diff(a, b, prec=prec, include_sign=True) == ulps
    assert ulp_diff(b, a, prec=prec, include_sign=True) == -ulps
    assert ulp_diff(-b, -a, prec=prec, include_sign=True) == ulps
    assert ulp_diff(-a, -b, prec=prec, include_sign=True) == -ulps


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
        ulp_diff(b, a)
    with pytest.raises(ValueError, match="finite"):
        ulp_diff(a, b, include_sign=True)
    with pytest.raises(ValueError, match="finite"):
        ulp_diff(b, a, include_sign=True)


@given(float_pairs(max_ulps=100))
@example((-5e-324, 5e-324, 2, Precision.BINARY64))
def test_compare_ulp(args: tuple[float, float, int, Precision]) -> None:
    a, b, ulps, prec = args
    assert compare_ulp(a, b, abs(ulps), prec=prec)
    if abs(ulps) > 0:
        assert not compare_ulp(a, b, abs(ulps) - 1, prec=prec)
    assert compare_ulp(a, b, abs(ulps) + 1, prec=prec)


def test_compare_ulp_errors() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        compare_ulp(1.0, 1.0, ulps=-1)


@given(floats_with_prec())
@example((float("nan"), Precision.BINARY64))
@example((float("nan"), Precision.BINARY32))
@example((float("nan"), Precision.BINARY16))
def test_float_inspector(entry: tuple[float, Precision]) -> None:
    x, prec = entry
    fi = FloatInspector(x, prec=prec)
    note(f"fi={fi} (subnormal: {fi.is_subnormal()})")
    if not math.isnan(x):
        assert float(fi) == x
    # convert to an int to check raw NaN representation
    assert float_to_int(float(fi), prec=prec) == float_to_int(x, prec=prec)

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
    min_normal = 1.0 / (1 << (prec.bias - 1))
    is_subnormal = 0 < abs(x) < min_normal
    assert fi.is_subnormal() == is_subnormal
