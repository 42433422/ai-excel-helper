#!/usr/bin/env python3
"""Generate Android launcher mipmaps from desktop brand icon (same as Windows)."""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BRAND_SOURCE = ROOT / "desktop" / "branding" / "app-icon-source.png"
BRAND_FALLBACK = ROOT / "desktop" / "resources" / "icon.png"
RES_MAIN = ROOT / "mobile-android" / "app" / "src" / "main" / "res"
SKU_TARGETS = (
    ("personal", (255, 255, 255, 255)),
    ("enterprise", (232, 238, 245, 255)),
)

# Launcher icon size per density (px)
LAUNCHER_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
# Adaptive foreground layer (108dp base)
FOREGROUND_SIZES = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}


def _is_background_pixel(r: int, g: int, b: int, a: int, threshold: int) -> bool:
    if a < 8:
        return True
    return r >= threshold and g >= threshold and b >= threshold


def _white_flood_to_transparent(im: Image.Image, threshold: int = 242) -> Image.Image:
    """Remove outer white matte via flood-fill from image edges (keeps logo colors)."""
    rgba = im.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    visited = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def try_push(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= w or y >= h or visited[x][y]:
            return
        r, g, b, a = px[x, y]
        if not _is_background_pixel(r, g, b, a, threshold):
            return
        visited[x][y] = True
        q.append((x, y))

    for x in range(w):
        try_push(x, 0)
        try_push(x, h - 1)
    for y in range(h):
        try_push(0, y)
        try_push(w - 1, y)

    while q:
        x, y = q.popleft()
        r, g, b, _a = px[x, y]
        px[x, y] = (r, g, b, 0)
        try_push(x - 1, y)
        try_push(x + 1, y)
        try_push(x, y - 1)
        try_push(x, y + 1)

    return rgba


def _load_master() -> Image.Image:
    src = BRAND_SOURCE if BRAND_SOURCE.is_file() else BRAND_FALLBACK
    if not src.is_file():
        raise SystemExit(f"Brand icon not found: {BRAND_SOURCE} or {BRAND_FALLBACK}")
    im = Image.open(src).convert("RGBA")
    return _white_flood_to_transparent(im)


def _square_canvas(
    im: Image.Image,
    size: int,
    inset_ratio: float = 0.0,
    background: tuple[int, int, int, int] = (255, 255, 255, 255),
) -> Image.Image:
    """Scale to fit square; inset_ratio shrinks logo for adaptive safe zone."""
    im = im.convert("RGBA")
    w, h = im.size
    inner = int(size * (1.0 - inset_ratio * 2))
    inner = max(inner, 1)
    scale = min(inner / w, inner / h)
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), background)
    canvas.paste(resized, ((size - nw) // 2, (size - nh) // 2), resized)
    return canvas


def _write_sku_icons(res_root: Path, launcher_bg: tuple[int, int, int, int]) -> None:
    master = _load_master()
    for folder, px in LAUNCHER_SIZES.items():
        out_dir = res_root / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        icon = _square_canvas(master, px, inset_ratio=0.06, background=launcher_bg)
        icon.save(out_dir / "ic_launcher.png", format="PNG")
        icon.save(out_dir / "ic_launcher_round.png", format="PNG")

    for folder, px in FOREGROUND_SIZES.items():
        out_dir = res_root / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        fg = _square_canvas(master, px, inset_ratio=0.12)
        fg.save(out_dir / "ic_launcher_foreground.png", format="PNG")


def main() -> int:
    android_app = ROOT / "mobile-android" / "app" / "src"
    for sku, bg in SKU_TARGETS:
        res = android_app / sku / "res"
        _write_sku_icons(res, bg)

    # Shared splash drawable for main theme
    drawable_dir = RES_MAIN / "drawable"
    drawable_dir.mkdir(parents=True, exist_ok=True)
    splash = _square_canvas(_load_master(), 288, inset_ratio=0.08)
    splash.save(drawable_dir / "ic_launcher_foreground.png", format="PNG")

    old_vec = RES_MAIN / "drawable" / "ic_launcher_foreground.xml"
    if old_vec.is_file():
        old_vec.unlink()

    src = BRAND_SOURCE if BRAND_SOURCE.is_file() else BRAND_FALLBACK
    print(f"[generate-android-icons] OK personal + enterprise from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
