/**
 * 为裸 fetch('/api/products/...') 等补上只读令牌头（与 api/core、utils/apiBase 一致）；
 * 并合并「原版模式」头，使未走 api 封装的请求仍与业务读隐藏策略一致。
 * 须在应用其它代码之前 import 一次。
 */
import { dbReadHeaders, dbWriteHeaders, shouldAttachDbReadToken, urlNeedsDbWriteToken } from './dbTokenHeaders';
import { getActiveExtensionModHeaders, getApiBase, getClientModsUiOffHeader } from '@/utils/apiBase';

declare global {
  interface Window {
    __XCAGI_FHD_FETCH_PATCHED?: boolean;
  }
}

function resolveMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return String(init.method).toUpperCase();
  if (typeof Request !== 'undefined' && input instanceof Request) {
    return String(input.method || 'GET').toUpperCase();
  }
  return 'GET';
}

function resolveUrl(input: RequestInfo | URL): string {
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.href;
  if (typeof Request !== 'undefined' && input instanceof Request) return input.url;
  return '';
}

function configuredApiOrigin(): string {
  if (typeof window === 'undefined') return '';
  const base = String(getApiBase() || '').trim();
  if (!base || !/^https?:\/\//i.test(base)) return '';
  try {
    return new URL(base).origin;
  } catch {
    return '';
  }
}

function shouldPatchRequestHeaders(rawUrl: string): boolean {
  const url = String(rawUrl || '').trim();
  if (!url) return false;
  if (typeof window === 'undefined') return true;
  if (!/^https?:\/\//i.test(url)) return true;
  try {
    const target = new URL(url);
    if (target.origin === window.location.origin) return true;
    const cfg = configuredApiOrigin();
    if (cfg && target.origin === cfg) return true;
    return false;
  } catch {
    return false;
  }
}

export function installFetchDbReadToken(): void {
  if (typeof window === 'undefined' || window.__XCAGI_FHD_FETCH_PATCHED) return;
  window.__XCAGI_FHD_FETCH_PATCHED = true;

  const native = window.fetch.bind(window);

  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const method = resolveMethod(input, init);
    const url = resolveUrl(input);
    if (!url) return native(input, init);
    if (!shouldPatchRequestHeaders(url)) return native(input, init);

    const readExtra = shouldAttachDbReadToken(url, method) ? dbReadHeaders() : {};
    const writeExtra = urlNeedsDbWriteToken(url, method) ? dbWriteHeaders() : {};
    const modsOff = getClientModsUiOffHeader();
    const activeMod = getActiveExtensionModHeaders(url);
    const merged = { ...readExtra, ...writeExtra, ...modsOff, ...activeMod };
    if (!Object.keys(merged).length) return native(input, init);

    if (typeof input === 'string' || input instanceof URL) {
      const headers = new Headers(init?.headers ?? undefined);
      for (const [k, v] of Object.entries(merged)) {
        if (v) headers.set(k, v);
      }
      return native(input, { ...init, headers });
    }

    if (typeof Request !== 'undefined' && input instanceof Request) {
      const headers = new Headers(input.headers);
      for (const [k, v] of Object.entries(merged)) {
        if (v) headers.set(k, v);
      }
      return native(new Request(input, { headers }), init);
    }

    return native(input, init);
  };
}

installFetchDbReadToken();
