import { authApi } from '@/api/auth';

let cachedValid: boolean | null = null;
let cachedAt = 0;
/** 企业版会话校验缓存：减少侧栏频繁切换时重复打 /api/auth/session/validate */
const SESSION_TTL_MS = 5 * 60_000;

function readValid(res: unknown): boolean {
  const r = res as { success?: boolean; valid?: boolean; data?: { valid?: boolean } };
  return r?.success === true || r?.valid === true || r?.data?.valid === true;
}

export async function validateEnterpriseSessionCached(force = false): Promise<boolean> {
  const now = Date.now();
  if (!force && cachedValid !== null && now - cachedAt < SESSION_TTL_MS) {
    return cachedValid;
  }
  const res = await authApi.validateSession();
  cachedValid = readValid(res);
  cachedAt = now;
  return cachedValid;
}

export function invalidateEnterpriseSessionCache(): void {
  cachedValid = null;
  cachedAt = 0;
}
