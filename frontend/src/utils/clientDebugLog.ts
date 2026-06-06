import { apiFetch } from './apiBase';

const STORAGE_KEY = 'xcagi_client_debug_log';

function isBridgeEnabled(): boolean {
  try {
    if (localStorage.getItem(STORAGE_KEY) === '0') return false;
    if (localStorage.getItem(STORAGE_KEY) === '1') return true;
  } catch {
    /* ignore */
  }
  if (import.meta.env.VITE_CLIENT_DEBUG_LOG === 'true') return true;
  return import.meta.env.DEV === true;
}

function clip(s: string, max = 8000): string {
  if (s.length <= max) return s;
  return `${s.slice(0, max)}…`;
}

function stringifyArgs(args: unknown[]): string {
  return args
    .map((a) => {
      try {
        if (a instanceof Error) return a.stack || a.message;
        if (typeof a === 'object' && a !== null) return JSON.stringify(a);
        return String(a);
      } catch {
        return String(a);
      }
    })
    .join(' ');
}

let posting = false;
let bridgeForbidden = false;
const queue: Record<string, unknown>[] = [];

function flushQueue(): void {
  if (bridgeForbidden) {
    queue.length = 0;
    return;
  }
  if (posting || queue.length === 0) return;
  posting = true;
  const batch = queue.splice(0, 8);
  void Promise.all(
    batch.map((body) =>
      apiFetch('/api/debug/client-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
        .then((resp) => {
          // 404：后端未挂载该路由或代理未指向 FastAPI；停止上报避免控制台刷屏
          if (resp.status === 403 || resp.status === 404) {
            bridgeForbidden = true;
            queue.length = 0;
          }
        })
        .catch(() => {})
    )
  ).finally(() => {
    posting = false;
    if (!bridgeForbidden && queue.length) flushQueue();
  });
}

/** 与旧版静态页一致：写入后端 ``debug_ndjson.log``（需路由 ``/api/debug/client-log`` 可用）。 */
export function postClientDebugLog(payload: Record<string, unknown>): void {
  if (!isBridgeEnabled() || bridgeForbidden) return;
  queue.push(payload);
  flushQueue();
}

/**
 * 将 ``console.error`` / ``console.warn`` 镜像到服务端 NDJSON（开发环境默认开启）。
 * 生产环境可设 ``localStorage.xcagi_client_debug_log='1'`` 或 ``VITE_CLIENT_DEBUG_LOG=true``。
 * 关闭：``localStorage.xcagi_client_debug_log='0'``。
 */
export function installClientConsoleBridge(): void {
  if (!isBridgeEnabled() || bridgeForbidden) return;

  const origError = console.error.bind(console);
  const origWarn = console.warn.bind(console);

  console.error = (...args: unknown[]) => {
    origError(...args);
    queue.push({
      runId: 'vue-shell',
      hypothesisId: 'console',
      location: 'console.error',
      message: clip(stringifyArgs(args)),
      data: {},
    });
    flushQueue();
  };

  console.warn = (...args: unknown[]) => {
    origWarn(...args);
    queue.push({
      runId: 'vue-shell',
      hypothesisId: 'console',
      location: 'console.warn',
      message: clip(stringifyArgs(args)),
      data: {},
    });
    flushQueue();
  };
}
