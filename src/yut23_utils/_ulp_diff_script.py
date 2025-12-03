# SPDX-FileCopyrightText: 2025-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause
"""Command-line script for getting the ULP difference between two numbers."""
# ruff: noqa: T201

import argparse

from yut23_utils.fp import Precision, ulp_diff


def float_literal(s: str) -> float:
    if s.startswith("0x") and "p" in s:
        return float.fromhex(s)
    return float(s)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-f", "--float", action="store_true")
    args, rest = parser.parse_known_args()
    if not rest:
        # try reading from stdin
        rest.append(input())
        rest.append(input())
    a = float_literal(rest[0])
    b = float_literal(rest[1])

    prec = Precision.BINARY64
    if args.float:
        prec = Precision.BINARY32
    ulps = ulp_diff(a, b, prec)
    if args.quiet:
        print(ulps)
    else:
        print(f"a: {a!s:22s} ({a.hex()})")
        print(f"b: {b!s:22s} ({b.hex()})")
        print(f"{ulps} ULP{'' if ulps == 1 else 's'}", end="")
        if ulps > 0:
            print(f" (~{abs(a - b) / abs(a):.3g}×a)")  # noqa: RUF001
        else:
            print()
