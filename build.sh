#!/usr/bin/env bash
#
# Build the GHCC Library Management desktop app (.app) on macOS with PyInstaller.
#
# Usage (from the project root):
#     ./build.sh
#
# Force a specific interpreter:   PYTHON=python3.13 ./build.sh
#
# IMPORTANT (macOS): the app MUST be built with a Python whose Tk is >= 8.6.
# Apple's system Python (/usr/bin/python3) ships Tk 8.5, which renders a black/
# blank window on modern macOS. This script auto-selects a Tk 8.6 interpreter.
#
set -euo pipefail

APP_NAME="GHCC Library"
ENTRY="main.py"

cd "$(dirname "$0")"   # always run from the project root

# --- Pick a Python with a modern Tk (>= 8.6) --------------------------------
has_good_tk() {
    "$1" -c 'import sys, tkinter; sys.exit(0 if tkinter.TkVersion >= 8.6 else 1)' \
        >/dev/null 2>&1
}

PYTHON="${PYTHON:-}"
if [ -n "$PYTHON" ]; then
    if ! has_good_tk "$PYTHON"; then
        echo "ERROR: '$PYTHON' has Tk < 8.6 — the built app would show a black"
        echo "       window on macOS. Use a python.org / Homebrew / conda Python 3."
        exit 1
    fi
else
    for cand in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$cand" >/dev/null 2>&1 && has_good_tk "$cand"; then
            PYTHON="$cand"
            break
        fi
    done
    if [ -z "$PYTHON" ]; then
        echo "ERROR: No Python with Tk >= 8.6 found on PATH."
        echo "       macOS system Python uses Tk 8.5 (renders a blank window)."
        echo "       Install Python 3 from https://python.org (bundles Tk 8.6),"
        echo "       or use a conda/Homebrew Python, then re-run ./build.sh."
        exit 1
    fi
fi

TKVER="$("$PYTHON" -c 'import tkinter; print(tkinter.TkVersion)')"
echo "==> Using $("$PYTHON" --version) (Tk $TKVER) at $(command -v "$PYTHON")"

echo "==> Installing build dependencies (pyinstaller, openpyxl, Pillow)…"
"$PYTHON" -m pip install --upgrade pyinstaller openpyxl Pillow

echo "==> Cleaning previous build artifacts…"
rm -rf build dist "${APP_NAME}.spec"

echo "==> Building ${APP_NAME}.app…"
"$PYTHON" -m PyInstaller \
    --noconfirm \
    --windowed \
    --name "$APP_NAME" \
    --osx-bundle-identifier "com.ghcc.library" \
    --add-data "library_app/assets:library_app/assets" \
    "$ENTRY"

echo
echo "==> Done.  App bundle:  dist/${APP_NAME}.app"
echo "    Launch it with:     open \"dist/${APP_NAME}.app\""
