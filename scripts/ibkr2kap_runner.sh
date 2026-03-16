#!/bin/bash
# Runner script for IBKR2KAP macOS Launcher

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Check for .venv
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment (.venv) not found."
    echo "Please run the installation steps in README.md first."
    exit 1
fi

# Activate venv and run launcher
source .venv/bin/activate
python3 src/ibkr_tax/launcher.py
