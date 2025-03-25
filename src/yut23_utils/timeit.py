# SPDX-FileCopyrightText: 2023-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause
"""Work-alike for `python -m timeit` with my custom formatting."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING

from yut23_utils import timing

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Callable


def main(
    arguments: Sequence[str] | None = None,
    *,
    _wrap_timer: Callable[[Callable[[], float]], Callable[[], float]] | None = None,
) -> int | None:
    parser = argparse.ArgumentParser(
        epilog="""
A multi-line statement may be given by specifying each line as a
separate argument; indented lines are possible by enclosing an
argument in quotes and using leading spaces.  Multiple -s options are
treated similarly.
"""
    )
    parser.add_argument(
        "-n",
        "--number",
        metavar="N",
        type=int,
        default=None,
        help="how many times to execute 'statement'",
    )
    parser.add_argument(
        "-r",
        "--repeat",
        metavar="N",
        type=int,
        default=7,
        help="how many times to repeat the timer (default 7)",
    )
    parser.add_argument(
        "-s",
        "--setup",
        metavar="S",
        action="append",
        help="statement to be executed once initially (default 'pass')",
    )
    parser.add_argument(
        "-f",
        "--format",
        metavar="FMT",
        choices=["ipython", "hyperfine", "timeit"],
        default="hyperfine",
        help="how to style the timing output (hyperfine, ipython, or timeit)",
    )
    parser.add_argument(
        "--show-output",
        action="store_true",
        help="print the stdout and stderr of the statement instead of suppressing it",
    )
    parser.add_argument(
        "statement", action="append", help="statement to be timed (default 'pass')"
    )
    args = parser.parse_args(arguments)

    timer = timing.default_timer
    stmt = "\n".join(args.statement) or "pass"
    setup = "\n".join(args.setup) or "pass"
    fmt = getattr(timing.TimingFormat, args.format.upper())

    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)

    sys.path.insert(0, os.curdir)
    if _wrap_timer is not None:
        timer = _wrap_timer(timer)

    # from https://stackoverflow.com/a/52442331
    @contextmanager
    def suppress_stdout_stderr():
        """A context manager that redirects stdout and stderr to devnull"""
        if not args.show_output:
            with (
                open(os.devnull, "w") as fnull,
                redirect_stderr(fnull) as err,
                redirect_stdout(fnull) as out,
            ):
                yield (err, out)
        else:
            yield ()

    t = timing.Timer(stmt, setup, timer)
    try:
        with suppress_stdout_stderr():
            # pylint: disable-next=protected-access
            info = timing._timeit_helper(  # noqa: SLF001
                timer_obj=t, repeat=args.repeat, num_loops=args.number
            )
    except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        t.print_exc()
        return 1

    print(info.pretty(fmt))  # noqa: T201
    return None


if __name__ == "__main__":
    sys.exit(main())
