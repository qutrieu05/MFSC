#!/usr/bin/env bash
# Build and run core_logic host unit tests with the MSYS2 UCRT64 gcc found on this machine
# (not on PATH by default -- see PROJECT_STATUS.md P1.5 section for how this was discovered).
# Usage: bash firmware/cell_controller/test_host/build_and_run.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
CORE="$ROOT/components/core_logic"
HAL="$ROOT/components/hal"
GCC_DIR="/c/msys64/ucrt64/bin"

if [ ! -x "$GCC_DIR/gcc.exe" ]; then
    echo "gcc not found at $GCC_DIR -- see docs prerequisite notes." >&2
    exit 2
fi
export PATH="$GCC_DIR:$PATH"

CFLAGS="-std=c99 -Wall -Wextra -Werror -I$CORE -I$HAL"
CORE_SRCS="$CORE/cell_sm.c $CORE/fault_manager.c $CORE/debounce.c $CORE/safety_supervisor.c $CORE/cmd_handler.c $CORE/logger.c $CORE/watchdog.c $CORE/safety_interlock.c $HAL/hal_host_mock.c"

total_run=0
total_failed=0
any_build_failed=0

for t in "$HERE"/test_*.c; do
    name="$(basename "$t" .c)"
    exe="$HERE/${name}.exe"
    if ! gcc.exe $CFLAGS "$t" $CORE_SRCS -o "$exe" 2>"$HERE/${name}.build.log"; then
        echo "BUILD FAILED: $name (see ${name}.build.log)"
        any_build_failed=1
        continue
    fi
    echo "--- $name ---"
    out="$("$exe")" || true
    echo "$out"
    line="$(echo "$out" | grep '^SUMMARY:' || true)"
    run="$(echo "$line" | sed -E 's/SUMMARY: ([0-9]+) run, ([0-9]+) failed.*/\1/')"
    failed="$(echo "$line" | sed -E 's/SUMMARY: ([0-9]+) run, ([0-9]+) failed.*/\2/')"
    total_run=$((total_run + run))
    total_failed=$((total_failed + failed))
done

echo "==================================================="
echo "TOTAL: $total_run checks run, $total_failed failed"
if [ "$any_build_failed" -ne 0 ] || [ "$total_failed" -ne 0 ]; then
    exit 1
fi
exit 0
