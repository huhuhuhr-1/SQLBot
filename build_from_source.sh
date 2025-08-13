#!/usr/bin/env bash
set -euo pipefail

# Resolve project root
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Backend build
if command -v uv >/dev/null 2>&1; then
  echo "[1/5] Building backend wheel"
  cd backend
  uv sync
  uv build --wheel -o dist
  cd "$ROOT_DIR"
else
  echo "uv is not installed; skipping backend build" >&2
fi

# Frontend build
if command -v npm >/dev/null 2>&1; then
  echo "[2/5] Building frontend assets"
  cd frontend
  npm install
  npm run build
  cd "$ROOT_DIR"
else
  echo "npm is not installed; skipping frontend build" >&2
fi

# g2-ssr dependencies
if command -v npm >/dev/null 2>&1; then
  echo "[3/5] Installing g2-ssr dependencies"
  cd g2-ssr
  npm install
  cd "$ROOT_DIR"
fi

# Collect artifacts for packaging
echo "[4/5] Collecting build artifacts"
STAGE="package/opt/sqlbot"
rm -rf package
mkdir -p "$STAGE"/{backend,frontend,g2-ssr}
cp backend/dist/*.whl "$STAGE/backend/" 2>/dev/null || true
cp -r frontend/dist "$STAGE/frontend/" 2>/dev/null || true
cp -r g2-ssr "$STAGE/g2-ssr/"
cp start.sh "$STAGE"

# Build RPM if fpm is available
if command -v fpm >/dev/null 2>&1; then
  echo "[5/5] Building RPM via fpm"
  fpm -s dir -t rpm -n sqlbot -v 1.0.0 -C package opt/sqlbot
else
  echo "fpm not found; skipping RPM build" >&2
fi

# Build Docker image
if command -v docker >/dev/null 2>&1; then
  echo "Building Docker image sqlbot:latest"
  docker build -t sqlbot:latest .
else
  echo "docker not installed; skipping image build" >&2
fi

echo "Done"
