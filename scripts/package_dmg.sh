#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

# 1. Build app bundle first
./scripts/build_app.sh

echo "📦 Creating FreeFlow.dmg installer image..."

DMG_ROOT="dist/dmg_root"
rm -rf "$DMG_ROOT"
mkdir -p "$DMG_ROOT"

# Copy App into DMG root
cp -R "dist/FreeFlow.app" "$DMG_ROOT/"

# Symlink Applications folder
ln -s "/Applications" "$DMG_ROOT/Applications"

# Output DMG path
DMG_OUTPUT="dist/FreeFlow-v1.0.0-AppleSilicon.dmg"
rm -f "$DMG_OUTPUT"

# Create DMG with hdiutil
hdiutil create \
    -volname "FreeFlow" \
    -srcfolder "$DMG_ROOT" \
    -ov \
    -format UDZO \
    "$DMG_OUTPUT"

rm -rf "$DMG_ROOT"

echo "🎉 Successfully packaged: ${DMG_OUTPUT}"
ls -lh "$DMG_OUTPUT"
