/** 与 FHD 后端 X-FHD-Db-*-Token 对齐；合并进现有 axios/fetch 封装。 */

export const LS_DB_READ_TOKEN = "xcagi_db_read_token";
export const LS_DB_WRITE_TOKEN = "xcagi_db_write_token";

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

export function saveStoredReadToken(read: string): void {
  if (typeof localStorage === "undefined") return;
  const rt = read.trim();
  if (rt) localStorage.setItem(LS_DB_READ_TOKEN, rt);
  else localStorage.removeItem(LS_DB_READ_TOKEN);
}

const _listProbeUrl = (apiBase: string) =>
  `${apiBase}/api/products/list?page=1&per_page=1`;

const _fetchInit: RequestInit = { credentials: "same-origin" };

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

export async function probeProductsReadAccess(apiBase = ""): Promise<boolean> {
  const s = await getProductsReadLockState(apiBase);
  return s === "open";
}

/** 一级：仅「产品库」相关 GET（列表、单位、报价导出/预览等），不含客户/采购单位。 */
const READ_GUARD_PATH = /^\/api\/products\//;

/** 二级：兼容层产品增删改 POST。 */
const WRITE_GUARD_PATH = /^\/api\/products\/(update|add|delete|batch-delete)(\/|$)/i;

function apiPathname(rawUrl: string): string {
  const s = (rawUrl || "").trim();
  if (!s) return "";
  let path = s.split("?")[0] || "";
  if (/^https?:\/\//i.test(path)) {
    try {
      path = new URL(path).pathname || "";
    } catch {
      return "";
    }
  }
  if (!path.startsWith("/")) path = `/${path}`;
  return path;
}

export function urlNeedsDbReadToken(rawUrl: string): boolean {
  return READ_GUARD_PATH.test(apiPathname(rawUrl));
}

export function urlNeedsDbWriteToken(rawUrl: string, method: string): boolean {
  const m = (method || "GET").toUpperCase();
  if (m === "GET" || m === "HEAD" || m === "OPTIONS") return false;
  return WRITE_GUARD_PATH.test(apiPathname(rawUrl));
}

export function combinedRequestUrl(config: { baseURL?: string; url?: string }): string {
  const u = config.url || "";
  if (/^https?:\/\//i.test(u)) return u;
  const b = (config.baseURL || "").replace(/\/$/, "");
  const path = u.startsWith("/") ? u : `/${u}`;
  return b ? `${b}${path}` : path;
}

export function dbReadHeaders(): Record<string, string> {
  const { read } = readStoredDbTokens();
  return read ? { "X-FHD-Db-Read-Token": read } : {};
}

export function dbWriteHeaders(): Record<string, string> {
  const { write } = readStoredDbTokens();
  return write ? { "X-FHD-Db-Write-Token": write } : {};
}
