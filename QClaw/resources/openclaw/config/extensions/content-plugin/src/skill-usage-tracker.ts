/**
 * Skill 使用记录追踪器
 *
 * 在 agent_end 钩子中检测到 Skill 被使用后，将使用记录写入 JSON 文件。
 * 文件路径: ~/.qclaw/skill-usage.json
 *
 * 数据格式:
 * {
 *   "records": [
 *     { "skillName": "browser-control", "usedAt": 1711459200000 },
 *     { "skillName": "multi-search-engine", "usedAt": 1711372800000 }
 *   ]
 * }
 *
 * 设计决策:
 * - 单写者（content-plugin agent_end 钩子）、多读者（UI 渲染进程）
 * - 写入频率极低（每次 agent 会话最多一次），无并发风险
 * - 记录保留最近 30 天，超期自动清理
 * - 每个 skill 只保留一条记录（upsert 语义）：已存在则更新 usedAt，否则新增
 * - 同一 skill 在同一次 agent 会话中只记录一次（去重）
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const LOG_TAG = "[skill-usage-tracker]";

/** 使用记录保留天数 */
const RETENTION_DAYS = 30;

/** JSON 文件名 */
const USAGE_FILE_NAME = "skill-usage.json";

/** ~/.qclaw 目录名 */
const QCLAW_DIR_NAME = ".qclaw";

/** 单条使用记录 */
export interface SkillUsageRecord {
  /** Skill 名称（来自 SKILL.md frontmatter 的 name 字段） */
  skillName: string;
  /** 使用时间戳（毫秒） */
  usedAt: number;
}

/** 文件存储结构 */
interface SkillUsageData {
  records: SkillUsageRecord[];
}

/**
 * 获取 skill-usage.json 的完整路径
 */
function getUsageFilePath(): string {
  return path.join(os.homedir(), QCLAW_DIR_NAME, USAGE_FILE_NAME);
}

/**
 * 读取现有的使用记录
 * 读取失败时返回空数组（容错）
 */
function readUsageData(): SkillUsageData {
  const filePath = getUsageFilePath();
  try {
    if (!fs.existsSync(filePath)) {
      return { records: [] };
    }
    const raw = fs.readFileSync(filePath, "utf-8");
    const data = JSON.parse(raw) as SkillUsageData;
    if (!Array.isArray(data.records)) {
      return { records: [] };
    }
    return data;
  } catch {
    // 文件损坏或格式异常，返回空数据（下次写入时会覆盖修复）
    return { records: [] };
  }
}

/**
 * 将使用记录写入文件
 * 包含过期清理逻辑
 */
function writeUsageData(data: SkillUsageData): void {
  const filePath = getUsageFilePath();
  try {
    // 确保目录存在
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    // 清理过期记录（超过 RETENTION_DAYS 天的）
    const cutoff = Date.now() - RETENTION_DAYS * 24 * 60 * 60 * 1000;
    data.records = data.records.filter((r) => r.usedAt >= cutoff);

    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), "utf-8");
  } catch (err) {
    // 写入失败不影响主流程，仅打印日志
    console.error(
      `${LOG_TAG} 写入 skill-usage.json 失败:`,
      err instanceof Error ? err.message : String(err),
    );
  }
}

/**
 * 记录一批 Skill 的使用
 *
 * 在 agent_end 钩子中检测到 detectedSkills 后调用。
 * 同一 skill 名称不会在同一次调用中重复写入。
 *
 * @param skillNames - 检测到的 skill 名称列表
 */
export function trackSkillUsage(skillNames: string[]): void {
  if (!skillNames.length) return;

  try {
    const data = readUsageData();
    const now = Date.now();

    // 去重：同一次 agent 会话中同名 skill 只记录一次
    const uniqueNames = [...new Set(skillNames)];

    for (const skillName of uniqueNames) {
      // 查找已有记录，更新 usedAt 而非新增，避免列表无限增长
      const existing = data.records.find((r) => r.skillName === skillName);
      if (existing) {
        existing.usedAt = now;
      } else {
        data.records.push({
          skillName,
          usedAt: now,
        });
      }
    }

    writeUsageData(data);
  } catch (err) {
    // 整体异常兜底，不影响 agent_end 主流程
    console.error(
      `${LOG_TAG} trackSkillUsage 异常:`,
      err instanceof Error ? err.message : String(err),
    );
  }
}
