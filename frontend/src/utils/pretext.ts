// @ts-nocheck
/**
 * Pretext.js 工具封装
 * 零 DOM 文本测量，比浏览器快 500 倍
 * 
 * API 文档: https://www.npmjs.com/package/@chenglou/pretext
 */

import { prepare, layout, prepareWithSegments, layoutWithLines, type LayoutResult, type LineResult } from '@chenglou/pretext';

// 测量结果接口
export interface MeasureResult {
  width: number;
  height: number;
  lines: string[];
  lineCount: number;
}

// 测量选项接口
export interface TextMeasureOptions {
  text: string;
  width: number;
  fontSize?: number;
  lineHeight?: number;
  fontFamily?: string;
  fontWeight?: string;
  letterSpacing?: number;
  whiteSpace?: 'normal' | 'pre-wrap';
  wordBreak?: 'normal' | 'keep-all';
}

// 缓存机制
const prepareCache = new Map<string, ReturnType<typeof prepare>>();
const CACHE_MAX_SIZE = 500;

/**
 * 生成缓存键
 */
function generateCacheKey(text: string, options: Omit<TextMeasureOptions, 'text' | 'width'>): string {
  return `${text}_${JSON.stringify(options)}`;
}

/**
 * 清理缓存（LRU 策略）
 */
function cleanupCache(): void {
  if (prepareCache.size > CACHE_MAX_SIZE) {
    const entriesToDelete = prepareCache.size - CACHE_MAX_SIZE;
    const keys = prepareCache.keys();
    for (let i = 0; i < entriesToDelete; i++) {
      const key = keys.next().value;
      if (key) {
        prepareCache.delete(key);
      }
    }
  }
}

/**
 * 获取字体字符串
 */
function getFontString(options: TextMeasureOptions): string {
  const weight = options.fontWeight || '400';
  const size = options.fontSize || 14;
  const family = options.fontFamily || 'system-ui, -apple-system, sans-serif';
  return `${weight} ${size}px ${family}`;
}

/**
 * 测量文本尺寸
 * @param options 测量选项
 * @returns 测量结果
 */
export function measureText(options: TextMeasureOptions): MeasureResult {
  const cacheKey = generateCacheKey(options.text, {
    fontSize: options.fontSize,
    fontFamily: options.fontFamily,
    fontWeight: options.fontWeight,
    letterSpacing: options.letterSpacing,
    whiteSpace: options.whiteSpace,
    wordBreak: options.wordBreak,
  });
  
  // 检查缓存
  let prepared = prepareCache.get(cacheKey);
  
  if (!prepared) {
    // 执行 prepare（一次性字体分析）
    const font = getFontString(options);
    prepared = prepare(options.text, font, {
      whiteSpace: options.whiteSpace || 'normal',
      wordBreak: options.wordBreak,
      letterSpacing: options.letterSpacing,
    });
    
    // 存入缓存
    prepareCache.set(cacheKey, prepared);
    cleanupCache();
  }
  
  // 执行 layout（纯算术计算）
  const lineHeight = options.lineHeight || 1.5;
  const fontSize = options.fontSize || 14;
  const result: LayoutResult = layout(prepared, options.width, fontSize * lineHeight);
  
  return {
    width: result.width,
    height: result.height,
    lines: [], // layout 不返回具体行内容，需要 layoutWithLines
    lineCount: result.lineCount,
  };
}

/**
 * 测量并获取行内容
 * @param options 测量选项
 * @returns 包含行内容的测量结果
 */
export function measureTextWithLines(options: TextMeasureOptions): MeasureResult & { lines: string[] } {
  const font = getFontString(options);
  const prepared = prepareWithSegments(options.text, font, {
    whiteSpace: options.whiteSpace || 'normal',
    wordBreak: options.wordBreak,
    letterSpacing: options.letterSpacing,
  });
  
  const lineHeight = options.lineHeight || 1.5;
  const fontSize = options.fontSize || 14;
  const result = layoutWithLines(prepared, options.width, fontSize * lineHeight);
  
  return {
    width: result.width,
    height: result.height,
    lines: result.lines.map((line: LineResult) => line.text),
    lineCount: result.lines.length,
  };
}

/**
 * 批量测量文本
 * @param items 测量选项数组
 * @returns 测量结果数组
 */
