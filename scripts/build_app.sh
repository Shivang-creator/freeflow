#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "🔨 Building FreeFlow.app macOS Application Bundle..."

APP_NAME="FreeFlow"
APP_BUNDLE="dist/${APP_NAME}.app"
CONTENTS="${APP_BUNDLE}/Contents"
MACOS="${CONTENTS}/MacOS"
RESOURCES="${CONTENTS}/Resources"

# Clean prior build
rm -rf "dist"
mkdir -p "${MACOS}" "${RESOURCES}"

# Copy App Icon
if [ -f "assets/AppIcon.icns" ]; then
    cp "assets/AppIcon.icns" "${RESOURCES}/AppIcon.icns"
fi
if [ -f "assets/icon.png" ]; then
    cp "assets/icon.png" "${RESOURCES}/icon.png"
fi

# Create Info.plist
cat <<EOF > "${CONTENTS}/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>FreeFlow</string>
    <key>CFBundleDisplayName</key>
    <string>FreeFlow</string>
    <key>CFBundleIdentifier</key>
    <string>com.freeflow.dictation</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>FreeFlow</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>FreeFlow needs access to your microphone to transcribe speech 100% on-device.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>FreeFlow needs accessibility access to paste transcribed text into your focused applications.</string>
</dict>
</plist>
EOF

# Copy repository source code and assets into Resources/app
mkdir -p "${RESOURCES}/app"
cp -r pyproject.toml requirements.txt README.md run.sh "${RESOURCES}/app/"
cp -r freeflow "${RESOURCES}/app/"
cp -r hud "${RESOURCES}/app/"

# Ensure HUD binary is compiled
if [ ! -f "${RESOURCES}/app/hud/freeflow-hud" ]; then
    echo "⚡ Compiling native Swift HUD binary..."
    swiftc -O "${RESOURCES}/app/hud/freeflow_hud.swift" -o "${RESOURCES}/app/hud/freeflow-hud"
    chmod +x "${RESOURCES}/app/hud/freeflow-hud"
fi

# Create launcher executable in Contents/MacOS/FreeFlow
cat <<'EOF' > "${MACOS}/FreeFlow"
#!/bin/bash
set -e

# Resolve paths
MACOS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$( cd "${MACOS_DIR}/../Resources/app" && pwd )"
cd "$APP_DIR"

# Send boot notification
osascript -e 'display notification "Starting FreeFlow 100% On-Device Voice Dictation..." with title "FreeFlow"' 2>/dev/null || true

# Determine Python runtime
PYTHON_BIN=""
if [ -d "$APP_DIR/.venv" ] && [ -x "$APP_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$APP_DIR/.venv/bin/python"
elif [ -d "$HOME/.freeflow/venv" ] && [ -x "$HOME/.freeflow/venv/bin/python" ]; then
    PYTHON_BIN="$HOME/.freeflow/venv/bin/python"
fi

# Automated 1-Click Bootstrap if venv not present
if [ -z "$PYTHON_BIN" ]; then
    osascript -e 'display notification "First-time setup: Preparing local MLX environment..." with title "FreeFlow"' 2>/dev/null || true
    TARGET_VENV="$HOME/.freeflow/venv"
    mkdir -p "$HOME/.freeflow"
    
    if command -v uv &> /dev/null; then
        uv venv "$TARGET_VENV"
        uv pip install --python "$TARGET_VENV/bin/python" -r requirements.txt
        uv pip install --python "$TARGET_VENV/bin/python" -e .
    else
        python3 -m venv "$TARGET_VENV"
        "$TARGET_VENV/bin/pip" install --upgrade pip
        "$TARGET_VENV/bin/pip" install -r requirements.txt
        "$TARGET_VENV/bin/pip" install -e .
    fi
    PYTHON_BIN="$TARGET_VENV/bin/python"
fi

# Ensure Swift HUD binary is compiled
if [ ! -f "$APP_DIR/hud/freeflow-hud" ]; then
    swiftc -O "$APP_DIR/hud/freeflow_hud.swift" -o "$APP_DIR/hud/freeflow-hud"
    chmod +x "$APP_DIR/hud/freeflow-hud"
fi

# Launch FreeFlow Menu Bar App
exec "$PYTHON_BIN" -m freeflow.main --app
EOF

chmod +x "${MACOS}/FreeFlow"

echo "✅ Successfully built ${APP_BUNDLE}!"
