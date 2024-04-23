# SPDX-FileCopyrightText: 2023-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import enum
import math
import statistics
from dataclasses import dataclass
from functools import cached_property
from timeit import Timer
from typing import Any, Callable

__all__ = ["TimingFormat", "TimingInfo", "timeit"]


def _calc_order(timespan: float) -> int:
    if timespan == 0:
        return 3
    return min(-int(math.floor(math.log10(timespan)) // 3), 3)


# modified from IPython/core/magics/execution.py
def _format_time(
    timespan: float,
    precision: int = 3,
    *,
    fmt: str = "g",
    order: int | None = None,
) -> str:
    """Formats the timespan in a human readable form"""

    if timespan >= 60.0:  # noqa: PLR2004
        # we have more than a minute, format that in a human readable form
        # Idea from http://snipplr.com/view/5713/
        parts = [("d", 60 * 60 * 24), ("h", 60 * 60), ("min", 60), ("s", 1)]
        time_str = []
        leftover = timespan
        for suffix, length in parts:
            value = int(leftover / length)
            if value > 0:
                leftover = leftover % length
                time_str.append(f"{value!s}{suffix}")
            if leftover < 1:
                break
        return " ".join(time_str)

    units = ["s", "ms", "μs", "ns"]
    scaling = [1, 1e3, 1e6, 1e9]

    if order is None:
        order = _calc_order(timespan)
    return f"{timespan * scaling[order]:.{precision}{fmt}} {units[order]}"


class TimingFormat(enum.Enum):
    IPYTHON = enum.auto()
    HYPERFINE = enum.auto()


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
    def min(self) -> float:  # noqa: A003
        return min(self.times)

    @cached_property
    def max(self) -> float:  # noqa: A003
        return max(self.times)

    def pretty(self, fmt: TimingFormat) -> str:
        if fmt is TimingFormat.HYPERFINE:
            order = _calc_order(self.max)
            prec = 3 if order == 0 else 1

            def time_str(timespan: float) -> str:
                return "{:>8s}".format(
                    _format_time(timespan, precision=prec, fmt="f", order=order)
                )

            bg = "\033[1;32m"
            g = "\033[32m"
            c = "\033[36m"
            m = "\033[35m"
            r = "\033[0m"
            f = "\033[2m"
            return (
                f"  Time ({bg}mean{r} ± {g}σ{r}):  "  # noqa: RUF001
                f"   {bg}{time_str(self.mean)}{r} ± {g}{time_str(self.stdev)}{r}\n"
                f"  Range ({c}min{r} … {m}max{r}):"
                f"   {c}{time_str(self.min)}{r} … {m}{time_str(self.max)}{r}"
                f"    {f}{self.repeat} runs, {self.num_loops} loops each{r}"
            )
        if fmt is TimingFormat.IPYTHON:
            return (
                f"{_format_time(self.mean)} ± {_format_time(self.stdev)} per loop"
                f" (mean ± std. dev. of {self.repeat} loops,"
                f" {self.num_loops} loops each)"
            )
        raise AssertionError


def timeit(  # pylint: disable=too-many-arguments
    stmt: str | Callable[[], Any] = "pass",
    setup: str | Callable[[], Any] = "pass",
    repeat: int = 7,
    num_loops: int | None = None,
    # pylint: disable-next=redefined-builtin
    globals: dict[str, Any] | None = None,  # noqa: A002
    fmt: TimingFormat = TimingFormat.HYPERFINE,
) -> TimingInfo:
    timer = Timer(stmt, setup, globals=globals)
    if num_loops is None:
        num_loops, total_time = timer.autorange()
    else:
        # do a single run to get the first time
        total_time = timer.timeit(number=num_loops)
    times = tuple(
        t / num_loops
        for t in [total_time, *timer.repeat(repeat=repeat - 1, number=num_loops)]
    )
    info = TimingInfo(times, num_loops=num_loops)
    print(info.pretty(fmt))  # noqa: T201
    return info
