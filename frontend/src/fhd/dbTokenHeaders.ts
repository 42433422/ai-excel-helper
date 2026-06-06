/** 与 FHD 后端 X-FHD-Db-Read-Token 对齐；供 apiFetch / fetch 补丁 / 一级锁 UI 使用。 */
import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from '@/utils/xcagiStorageKeys';

export const LS_DB_READ_TOKEN = 'xcagi_db_read_token';
export const LS_DB_WRITE_TOKEN = 'xcagi_db_write_token';
export const LS_DB_TOKENS_BY_MOD = 'xcagi_db_tokens_by_mod';

/** 任意代码写入「按 Mod 存储的 DB 令牌」后派发；设置页等可据此刷新输入框。 */
export const FHD_STORED_DB_TOKENS_CHANGED_EVENT = 'fhd:stored-db-tokens-changed';

export const FHD_DB_READ_UNLOCKED_EVENT = 'fhd-db-read-unlocked';

/** 侧栏每次点击「产品管理」时派发；产品页据此再次要求输入一级口令。 */
export const XCAGI_PRODUCTS_SIDEBAR_ACTIVATED = 'xcagi:products-sidebar-activated';

/** 一级读口令验证成功后 5 分钟内免再次输入（本标签页 sessionStorage）；产品管理入口闸与全局弹窗共用。 */
const SS_PRODUCTS_READ_GATE_GRACE_UNTIL = 'xcagi_products_read_gate_grace_until_ms';
const PRODUCTS_READ_GATE_GRACE_MS = 5 * 60 * 1000;

export function isProductsReadGateGraceActive(): boolean {
  if (typeof sessionStorage === 'undefined') return false;
  try {
    const raw = sessionStorage.getItem(SS_PRODUCTS_READ_GATE_GRACE_UNTIL);
    if (!raw) return false;
    const until = parseInt(raw, 10);
    return Number.isFinite(until) && Date.now() < until;
  } catch {
    return false;
  }
}

/** 自当前时刻起再保留 5 分钟免输产品页一级口令（滑动续期）。 */
export function touchProductsReadGateGrace(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(SS_PRODUCTS_READ_GATE_GRACE_UNTIL, String(Date.now() + PRODUCTS_READ_GATE_GRACE_MS));
}

export type DbTokensStatus = {
  read_token_configured: boolean;
  write_token_configured: boolean;
  active_mod_id?: string;
};

export async function fetchDbTokensStatus(apiBase = ''): Promise<DbTokensStatus> {
  const r = await fetch(`${apiBase}/api/fhd/db-tokens/status`);
  if (!r.ok) throw new Error(`db-tokens/status ${r.status}`);
  return r.json();
}

function readActiveModId(): string {
  if (typeof localStorage === 'undefined') return '';
  try {
    return String(localStorage.getItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY) || '').trim();
  } catch {
    return '';
  }
}

function readTokensByModMap(): Record<string, { read?: string; write?: string }> {
  if (typeof localStorage === 'undefined') return {};
  try {
    const raw = String(localStorage.getItem(LS_DB_TOKENS_BY_MOD) || '').trim();
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};
    const out: Record<string, { read?: string; write?: string }> = {};
    for (const [modId, row] of Object.entries(parsed as Record<string, unknown>)) {
      const key = String(modId || '').trim();
      if (!key || !row || typeof row !== 'object' || Array.isArray(row)) continue;
      const read = String((row as Record<string, unknown>).read || '').trim();
      const write = String((row as Record<string, unknown>).write || '').trim();
      if (!read && !write) continue;
      out[key] = {};
      if (read) out[key].read = read;
      if (write) out[key].write = write;
    }
    return out;
  } catch {
    return {};
  }
}

function writeTokensByModMap(next: Record<string, { read?: string; write?: string }>): void {
  if (typeof localStorage === 'undefined') return;
  const keys = Object.keys(next);
  if (!keys.length) {
    localStorage.removeItem(LS_DB_TOKENS_BY_MOD);
    return;
  }
  localStorage.setItem(LS_DB_TOKENS_BY_MOD, JSON.stringify(next));
}

