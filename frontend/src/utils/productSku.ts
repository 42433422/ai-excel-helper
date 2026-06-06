import { apiFetch } from '@/utils/apiBase';

let cachedSku: string | null = null;
let skuFetchPromise: Promise<string> | null = null;

function viteDevSkuOverride(): string | null {
  if (!import.meta.env.DEV) return null;
  const raw = import.meta.env.VITE_XCAGI_PRODUCT_SKU;
  if (typeof raw !== 'string') return null;
  const sku = raw.trim().toLowerCase();
  return sku || null;
}

export async function fetchProductSku(force = false): Promise<string> {
  const viteSku = viteDevSkuOverride();
  if (!force && viteSku) {
    cachedSku = viteSku;
    return viteSku;
  }
  if (!force && cachedSku) return cachedSku;
  if (!force && skuFetchPromise) return skuFetchPromise;
  skuFetchPromise = (async () => {
    try {
      const res = await apiFetch('/api/runtime/product-sku', { timeoutMs: 8_000 });
      if (res.ok) {
        const body = await res.json();
        const sku = String(body?.data?.sku || body?.sku || 'generic').trim() || 'generic';
        cachedSku = viteSku || sku;
        return cachedSku;
      }
    } catch {
      /* ignore */
    }
    cachedSku = viteSku || cachedSku || 'generic';
    return cachedSku;
  })();
  try {
    return await skuFetchPromise;
  } finally {
    skuFetchPromise = null;
  }
}

export function isEnterpriseEdition(sku?: string | null): boolean {
  const s = (sku ?? cachedSku ?? '').trim();
  return s === 'enterprise';
}
