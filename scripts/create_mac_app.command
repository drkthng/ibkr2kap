#!/bin/bash
# MacOS One-Click App Generator for IBKR2KAP

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"
RUNNER_PATH="$DIR/ibkr2kap_runner.sh"
APP_NAME="IBKR2KAP"
DESKTOP_PATH="$HOME/Desktop/$APP_NAME.app"

echo "------------------------------------------------"
echo "  IBKR2KAP macOS One-Click App Generator"
echo "------------------------------------------------"

# Ensure runner is executable
chmod +x "$RUNNER_PATH"

echo "Creating launcher on Desktop..."

# Use osacompile to create an AppleScript application (.app)
# This app simply executes the runner script in the background
osacompile -e "do shell script \"bash '$RUNNER_PATH' > /dev/null 2>&1 &\"" -o "$DESKTOP_PATH"

if [ -d "$DESKTOP_PATH" ]; then
    echo "SUCCESS: $APP_NAME.app has been created on your Desktop."
    echo "You can now drag it to your Dock or just double-click to start."
else
    echo "ERROR: Failed to create app bundle."
fi

echo "------------------------------------------------"
read -p "Press enter to close this window..."