export function readStoredDbTokensForMod(modId: string): { read: string; write: string } {
  const id = String(modId || '').trim();
  if (!id) return { read: '', write: '' };
  const map = readTokensByModMap();
  const row = map[id] || {};
  return {
    read: String(row.read || '').trim(),
    write: String(row.write || '').trim(),
  };
}

export function saveStoredDbTokensForMod(modId: string, read: string, write: string): void {
  const id = String(modId || '').trim();
  if (!id || typeof localStorage === 'undefined') return;
  const map = readTokensByModMap();
  const rt = String(read || '').trim();
  const wt = String(write || '').trim();
  if (!rt && !wt) {
    delete map[id];
    writeTokensByModMap(map);
  } else {
    map[id] = {};
    if (rt) map[id].read = rt;
    if (wt) map[id].write = wt;
    writeTokensByModMap(map);
  }
  try {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(FHD_STORED_DB_TOKENS_CHANGED_EVENT, { detail: { modId: id } }));
    }
  } catch {
    /* ignore */
  }
}

export function readStoredDbTokens(): { read: string; write: string } {
  if (typeof localStorage === 'undefined') return { read: '', write: '' };
  const globalTokens = {
    read: (localStorage.getItem(LS_DB_READ_TOKEN) || '').trim(),
    write: (localStorage.getItem(LS_DB_WRITE_TOKEN) || '').trim(),
  };
  const activeModId = readActiveModId();
  if (!activeModId) return globalTokens;
  const byMod = readStoredDbTokensForMod(activeModId);
  return {
    read: byMod.read || globalTokens.read,
    write: byMod.write || globalTokens.write,
  };
}

export function saveStoredDbTokens(read: string, write: string): void {
  if (typeof localStorage === 'undefined') return;
  const rt = read.trim();
  const wt = write.trim();
  if (rt) localStorage.setItem(LS_DB_READ_TOKEN, rt);
  else localStorage.removeItem(LS_DB_READ_TOKEN);
  if (wt) localStorage.setItem(LS_DB_WRITE_TOKEN, wt);
  else localStorage.removeItem(LS_DB_WRITE_TOKEN);
}

export function saveStoredReadToken(read: string): void {
  if (typeof localStorage === 'undefined') return;
  const rt = read.trim();
  const activeModId = readActiveModId();
  if (activeModId) {
    const { write } = readStoredDbTokensForMod(activeModId);
    saveStoredDbTokensForMod(activeModId, rt, write);
    return;
  }
  if (rt) {
    localStorage.setItem(LS_DB_READ_TOKEN, rt);
  } else {
    localStorage.removeItem(LS_DB_READ_TOKEN);
  }
}

/** 单独保存二级写入口令（Excel 导入数据库等写入类场景使用）。 */
export function saveStoredWriteToken(write: string): void {
  if (typeof localStorage === 'undefined') return;
  const wt = write.trim();
  const activeModId = readActiveModId();
  if (activeModId) {
    const { read } = readStoredDbTokensForMod(activeModId);
    saveStoredDbTokensForMod(activeModId, read, wt);
    return;
  }
  if (wt) {
    localStorage.setItem(LS_DB_WRITE_TOKEN, wt);
  } else {
    localStorage.removeItem(LS_DB_WRITE_TOKEN);
  }
}

const _listProbeUrl = (apiBase: string) => `${apiBase}/api/products/list?page=1&per_page=1`;

const _fetchInit: RequestInit = { credentials: 'same-origin' };

export type ProductsReadLockState = 'open' | 'locked_no_token' | 'locked_bad_token';

export interface ProductsReadProbeOptions {
  /** true 时允许用本地已保存令牌做一次“强制校验”（用于用户刚输入口令后的解锁流程）。 */
  allowStoredTokenBypassGrace?: boolean;
}

