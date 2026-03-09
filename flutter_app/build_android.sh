#!/bin/bash
# ==============================================================================
# DynaCalorie AI - Play Store Build Script
# ==============================================================================
# Since the Flutter SDK wasn't available in the current environment path, 
# please execute this script on a machine with Flutter installed to generate 
# the Android App Bundle for the Google Play Store.
# ==============================================================================

# 1. Regenerate Android platform files if missing
echo "Creating Android platform boundary..."
flutter create . --platforms android

# 2. Get dependencies
echo "Fetching pub packages..."
flutter pub get

# 3. Generate App Icons (from assets/icon/app_icon.png)
echo "Generating Launcher Icons..."
flutter pub run flutter_launcher_icons

# 4. Generate Native Splash Screen
echo "Generating Native Splash Screen..."
flutter pub run flutter_native_splash:create

# 5. Build Release App Bundle (.aab file for Play Store)
echo "Compiling Android App Bundle..."
flutter build appbundle --release

echo "=============================================================================="
echo "✅ Build Complete!"
echo "Your release bundle is located at: build/app/outputs/bundle/release/app-release.aab"
echo "You can upload this file directly to the Google Play Console."
echo "=============================================================================="
