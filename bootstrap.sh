#!/bin/bash
set -e

echo "Setting up zget..."

if command -v uv &> /dev/null; then
    echo "uv: $(uv --version)"
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv sync

echo ""
echo "Done. Examples:"
echo "  uv run zget <url>"
echo "  uv run zget info <url> --json"
echo "  uv run zget-mcp"
echo "  See docs/INTEGRATION.md"
