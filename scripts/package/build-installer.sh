#!/usr/bin/env bash
# macOS：按 SKU 输出到 release/xcagi-v{version}/{personal|enterprise}/
set -euo pipefail

VERSION="${1:-8.0.0}"
SKU="${2:-}"
VERSION="${VERSION#v}"
VERSION="${VERSION#V}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

sku_label() {
  case "$1" in
    personal) echo Personal ;;
    enterprise) echo Enterprise ;;
    *) echo "Unknown SKU: $1" >&2; exit 1 ;;
  esac
}

sku_app_id() {
  case "$1" in
    personal) echo com.xcagi.desktop.personal ;;
    enterprise) echo com.xcagi.desktop.enterprise ;;
    *) echo "Unknown SKU: $1" >&2; exit 1 ;;
  esac
}

sku_update_url() {
  case "$1" in
    personal) echo https://update.xcagi.com/releases/stable/personal/ ;;
    enterprise) echo https://update.xcagi.com/releases/stable/enterprise/ ;;
    *) echo "Unknown SKU: $1" >&2; exit 1 ;;
  esac
}

build_one_sku() {
  local sku="$1"
  local label
  label="$(sku_label "$sku")"
  local out_dir="${ROOT}/release/xcagi-v${VERSION}/${sku}"
  mkdir -p "${out_dir}"

  echo "========== Building macOS SKU: ${sku} =========="
  if [ "${SKIP_BACKEND:-0}" != "1" ]; then
    XCAGI_PRODUCT_SKU="${sku}" scripts/package/build-backend.sh "${VERSION}"
  else
    python3 -m pip install "Pillow>=10.2.0" -q
  fi

  printf '{"sku":"%s","schema_version":1}\n' "${sku}" > desktop/resources/product-sku.json
  python3 scripts/package/generate-desktop-resources.py

  (cd desktop && [ -d node_modules ] || npm install)
  (cd desktop && npm version "${VERSION}" --no-git-tag-version)
  (cd desktop && npx electron-builder --mac dmg zip \
    "--config.directories.output=../release/xcagi-v${VERSION}/${sku}" \
    "--config.appId=$(sku_app_id "$sku")" \
    "--config.publish.url=$(sku_update_url "$sku")" \
    "--config.extraMetadata.productSku=${sku}")

  local artifact
  artifact="$(find "${out_dir}" -type f \( -name "*.dmg" -o -name "XCAGI-${label}-*.dmg" \) -print 2>/dev/null | sort | tail -n 1 || true)"
  if [ -n "${artifact}" ]; then
    node scripts/package/generate-update-metadata.mjs "${artifact}" "${VERSION}" mac
  fi
  echo "Done: ${out_dir}/"
}

if [ -z "${SKU}" ]; then
  echo "Usage: $0 <version> <personal|enterprise>"
  echo "   or: $0 <version> all"
  exit 1
fi

if [ "${SKU}" = "all" ]; then
  mkdir -p "${ROOT}/release/xcagi-v${VERSION}"/{personal,enterprise}
  for s in personal enterprise; do
    build_one_sku "${s}"
  done
  echo "Both macOS SKUs under release/xcagi-v${VERSION}/"
else
  case "${SKU}" in
    personal|enterprise) build_one_sku "${SKU}" ;;
    *) echo "Invalid SKU: ${SKU}" >&2; exit 1 ;;
  esac
fi
