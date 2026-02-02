#!/bin/bash

# Navigate to the project root (same directory as this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 Starting zget from $SCRIPT_DIR..."

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv (fast python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env"
fi

# Sync dependencies and run
echo "⚡️ Launching Server..."
uv run zget-server --open
