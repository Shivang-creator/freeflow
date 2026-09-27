#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Ensure venv exists
if [ ! -d ".venv" ]; then
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
