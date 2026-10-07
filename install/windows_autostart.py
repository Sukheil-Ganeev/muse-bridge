#!/usr/bin/env python3
"""Render a UTF-8 Windows startup batch file for the bridge."""

import sys


def render_autostart(bridge_path):
    # Batch files expand %NAME% when they run; double percent signs so a
    # literal percent sequence in the installed path survives that pass.
    batch_path = bridge_path.replace("%", "%%")
    return (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "setlocal DisableDelayedExpansion\r\n"
        f'start "" /min pythonw "{batch_path}"\r\n'
    )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Usage: windows_autostart.py BRIDGE_PATH", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(render_autostart(argv[0]).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
