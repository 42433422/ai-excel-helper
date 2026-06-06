/**
 * 全景「四工位横拼」：在 desk 逻辑画布上裁掉四周透明边，再边对边贴齐。
 * 画布宽高优先使用运行时读到的 `naturalWidth`/`naturalHeight`（见 useYuangongDeskIntrinsicSize），
 * 未加载前回退为下列默认值。更换素材后可微调 TRIM。
 *
 * 高度 100 与素材 desk.png（576×1024 portrait）目视比例更接近——之前 58 让条带过扁，
 * 在全景页表现为「上方/下方一大片黑底，工位挤在顶部」。当 desk.png 放大且超过
 * `COMPOSED_DESK_LAYOUT_MAX_DIM` 时，StitchStage 会回退到这里的 80×100 作为逻辑格。
 */
export const YUANGONG_CANVAS_W = 80
export const YUANGONG_CANVAS_H = 100

export const YUANGONG_COMPOSED_TRIM = {
  left: 6,
  right: 6,
  top: 0,
  bottom: 0,
} as const

/** 默认画布（未探测到实际尺寸时） */
export function yuangongComposedBaseSize(): { width: number; height: number } {
  return yuangongComposedBaseSizeFromCanvas(YUANGONG_CANVAS_W, YUANGONG_CANVAS_H)
}

/** 已知 desk 实际像素尺寸时的裁后可视区域 */
export function yuangongComposedBaseSizeFromCanvas(canvasW: number, canvasH: number): { width: number; height: number } {
  const t = YUANGONG_COMPOSED_TRIM
  return {
    width: Math.max(1, Math.round(canvasW) - t.left - t.right),
    height: Math.max(1, Math.round(canvasH) - t.top - t.bottom),
  }
}
