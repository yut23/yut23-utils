#!/bin/bash
# SPDX-FileCopyrightText: 2025-present Eric T. Johnson
#
# SPDX-License-Identifier: BSD-3-Clause
set -euo pipefail

args=()
for arg; do
  if [[ "$arg" == '--help' ]]; then
    inferno-flamegraph --help
    exit
  fi
  args+=("$arg")
done

input="${args[-1]}"
output=${input%.txt}.svg
output=${output/logs\//}
reverse_output=${input%.txt}_reverse.svg
reverse_output=${reverse_output/logs\//}
unset "args[-1]"

if ! [[ -e "$input" ]]; then
  echo "Error: input file doesn't exist"
  exit 1
fi

if (( ${#args[@]} == 0 )); then
  # default args
  args=(--minwidth 0.1 --inverted --deterministic)
fi

# flip --inverted for the reverse flamegraphs
is_inverted=n
reverse_args=(--reverse)
for arg in "${args[@]}"; do
  if [[ $arg == --inverted ]]; then
    is_inverted=y
  else
    reverse_args+=("$arg")
  fi
done
if [[ $is_inverted == n ]]; then
  reverse_args+=(--inverted)
fi

inferno-flamegraph "${args[@]}" "$input" > "$output"
inferno-flamegraph "${reverse_args[@]}" "$input" > "$reverse_output"
