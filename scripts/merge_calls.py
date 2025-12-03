#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAME_RE = re.compile(r"(?P<method>\S+) \((?P<file>[^<>:]+):(?P<line>\d+)\)")


def filter_trace(trace: list[str], source_path: Path) -> list[str]:
    it = iter(trace)
    try:
        while frame := next(it):
            if (m := FRAME_RE.match(frame)) is not None:
                file = Path(m["file"])
                assert file.is_absolute(), file  # noqa: S101
                if file.is_relative_to(source_path) and file.parts[-2] != "tests":
                    return [frame, *it]
    except StopIteration:
        pass
    return []


def main() -> None:
    in_file, out_file, *rest = sys.argv[1:]
    source_path = Path(rest[0]) if rest else Path()
    source_path = source_path.resolve()
    with open(in_file) as f, open(out_file, "w") as of:
        for line in f:
            trace, _, count = line.rpartition(" ")
            new_trace = filter_trace(trace.split(";"), source_path)
            if new_trace:
                of.write(";".join(new_trace) + " " + count)


if __name__ == "__main__":
    main()
