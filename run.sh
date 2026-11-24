#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Ensure a WORKING venv exists. Checking only for the directory is not enough: a
# venv's python is a symlink to the interpreter it was built from, so after a
# Homebrew/uv Python upgrade the directory is still there but nothing in it runs.
if ! .venv/bin/python -c "" 2>/dev/null; then
    rm -rf .venv
    echo "⚡ Initializing FreeFlow virtual environment..."
    if command -v uv &> /dev/null; then
        uv venv .venv
        uv pip install -r requirements.txt
        uv pip install -e .
    else
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        pip install -e .
    fi
fi

# Ensure Swift HUD binary is compiled
if [ ! -f "hud/freeflow-hud" ]; then
    echo "🔨 Compiling native FreeFlow HUD overlay..."
    swiftc -O hud/freeflow_hud.swift -o hud/freeflow-hud
    chmod +x hud/freeflow-hud
fi

# Launch FreeFlow
echo "🎙️ Launching FreeFlow (On-Device Speech-to-Text)..."
exec .venv/bin/python -m freeflow.main "$@"