export async function getProductsReadLockState(
  apiBase = '',
  options: ProductsReadProbeOptions = {}
): Promise<ProductsReadLockState> {
  const url = _listProbeUrl(apiBase);
  try {
    const r0 = await fetch(url, _fetchInit);
    if (r0.status !== 403) return 'open';
    const h = dbReadHeaders({ ignoreGrace: !!options.allowStoredTokenBypassGrace });
    if (!h['X-FHD-Db-Read-Token']) return 'locked_no_token';
    const r1 = await fetch(url, { ..._fetchInit, headers: h });
    if (r1.status === 403) return 'locked_bad_token';
    touchProductsReadGateGrace();
    return 'open';
  } catch {
    return 'open';
  }
}

export async function probeProductsReadAccess(
  apiBase = '',
  options: ProductsReadProbeOptions = {}
): Promise<boolean> {
  const s = await getProductsReadLockState(apiBase, options);
  return s === 'open';
}

/** 一级：产品库与客户列表 GET；销售合同模板预览、话术→槽位（读库）。 */
const READ_GUARD_PATH =
  /^\/api\/(products\/|customers\/list(?:\/|$)|sales-contract\/(template-preview|resolve-from-text)(?:\/|$))/;

/** 二级：产品增删改 POST；客户创建/改删/批量删/Excel 导入（与后端 ``verify_db_write_token_header`` 对齐）。 */
const WRITE_GUARD_PRODUCTS = /^\/api\/products\/(update|add|delete|batch-delete)(\/|$)/i;
/** 任务执行总入口：部分写操作经由 /api/tools/execute 下发。 */
const WRITE_GUARD_TOOLS_EXECUTE = /^\/api\/tools\/execute(?:\/|$)/i;

function apiPathname(rawUrl: string): string {
  const s = (rawUrl || '').trim();
  if (!s) return '';
  let path = s.split('?')[0] || '';
  if (/^https?:\/\//i.test(path)) {
    try {
      path = new URL(path).pathname || '';
    } catch {
      return '';
    }
  }
  if (!path.startsWith('/')) path = `/${path}`;
  return path;
}

export function urlNeedsDbReadToken(rawUrl: string): boolean {
  return READ_GUARD_PATH.test(apiPathname(rawUrl));
}

/**
 * 是否应在请求头附带 ``X-FHD-Db-Read-Token``。
 * 历史上仅 GET 走读锁；``POST /api/sales-contract/resolve-from-text`` 同样读主数据，须带令牌。
 */
export function shouldAttachDbReadToken(rawUrl: string, method: string): boolean {
  const m = (method || 'GET').toUpperCase();
  const path = apiPathname(rawUrl);
  if (m === 'POST' && /^\/api\/sales-contract\/resolve-from-text(?:\/|$)/i.test(path)) {
    return true;
  }
  return (m === 'GET' || m === 'HEAD') && READ_GUARD_PATH.test(path);
}

/** 受保护请求返回 403 时分发，强制拉起一级口令弹窗（与 GlobalReadTokenPrompt 约定）。 */
export const XCAGI_PROMPT_DB_READ_TOKEN_EVENT = 'xcagi:prompt-db-read-token';

/**
 * Planner/Unified Chat 回传 ``requires_token`` 且为 DB_WRITE_TOKEN（Excel 导入数据库等）时派发，
 * 由 GlobalWriteTokenPrompt 捕获并弹窗要求用户输入二级写入口令。
 */
export const XCAGI_PROMPT_DB_WRITE_TOKEN_EVENT = 'xcagi:prompt-db-write-token';

/** 二级写入口令验证成功后派发，便于上游重试被 403 的导入请求。 */
export const FHD_DB_WRITE_UNLOCKED_EVENT = 'fhd-db-write-unlocked';

/**
 * Planner / 聊天 JSON 仅在「用户刚于弹窗确认」后的下一条请求附带 db_write_token，
 * 避免 localStorage 持久化后静默跳过二级确认（须每次弹窗后再发）。
 */
