#!/bin/bash
# SPDX-FileCopyrightText: 2025-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause
set -euo pipefail

ROOT="$(dirname -- "${BASH_SOURCE[0]}")"
: "${SOURCE_DIR:=$PWD}"

mkdir -p profiling/logs
timestamp=$(date -Is)
log_file="profiling/logs/python-$timestamp.txt"
log_file_func="profiling/logs/python-$timestamp-func.txt"

while ! [[ -e "$log_file" ]]; do
  py-spy record -s -n --full-filenames -f raw -o "$log_file" -- "$@" || true
done
while ! [[ -e "$log_file_func" ]]; do
  py-spy record -s -n -F --full-filenames -f raw -o "$log_file_func" -- "$@" || true
done

args=(--minwidth 0.1 --inverted --deterministic --fonttype monospace --width 2000)
for input in "$log_file" "$log_file_func"; do
  clean_input=${input%.txt}_clean.txt
  "$ROOT/merge_calls.py" "$input" "$clean_input" "$SOURCE_DIR"
  "$ROOT/make_flamegraphs.sh" "${args[@]}" "$input"
  "$ROOT/make_flamegraphs.sh" "${args[@]}" "$clean_input"
done
