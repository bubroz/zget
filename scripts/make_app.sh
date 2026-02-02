#!/bin/bash

# Get project directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

APP_NAME="zget.app"
APP_DIR="$DIR/$APP_NAME"
ICON_SOURCE="$DIR/zget-icon.jpeg"

echo "🍎 Building $APP_NAME..."

# Cleaning up old build
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>zget</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.zget.launcher</string>
    <key>CFBundleName</key>
    <string>zget</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF

# Copy Main Script
cp "$DIR/zget-start.command" "$APP_DIR/Contents/MacOS/zget"
chmod +x "$APP_DIR/Contents/MacOS/zget"

# Generate ICNS
if [ -f "$ICON_SOURCE" ]; then
    echo "🎨 Generating AppIcon..."
    ICONSET="$DIR/zget.iconset"
    mkdir -p "$ICONSET"
    
    # Convert jpeg to png first
    sips -s format png "$ICON_SOURCE" --out "$DIR/temp_icon.png" --resampleHeightWidth 1024 1024 > /dev/null

    # Generate sizes
    sips -z 16 16     "$DIR/temp_icon.png" --out "$ICONSET/icon_16x16.png" > /dev/null
    sips -z 32 32     "$DIR/temp_icon.png" --out "$ICONSET/icon_16x16@2x.png" > /dev/null
    sips -z 32 32     "$DIR/temp_icon.png" --out "$ICONSET/icon_32x32.png" > /dev/null
    sips -z 64 64     "$DIR/temp_icon.png" --out "$ICONSET/icon_32x32@2x.png" > /dev/null
    sips -z 128 128   "$DIR/temp_icon.png" --out "$ICONSET/icon_128x128.png" > /dev/null
    sips -z 256 256   "$DIR/temp_icon.png" --out "$ICONSET/icon_128x128@2x.png" > /dev/null
    sips -z 512 512   "$DIR/temp_icon.png" --out "$ICONSET/icon_512x512.png" > /dev/null
    sips -z 1024 1024 "$DIR/temp_icon.png" --out "$ICONSET/icon_512x512@2x.png" > /dev/null

    # Create icns
    iconutil -c icns "$ICONSET" -o "$APP_DIR/Contents/Resources/AppIcon.icns"

    # Cleanup
    rm -rf "$ICONSET"
    rm "$DIR/temp_icon.png"
else
    echo "⚠️ Warning: $ICON_SOURCE not found, skipping icon generation."
fi

echo "✅ $APP_NAME created successfully!"
