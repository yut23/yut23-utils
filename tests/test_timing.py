# SPDX-FileCopyrightText: 2023-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

import math

import pytest
from hypothesis import example, given, note
from hypothesis import strategies as st

from yut23_utils.timing import TimingFormat, TimingInfo, format_time


@given(st.floats(min_value=0, max_value=1e9), st.integers(min_value=1, max_value=10))
@example(0.0, 2)
@example(1e-9, 3)
@example(1e-6, 3)
@example(1e-3, 3)
@example(1.0, 3)
@example(1000.0, 3)
def test_format_time(t: float, precision: int) -> None:
    s = format_time(t, precision=precision, fmt="f")
    note(f"formatted: {s!r}")
    num_str, unit = s.split()
    # unit should be chosen to give a whole number
    if t >= 1e-9:
        assert float(num_str) >= 1.0
    # unit should be chosen to give a number less than 1 of the next larger unit
    if t <= 1.0:
        assert float(num_str) <= 1000.0

    # unit should match these ranges
    if t < 1e-6:
        assert unit == "ns"
    elif t < 1e-3:
        assert unit == "μs"
    elif t < 1.0:
        assert unit == "ms"
    else:
        assert unit == "s"

    # number should have `precision` decimals
    assert len(num_str.partition(".")[2]) == precision


class TestTimingInfo:
    def test_stdev(self):
        times = (1.23, 3.21, 2.75, 2.53)
        info = TimingInfo(times, 1)
        assert info.stdev == pytest.approx(0.8486852577172922)

    def test_stdev_single(self):
        times = (1.0,)
        info = TimingInfo(times, 1)
        assert math.isnan(info.stdev)

    def test_pretty_hyperfine(self):
        times = (1.23, 3.21, 2.75, 2.53)

        info = TimingInfo(times, 1)
        assert (
            info.pretty(TimingFormat.HYPERFINE)
            == """\
  Time (\x1b[1;32mmean\x1b[0m ± \x1b[32m\u03c3\x1b[0m):     \x1b[1;32m 2.430 s\
\x1b[0m ± \x1b[32m 0.849 s\x1b[0m
  Range (\x1b[36mmin\x1b[0m … \x1b[35mmax\x1b[0m):   \x1b[36m 1.230 s\
\x1b[0m … \x1b[35m 3.210 s\x1b[0m    \x1b[2m4 runs, 1 loop each\x1b[0m"""
        )

        info = TimingInfo(times, 3)
        assert info.pretty(TimingFormat.HYPERFINE) == (
            "  Time (\x1b[1;32mmean\x1b[0m ± \x1b[32m\u03c3\x1b[0m):"
            "     \x1b[1;32m 2.430 s\x1b[0m ± \x1b[32m 0.849 s\x1b[0m\n"
            "  Range (\x1b[36mmin\x1b[0m … \x1b[35mmax\x1b[0m):"
            "   \x1b[36m 1.230 s\x1b[0m … \x1b[35m 3.210 s\x1b[0m"
            "    \x1b[2m4 runs, 3 loops each\x1b[0m"
        )

    def test_pretty_hyperfine_single(self):
        times = (3.14159,)

        info = TimingInfo(times, 1)
        assert info.pretty(TimingFormat.HYPERFINE) == (
            "  Time (\x1b[1;32mabs\x1b[0m ≡):"
            "        \x1b[1;32m 3.142 s\x1b[0m"
            "               \x1b[2m1 run, 1 loop each\x1b[0m"
        )

        info = TimingInfo(times, 2)
        assert info.pretty(TimingFormat.HYPERFINE) == (
            "  Time (\x1b[1;32mabs\x1b[0m ≡):"
            "        \x1b[1;32m 3.142 s\x1b[0m"
            "               \x1b[2m1 run, 2 loops each\x1b[0m"
        )

    def test_pretty_ipython(self):
        times = (1.23, 3.21, 2.75, 2.53)

        info = TimingInfo(times, 1)
        assert (
            info.pretty(TimingFormat.IPYTHON)
            == "2.43 s ± 849 ms per loop (mean ± std. dev. of 4 loops, 1 loop each)"
        )

        info = TimingInfo(times, 3)
        assert (
            info.pretty(TimingFormat.IPYTHON)
            == "2.43 s ± 849 ms per loop (mean ± std. dev. of 4 loops, 3 loops each)"
        )

    def test_pretty_ipython_single(self):
        times = (3.14159,)

        info = TimingInfo(times, 1)
        assert info.pretty(TimingFormat.IPYTHON) == (
            "3.14 s ± nan s per loop (mean ± std. dev. of 1 loop, 1 loop each)"
        )

        info = TimingInfo(times, 2)
        assert info.pretty(TimingFormat.IPYTHON) == (
            "3.14 s ± nan s per loop (mean ± std. dev. of 1 loop, 2 loops each)"
        )

    def test_pretty_timeit(self):
        times = (1.23, 3.21, 2.75, 2.53)

        info = TimingInfo(times, 1)
        assert info.pretty(TimingFormat.TIMEIT) == "1 loop, best of 4: 1.23 s per loop"

        info = TimingInfo(times, 3)
        assert info.pretty(TimingFormat.TIMEIT) == "3 loops, best of 4: 1.23 s per loop"

    def test_pretty_timeit_single(self):
        times = (3.14159,)

        info = TimingInfo(times, 1)
        assert info.pretty(TimingFormat.TIMEIT) == (
            "1 loop, best of 1: 3.14 s per loop"
        )

        info = TimingInfo(times, 2)
        assert info.pretty(TimingFormat.TIMEIT) == (
            "2 loops, best of 1: 3.14 s per loop"
        )
