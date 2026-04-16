/** 与 FHD 后端 X-FHD-Db-*-Token 对齐；合并进现有 axios/fetch 封装。 */

export const LS_DB_READ_TOKEN = "xcagi_db_read_token";
export const LS_DB_WRITE_TOKEN = "xcagi_db_write_token";

/** 全局解锁成功后派发，各页监听以重新请求受保护 GET */
export const FHD_DB_READ_UNLOCKED_EVENT = "fhd-db-read-unlocked";

export type DbTokensStatus = {
  read_token_configured: boolean;
  write_token_configured: boolean;
};

export async function fetchDbTokensStatus(apiBase = ""): Promise<DbTokensStatus> {
  const r = await fetch(`${apiBase}/api/fhd/db-tokens/status`);
  if (!r.ok) throw new Error(`db-tokens/status ${r.status}`);
  return r.json();
}

export function readStoredDbTokens(): { read: string; write: string } {
  if (typeof localStorage === "undefined") return { read: "", write: "" };
  return {
    read: (localStorage.getItem(LS_DB_READ_TOKEN) || "").trim(),
    write: (localStorage.getItem(LS_DB_WRITE_TOKEN) || "").trim(),
  };
}

export function saveStoredDbTokens(read: string, write: string): void {
  if (typeof localStorage === "undefined") return;
  const rt = read.trim();
  const wt = write.trim();
  if (rt) localStorage.setItem(LS_DB_READ_TOKEN, rt);
  else localStorage.removeItem(LS_DB_READ_TOKEN);
  if (wt) localStorage.setItem(LS_DB_WRITE_TOKEN, wt);
  else localStorage.removeItem(LS_DB_WRITE_TOKEN);
}

/** 产品页解锁用：只更新一级令牌，不改动二级。 */
export function saveStoredReadToken(read: string): void {
  if (typeof localStorage === "undefined") return;
  const rt = read.trim();
  if (rt) localStorage.setItem(LS_DB_READ_TOKEN, rt);
  else localStorage.removeItem(LS_DB_READ_TOKEN);
}

const _listProbeUrl = (apiBase: string) =>
  `${apiBase}/api/products/list?page=1&per_page=1`;

const _fetchInit: RequestInit = { credentials: "same-origin" };

/**
 * 仅根据产品列表接口判断一级锁（不依赖 /api/fhd/db-tokens/status，避免该请求失败或旧后端无此路由时误判为「无需锁」）。
 * - open：未配置 FHD_DB_READ_TOKEN，或已带正确读头可访问
 * - locked_no_token：服务器要求读头，但本地未保存
 * - locked_bad_token：本地有读头但仍 403
 */
export type ProductsReadLockState = "open" | "locked_no_token" | "locked_bad_token";

export async function getProductsReadLockState(apiBase = ""): Promise<ProductsReadLockState> {
  const url = _listProbeUrl(apiBase);
  try {
    const r0 = await fetch(url, _fetchInit);
    if (r0.status !== 403) return "open";
    const h = dbReadHeaders();
    if (!h["X-FHD-Db-Read-Token"]) return "locked_no_token";
    const r1 = await fetch(url, { ..._fetchInit, headers: h });
    if (r1.status === 403) return "locked_bad_token";
    return "open";
  } catch {
    return "open";
  }
}

/** 与 getProductsReadLockState 一致：open 表示可访问产品 GET。 */
export async function probeProductsReadAccess(apiBase = ""): Promise<boolean> {
  const s = await getProductsReadLockState(apiBase);
  return s === "open";
}

/**
 * 与 backend ``xcagi_compat`` 中 ``verify_db_read_token_header`` 的 GET 路径一致
 *（含 ``/api/products/price-list-template-preview`` 等）。
 */
const READ_GUARD_PATH = /^\/api\/(products\/|customers|purchase_units|shipment\/shipment-records\/units)/;

/** 从绝对或相对 URL 得到 pathname 后判断是否须带读头 */
export function urlNeedsDbReadToken(rawUrl: string): boolean {
  const s = (rawUrl || "").trim();
  if (!s) return false;
  let path = s.split("?")[0] || "";
  if (/^https?:\/\//i.test(path)) {
    try {
      path = new URL(path).pathname || "";
    } catch {
      return false;
    }
  }
  if (!path.startsWith("/")) path = `/${path}`;
  return READ_GUARD_PATH.test(path);
}

/** axios 风格 config 拼出完整 URL（用于拦截器） */
export function combinedRequestUrl(config: { baseURL?: string; url?: string }): string {
  const u = config.url || "";
  if (/^https?:\/\//i.test(u)) return u;
  const b = (config.baseURL || "").replace(/\/$/, "");
  const path = u.startsWith("/") ? u : `/${u}`;
  return b ? `${b}${path}` : path;
}

/** 附加到只读产品/客户 GET */
export function dbReadHeaders(): Record<string, string> {
  const { read } = readStoredDbTokens();
  return read ? { "X-FHD-Db-Read-Token": read } : {};
}

/** 附加到 bulk-import 等写接口 */
export function dbWriteHeaders(): Record<string, string> {
  const { write } = readStoredDbTokens();
  return write ? { "X-FHD-Db-Write-Token": write } : {};
}