const SS_PLANNER_CHAT_ATTACH_DB_WRITE_ONCE = 'fhd_planner_chat_attach_db_write_once';

export function armNextPlannerChatDbWriteToken(): void {
  if (typeof sessionStorage === 'undefined') return;
  try {
    sessionStorage.setItem(SS_PLANNER_CHAT_ATTACH_DB_WRITE_ONCE, '1');
  } catch {
    /* ignore */
  }
}

export function isPlannerChatDbWriteTokenArmed(): boolean {
  if (typeof sessionStorage === 'undefined') return false;
  try {
    return sessionStorage.getItem(SS_PLANNER_CHAT_ATTACH_DB_WRITE_ONCE) === '1';
  } catch {
    return false;
  }
}

export function consumePlannerChatDbWriteTokenArm(): void {
  if (typeof sessionStorage === 'undefined') return;
  try {
    sessionStorage.removeItem(SS_PLANNER_CHAT_ATTACH_DB_WRITE_ONCE);
  } catch {
    /* ignore */
  }
}

export function notifyDbReadTokenRequiredAfter403(
  status: number,
  requestUrl: string,
  method: string
): void {
  if (status !== 403 || typeof window === 'undefined') return;
  if (!shouldAttachDbReadToken(requestUrl, method)) return;
  window.dispatchEvent(new CustomEvent(XCAGI_PROMPT_DB_READ_TOKEN_EVENT, { detail: {} }));
}

/** 写入类接口 403（缺令牌或令牌错误）时拉起二级写入口令弹窗（与 GlobalWriteTokenPrompt 约定）。 */
export function notifyDbWriteTokenRequiredAfter403(
  status: number,
  requestUrl: string,
  method: string
): void {
  if (status !== 403 || typeof window === 'undefined') return;
  if (!urlNeedsDbWriteToken(requestUrl, method)) return;
  window.dispatchEvent(
    new CustomEvent(XCAGI_PROMPT_DB_WRITE_TOKEN_EVENT, {
      detail: {
        description: '该接口需要二级数据库写入口令（与服务器 FHD_DB_WRITE_TOKEN 一致）。',
      },
    })
  );
}

export function urlNeedsDbWriteToken(rawUrl: string, method: string): boolean {
  const m = (method || 'GET').toUpperCase();
  if (m === 'GET' || m === 'HEAD' || m === 'OPTIONS') return false;
  const path = apiPathname(rawUrl);
  if (m === 'POST' && WRITE_GUARD_TOOLS_EXECUTE.test(path)) return true;
  if (WRITE_GUARD_PRODUCTS.test(path)) return true;
  if (/^\/api\/customers\/(import|batch-delete)(\/|$)/i.test(path) && m === 'POST') return true;
  if (/^\/api\/customers\/?$/i.test(path) && m === 'POST') return true;
  if (/^\/api\/customers\/\d+\/?$/i.test(path) && (m === 'PUT' || m === 'PATCH' || m === 'DELETE')) {
    return true;
  }
  return false;
}

export function combinedRequestUrl(config: { baseURL?: string; url?: string }): string {
  const u = config.url || '';
  if (/^https?:\/\//i.test(u)) return u;
  const b = (config.baseURL || '').replace(/\/$/, '');
  const path = u.startsWith('/') ? u : `/${u}`;
  return b ? `${b}${path}` : path;
}

export function dbReadHeaders(options: { ignoreGrace?: boolean } = {}): Record<string, string> {
  void options.ignoreGrace;
  const { read } = readStoredDbTokens();
  // 只要本机已存一级口令就随请求携带；勿再用「grace 窗口」卡死头，否则 grace 过期后
  // installFetchDbReadToken / 探针 GET /api/products/list 会永久 403，弹窗提示「口令错误或服务不可达」。
  return read ? { 'X-FHD-Db-Read-Token': read } : {};
}

export function dbWriteHeaders(): Record<string, string> {
  const { write } = readStoredDbTokens();
  return write ? { 'X-FHD-Db-Write-Token': write } : {};
}
