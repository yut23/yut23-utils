# SPDX-FileCopyrightText: 2023-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import enum
import math
import statistics
import warnings
from dataclasses import dataclass
from functools import cached_property
from timeit import Timer, default_timer
from typing import Any, Callable

__all__ = ["TimingFormat", "TimingInfo", "timeit", "ContextTimer"]


def _calc_order(timespan: float) -> int:
    if timespan == 0:
        return 3
    return min(max(0, -int(math.floor(math.log10(timespan)) // 3)), 3)


# modified from IPython/core/magics/execution.py
def format_time(
    timespan: float,
    precision: int = 3,
    *,
    fmt: str = "g",
    order: int | None = None,
) -> str:
    """Formats the timespan in a human readable form"""

    units = ["s", "ms", "μs", "ns"]
    scaling = [1, 1e3, 1e6, 1e9]

    if order is None:
        order = _calc_order(timespan)
    return f"{timespan * scaling[order]:.{precision}{fmt}} {units[order]}"


class TimingFormat(enum.Enum):
    IPYTHON = enum.auto()
    HYPERFINE = enum.auto()
    TIMEIT = enum.auto()


@dataclass(frozen=True)
class TimingInfo:
    times: tuple[float, ...]
    num_loops: int

    @cached_property
    def repeat(self) -> int:
        return len(self.times)

    @cached_property
    def mean(self) -> float:
        return statistics.mean(self.times)

    @cached_property
    def stdev(self) -> float:
        if self.repeat > 1:
            return statistics.stdev(self.times, xbar=self.mean)
        return float("nan")

    @cached_property
    def min(self) -> float:
        return min(self.times)

    @cached_property
    def max(self) -> float:
        return max(self.times)

    def pretty(self, fmt: TimingFormat) -> str:
        def label_count(num: int, item: str) -> str:
            return f"{num} {item}{'' if num == 1 else 's'}"

        loop_str = label_count(self.num_loops, "loop")
        if fmt is TimingFormat.HYPERFINE:
            order = _calc_order(self.max)
            prec = 3 if order == 0 else 1

            def time_str(timespan: float) -> str:
                return "{:>8s}".format(
                    format_time(timespan, precision=prec, fmt="f", order=order)
                )

            bg = "\033[1;32m"
            g = "\033[32m"
            c = "\033[36m"
            m = "\033[35m"
            r = "\033[0m"
            f = "\033[2m"
            if self.repeat == 1:
                return (
                    f"  Time ({bg}abs{r} ≡):     "
                    f"   {bg}{time_str(self.times[0])}{r}           "
                    f"    {f}{self.repeat} run, {loop_str} each{r}"
                )
            return (
                f"  Time ({bg}mean{r} ± {g}\u03c3{r}):  "
                f"   {bg}{time_str(self.mean)}{r} ± {g}{time_str(self.stdev)}{r}\n"
                f"  Range ({c}min{r} … {m}max{r}):"
                f"   {c}{time_str(self.min)}{r} … {m}{time_str(self.max)}{r}"
                f"    {f}{self.repeat} runs, {loop_str} each{r}"
            )
        if fmt is TimingFormat.IPYTHON:
            mean_order = _calc_order(self.mean)
            stdev_order = _calc_order(self.stdev) if self.repeat > 1 else mean_order
            return (
                f"{format_time(self.mean, order=mean_order)}"
                f" ± {format_time(self.stdev, order=stdev_order)} per loop"
                f" (mean ± std. dev. of {label_count(self.repeat, 'loop')},"
                f" {loop_str} each)"
            )
        if fmt is TimingFormat.TIMEIT:
            return (
                f"{loop_str}, best of {self.repeat}:"
                f" {format_time(self.min)} per loop"
            )
        raise AssertionError


def timeit(  # pylint: disable=too-many-arguments
    stmt: str | Callable[[], Any] = "pass",
    setup: str | Callable[[], Any] = "pass",
    repeat: int = 7,
    num_loops: int | None = None,
    timer: Callable[[], float] = default_timer,
    # pylint: disable-next=redefined-builtin
    globals: dict[str, Any] | None = None,  # noqa: A002
    fmt: TimingFormat | None = TimingFormat.HYPERFINE,
) -> TimingInfo:
    """IPython %timeit work-alike, with a similar interface to timeit.timeit().

    Prints a summary of the times if `fmt` is not None, and returns a
    TimingInfo object holding the full results.
    """
    timer_obj = Timer(stmt, setup, timer=timer, globals=globals)
    if num_loops is None:
        num_loops, total_time = timer_obj.autorange()
    else:
        # do a single run to get the first time
        total_time = timer_obj.timeit(number=num_loops)
    times = tuple(
        t / num_loops
        for t in [total_time, *timer_obj.repeat(repeat=repeat - 1, number=num_loops)]
    )
    info = TimingInfo(times, num_loops=num_loops)
    if fmt is not None:
        print(info.pretty(fmt))  # noqa: T201
    return info


class ContextTimer:
    """Time a code block in a with statement.

    >>> with ContextTimer() as t:
    ...     # code here
    >>> print(t.elapsed)
    # time in seconds

    If passed a string, a nicely formatted time will be printed after the block
    finishes:

    >>> with ContextTimer("frobnicate"):
    ...     frobnicate(foo, bar)
    frobnicate: 36.1 ms
    """

    def __init__(
        self, name: str | None = None, *, timer: Callable[[], float] = default_timer
    ):
        self.name = name
        self.start: float | None = None
        self.end: float | None = None
        self._timer = timer

    @property
    def elapsed(self) -> float:
        if self.start is None:
            msg = "elapsed time is not accessible before entering a with block"
            raise ValueError(msg)
        if self.end is None:
            # inside the with block, return the current elapsed time
            return self._timer() - self.start
        # outside the with block, return the total elapsed time
        return self.end - self.start

    @property
    def pretty_elapsed(self) -> str:
        warnings.warn(
            "ContextTimer.pretty_elapsed is deprecated, use str() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return str(self)

    def __str__(self) -> str:
        return format_time(self.elapsed)

    def __enter__(self):
        self.start = self._timer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = self._timer()
        if exc_type is None and self.name is not None:
            if self.name:
                # print here is intentional
                print(f"{self.name}: {self}")  # noqa: T201
            else:
                print(self)  # noqa: T201
        # propagate any exceptions
        return False
