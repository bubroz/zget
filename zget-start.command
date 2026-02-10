#!/bin/bash

# Navigate to the project root (same directory as this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================================================"
echo "   🚀 Starting zget Archival Engine"
echo "================================================================"
echo "   📂 Location: $SCRIPT_DIR"
echo "   🔒 Mode:     Secure (Tailscale + Localhost only)"
echo "   🌍 URL:      http://localhost:9989"
echo "================================================================"
echo ""

# Check for uv (Python package manager)
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv (required for fast setup)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env"
fi

# Sync dependencies and run
echo "⚡️ Launching Server..."
echo "   (Keep this window open to keep zget running)"
echo ""

# Run with:
# --port 9989: User requested custom port
# --secure: Binds to 0.0.0.0 but restricts to Tailscale/Localhost IPs (Security)
# --open: Opens browser automatically
uv run zget-server --port 9989 --secure --open

# Prevent window from closing immediately if it crashes
echo ""
echo "❌ Server stopped. Press any key to exit..."
read -n 1