export function batchMeasure(items: TextMeasureOptions[]): MeasureResult[] {
  return items.map(item => measureText(item));
}

/**
 * 清空测量缓存
 */
export function clearMeasureCache(): void {
  prepareCache.clear();
}

/**
 * 获取缓存状态
 */
export function getCacheStats(): {
  size: number;
  maxSize: number;
} {
  return {
    size: prepareCache.size,
    maxSize: CACHE_MAX_SIZE,
  };
}

/**
 * 估算消息高度（用于 AI 对话）
 * @param content 消息内容
 * @param maxWidth 最大宽度
 * @param fontSize 字体大小
 * @returns 预估高度
 */
export function estimateMessageHeight(
  content: string,
  maxWidth: number,
  fontSize: number = 14
): number {
  // 去除 HTML 标签
  const plainText = content.replace(/<[^>]*>/g, '');
  
  const result = measureText({
    text: plainText,
    width: maxWidth,
    fontSize,
    lineHeight: 1.5,
    whiteSpace: 'pre-wrap',
  });
  
  return result.height;
}

/**
 * 批量估算消息高度
 * @param messages 消息数组
 * @param maxWidth 最大宽度
 * @returns 高度数组
 */
export function batchEstimateMessageHeights(
  messages: { content: string; fontSize?: number }[],
  maxWidth: number
): number[] {
  return messages.map(msg => 
    estimateMessageHeight(msg.content, maxWidth, msg.fontSize || 14)
  );
}

/**
 * 计算表格行高
 * @param cellContents 单元格内容数组
 * @param columnWidth 列宽
 * @param fontSize 字体大小
 * @returns 行高数组
 */
export function calculateTableRowHeights(
  cellContents: string[],
  columnWidth: number,
  fontSize: number = 12
): number[] {
  return cellContents.map(content => {
    const result = measureText({
      text: content,
      width: columnWidth,
      fontSize,
      lineHeight: 1.4,
      fontFamily: 'monospace',
      whiteSpace: 'pre-wrap',
    });
    return result.height + 16; // 加上 padding
  });
}

/**
 * 计算标签布局
 * @param text 标签文本
 * @param labelWidth 标签宽度
 * @param labelHeight 标签高度
 * @returns 布局信息
 */
export function calculateLabelLayout(
  text: string,
  labelWidth: number,
  labelHeight: number
): {
  fontSize: number;
  lines: string[];
  lineHeight: number;
} {
  // 尝试不同字体大小，找到最适合的
  const fontSizes = [16, 14, 12, 10, 8];
  
  for (const fontSize of fontSizes) {
    const result = measureTextWithLines({
      text,
      width: labelWidth - 8, // 减去边距
      fontSize,
      lineHeight: 1.2,
      whiteSpace: 'normal',
    });
    
    if (result.height <= labelHeight - 8) {
      return {
        fontSize,
        lines: result.lines,
        lineHeight: fontSize * 1.2,
      };
    }
  }
  
  // 如果都放不下，使用最小字体并截断
  const result = measureTextWithLines({
    text,
    width: labelWidth - 8,
    fontSize: 8,
    lineHeight: 1.2,
    whiteSpace: 'normal',
  });
  
  const maxLines = Math.floor((labelHeight - 8) / (8 * 1.2));
  return {
    fontSize: 8,
    lines: result.lines.slice(0, maxLines),
    lineHeight: 8 * 1.2,
  };
}

// 性能监控
let totalMeasurements = 0;
let cachedMeasurements = 0;

/**
 * 获取性能统计
 */
export function getPerformanceStats(): {
  totalMeasurements: number;
  cachedMeasurements: number;
  cacheHitRate: number;
} {
  return {
    totalMeasurements,
    cachedMeasurements,
    cacheHitRate: totalMeasurements > 0 
      ? cachedMeasurements / totalMeasurements 
      : 0,
  };
}

// 包装原始 measure 函数以统计性能
const originalMeasure = measureText;
export function measureTextWithStats(options: TextMeasureOptions): MeasureResult {
  totalMeasurements++;
  const cacheKey = generateCacheKey(options.text, {
    fontSize: options.fontSize,
    fontFamily: options.fontFamily,
    fontWeight: options.fontWeight,
  });
  if (prepareCache.has(cacheKey)) {
    cachedMeasurements++;
  }
  return originalMeasure(options);
}
