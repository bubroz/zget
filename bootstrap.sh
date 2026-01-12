#!/bin/bash

# Bootstrap script for zget
# This script sets up the development environment

set -e  # Exit on any error

echo "🚀 Setting up zget..."

# Check if uv is installed
if command -v uv &> /dev/null; then
    echo "✅ uv is already installed ($(uv --version))"
else
    echo "📦 uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the shell config to make uv available in this session
    # uv installs to ~/.local/bin by default
    export PATH="$HOME/.local/bin:$PATH"
    
    if command -v uv &> /dev/null; then
        echo "✅ uv installed successfully ($(uv --version))"
    else
        echo "❌ Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

echo ""
echo "🎉 Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  uv run zget-server --port 8000 --host 0.0.0.0"
