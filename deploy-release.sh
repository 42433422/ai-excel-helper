#!/bin/bash
set -euo pipefail

# Deploy from prebuilt images without source code.
cd "$(dirname "$0")"

ARCHIVE="$(ls xcagi-images-*.tar 2>/dev/null | head -n 1 || true)"
if [[ -z "${ARCHIVE}" ]]; then
  echo "Could not find xcagi-images-*.tar in current directory."
  exit 1
fi

if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo "Created .env from .env.example. Please update SECRET_KEY."
  else
    echo "Missing .env and .env.example."
    exit 1
  fi
fi

if [[ -f ".release.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source .release.env
  set +a
fi

echo "[1/4] Loading images from ${ARCHIVE} ..."
docker load -i "${ARCHIVE}"

echo "[2/4] Stopping previous containers ..."
docker-compose down >/dev/null 2>&1 || true

echo "[3/4] Starting services ..."
docker-compose up -d

echo "[4/4] Current status ..."
docker-compose ps

echo
echo "Deployment complete."
echo "Frontend: http://localhost"
echo "Backend health: http://localhost:5000/health"
