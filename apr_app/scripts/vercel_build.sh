#!/usr/bin/env bash
set -euo pipefail

FLUTTER_DIR="$PWD/.flutter"
FLUTTER_CHANNEL="${FLUTTER_CHANNEL:-stable}"

if [ ! -d "$FLUTTER_DIR" ]; then
  git clone --depth 1 -b "$FLUTTER_CHANNEL" https://github.com/flutter/flutter.git "$FLUTTER_DIR"
fi

export PATH="$FLUTTER_DIR/bin:$PATH"

flutter --version
flutter config --enable-web
flutter pub get

: "${API_BASE_URL:=/api}"
: "${BASE_HREF:=/}"
: "${PWA_STRATEGY:=none}"
: "${DEMO_EXTERNAL_URL:=}"
: "${CACHE_BUST_TOKEN:=${VERCEL_GIT_COMMIT_SHA:-}}"

# Vercel env values can carry CR/LF when added via stdin. Strip them to avoid
# breaking flutter build arguments.
API_BASE_URL="${API_BASE_URL//$'\r'/}"
API_BASE_URL="${API_BASE_URL//$'\n'/}"
BASE_HREF="${BASE_HREF//$'\r'/}"
BASE_HREF="${BASE_HREF//$'\n'/}"
PWA_STRATEGY="${PWA_STRATEGY//$'\r'/}"
PWA_STRATEGY="${PWA_STRATEGY//$'\n'/}"
DEMO_EXTERNAL_URL="${DEMO_EXTERNAL_URL//$'\r'/}"
DEMO_EXTERNAL_URL="${DEMO_EXTERNAL_URL//$'\n'/}"
CACHE_BUST_TOKEN="${CACHE_BUST_TOKEN//$'\r'/}"
CACHE_BUST_TOKEN="${CACHE_BUST_TOKEN//$'\n'/}"

if [ -z "${CACHE_BUST_TOKEN}" ]; then
  CACHE_BUST_TOKEN="$(date +%s)"
fi

BUILD_ARGS=(
  "--dart-define=API_BASE_URL=${API_BASE_URL}"
  "--base-href=${BASE_HREF}"
  "--pwa-strategy=${PWA_STRATEGY}"
)

if [ -n "${SUPABASE_URL:-}" ]; then
  BUILD_ARGS+=("--dart-define=SUPABASE_URL=${SUPABASE_URL}")
fi

if [ -n "${SUPABASE_ANON_KEY:-}" ]; then
  BUILD_ARGS+=("--dart-define=SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}")
fi

if [ -n "${DEMO_EXTERNAL_URL}" ]; then
  BUILD_ARGS+=("--dart-define=DEMO_EXTERNAL_URL=${DEMO_EXTERNAL_URL}")
fi

flutter build web --release "${BUILD_ARGS[@]}"

echo "Applying cache-bust token: ${CACHE_BUST_TOKEN}"

if [ -f "build/web/index.html" ]; then
  sed -i "s|flutter_bootstrap.js|flutter_bootstrap.js?v=${CACHE_BUST_TOKEN}|g" build/web/index.html
  sed -i "s|manifest.json|manifest.json?v=${CACHE_BUST_TOKEN}|g" build/web/index.html
  sed -i "s|favicon.png|favicon.png?v=${CACHE_BUST_TOKEN}|g" build/web/index.html
fi

if [ -f "build/web/flutter_bootstrap.js" ]; then
  sed -i "s|\"main.dart.js\"|\"main.dart.js?v=${CACHE_BUST_TOKEN}\"|g" build/web/flutter_bootstrap.js
fi
