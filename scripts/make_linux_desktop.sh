#!/bin/bash

# Get project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
ICON_PATH="$PROJECT_DIR/zget-icon.jpeg"
EXEC_PATH="$PROJECT_DIR/bootstrap.sh" # Using bootstrap as entry point or direct uv call?
# Better to use a dedicated linux launch script similar to macOS command
LAUNCHER_PATH="$PROJECT_DIR/zget-start.sh"

# Create the linux launcher first
cat > "$LAUNCHER_PATH" <<EOF
#!/bin/bash
cd "$PROJECT_DIR"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "\$HOME/.cargo/env"
fi
uv run zget-server --open
EOF
chmod +x "$LAUNCHER_PATH"

# Create .desktop file content
DESKTOP_FILE="[Desktop Entry]
Name=zget
Comment=Personal Media Archival
Exec=$LAUNCHER_PATH
Icon=$ICON_PATH
Terminal=true
Type=Application
Categories=Utility;Network;
"

# Install to user applications directory
INSTALL_DIR="$HOME/.local/share/applications"
mkdir -p "$INSTALL_DIR"
echo "$DESKTOP_FILE" > "$INSTALL_DIR/zget.desktop"

echo "✅ Installed zget.desktop to $INSTALL_DIR"
echo "You can now find zget in your application menu."
