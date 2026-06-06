import { apiFetch } from '@/utils/apiBase';

/** 与 ModelPaymentView 共用：修茈市场访问令牌（勿提交到版本库）。 */
export const LS_MARKET_ACCESS_TOKEN = 'xcagi_market_access_token';
export const LS_MARKET_REFRESH_TOKEN = 'xcagi_market_refresh_token';
export const LS_MARKET_USER_JSON = 'xcagi_market_user_json';

export type MarketUserProfile = {
  id?: number | string;
  username?: string;
  email?: string;
  phone?: string;
  is_admin?: boolean;
  experience?: number;
  level_profile?: Record<string, unknown>;
  created_at?: string;
};

export type MarketWalletOverview = {
  balance?: number;
  membership_reference_yuan?: number;
};

export type MarketMembershipOverview = {
  tier?: string;
  label?: string;
  is_member?: boolean;
  can_byok?: boolean;
};

export type MarketAccountOverviewData = {
  user: MarketUserProfile;
  market_base_url: string;
  wallet?: MarketWalletOverview;
  plan?: Record<string, unknown> | null;
  membership?: MarketMembershipOverview | null;
  quotas?: Array<Record<string, unknown>>;
  degraded?: boolean;
  market_unreachable?: boolean;
  sync_warning?: string;
  llm?: { providers?: MarketLlmProvider[] };
};

export type MarketAccountSyncData = {
  user: MarketUserProfile;
  market_base_url: string;
};

export type MarketAuthResult = {
  token: string;
  market_base_url: string;
  refresh_token?: string;
  raw?: Record<string, unknown>;
};

export type MarketLlmProvider = {
  provider: string;
  label?: string;
  models?: string[];
  models_detailed?: Array<Record<string, unknown>>;
  error?: string | null;
  fetch_source?: string | null;
};

export type MarketLlmCatalogData = {
  providers: MarketLlmProvider[];
  preferences?: Record<string, unknown>;
  cache_ttl_seconds?: number;
  market_base_url?: string;
};

/** 将用户粘贴的整行 ``Authorization: Bearer …`` 规范为可提交的 authorization 字段。 */
export function normalizePastedAuthorization(raw: string): string {
  let t = (raw || '').trim();
  if (!t) return '';
  if (/^authorization:\s*/i.test(t)) {
    t = t.replace(/^authorization:\s*/i, '').trim();
  }
  return t;
}

/** CSRF 中间件：若请求体带 token 但未显式带 Bearer，POST 会被拦截；同时后端可从 Header 读取令牌。 */
function marketBearerHeaders(rawAuth: string): Record<string, string> {
  const normalized = normalizePastedAuthorization(rawAuth).trim();
  if (!normalized) return {};
  const v = normalized.toLowerCase().startsWith('bearer ') ? normalized : `Bearer ${normalized}`;
  return { Authorization: v };
}

export async function syncMarketAccount(authorization: string): Promise<MarketAccountSyncData> {
  const res = await apiFetch('/api/market/account-sync', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...marketBearerHeaders(authorization) },
    body: JSON.stringify({ authorization }),
  });
  const j = (await res.json()) as {
    success?: boolean;
    detail?: string;
    message?: string;
    data?: MarketAccountSyncData;
  };
  if (!j.success || !j.data) {
    throw new Error(j.detail || j.message || '账号同步失败');
  }
  return j.data;
}

const DEFAULT_MARKET_BASE_HINT =
  'https://xiu-ci.com/market（公网）或 http://119.27.178.147:9999（直连）';

/** 将 HTTP 状态与英文 statusText 转为可展示的中文说明（含 XCAGI_MARKET_BASE_URL 提示）。 */
export function formatMarketServiceError(
  status: number,
  rawMessage: string,
  marketBaseUrl = '',
): string {
  const base = (marketBaseUrl || '').trim();
  const baseHint = base
    ? `请检查服务器 .env 中 XCAGI_MARKET_BASE_URL=${base}`
    : `请检查服务器 .env 中 XCAGI_MARKET_BASE_URL（示例：${DEFAULT_MARKET_BASE_HINT}）`;
  const msg = (rawMessage || '').trim();
  const genericEn = /^internal server error$/i.test(msg) || !msg;
  if (status >= 500) {
    const detail = genericEn ? '' : msg;
    return detail
      ? `市场服务返回 ${status}：${detail}。${baseHint}`
      : `市场服务返回 ${status}（服务器内部错误）。${baseHint}`;
  }
  if (status === 401 || /凭证无效|未授权|unauthorized/i.test(msg)) {
    return '尚未绑定修茈市场账号；请重新登录本软件以自动同步市场会话。';
  }
  return msg || `市场请求失败（HTTP ${status}）`;
}

export function degradedMarketAccountOverview(
  syncWarning: string,
  marketBaseUrl = '',
): MarketAccountOverviewData {
  return {
    user: {},
    market_base_url: marketBaseUrl,
    degraded: true,
    market_unreachable: true,
    sync_warning: syncWarning,
    wallet: { balance: undefined },
    membership: { label: '未同步', tier: 'unknown', can_byok: false },
    quotas: [],
    llm: { providers: [] },
  };
}

function marketErrorBody(j: Record<string, unknown>): {
  message: string;
  marketBaseUrl: string;
} {
  const data = j.data as Record<string, unknown> | undefined;
  const marketBaseUrl =
    (typeof data?.market_base_url === 'string' && data.market_base_url) ||
    (typeof j.market_base_url === 'string' && j.market_base_url) ||
    '';
  const message = String(j.message || j.detail || '').trim();
  return { message, marketBaseUrl };
}

export async function fetchMarketAccountOverview(authorization: string): Promise<MarketAccountOverviewData> {
  const res = await apiFetch('/api/market/account-overview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...marketBearerHeaders(authorization) },
    body: JSON.stringify({ authorization }),
  });
  const j = (await res.json()) as {
    success?: boolean;
    detail?: string;
    message?: string;
    data?: MarketAccountOverviewData;
  };
  if (j.data && (j.success || j.data.degraded || j.data.market_unreachable)) {
    const data = j.data;
    if (data.sync_warning) {
      data.sync_warning = formatMarketServiceError(
        res.status,
        String(data.sync_warning),
        data.market_base_url || '',
      );
    }
    return data;
  }
  const { message, marketBaseUrl } = marketErrorBody(j as Record<string, unknown>);
  if (!res.ok && res.status >= 500) {
    return degradedMarketAccountOverview(
      formatMarketServiceError(res.status, message || res.statusText, marketBaseUrl),
      marketBaseUrl,
    );
  }
  if (!j.success || !j.data) {
    if (res.status === 401) {
      throw new Error(formatMarketServiceError(401, message, marketBaseUrl));
    }
    throw new Error(message || '线上额度同步失败');
  }
  return j.data;
}

export async function fetchMarketLlmCatalog(
  authorization = '',
  refresh = false,
): Promise<MarketLlmCatalogData> {
  const p = new URLSearchParams();
  if (refresh) p.set('refresh', 'true');
  const res = await apiFetch(`/api/market/llm-catalog${p.toString() ? `?${p}` : ''}`, {
    headers: { ...marketBearerHeaders(authorization) },
  });
  const j = (await res.json()) as {
    success?: boolean;
    detail?: string;
    message?: string;
    data?: MarketLlmCatalogData;
  };
  const { message, marketBaseUrl } = marketErrorBody(j as Record<string, unknown>);
  if (j.data && (j.success || (j.data as MarketLlmCatalogData & { degraded?: boolean }).degraded)) {
    const data = j.data as MarketLlmCatalogData & { sync_warning?: string; degraded?: boolean };
    if (data.sync_warning) {
      data.sync_warning = formatMarketServiceError(
        res.status,
        String(data.sync_warning),
        data.market_base_url || marketBaseUrl,
      );
    }
    return data;
  }
  if (!res.ok && res.status >= 500) {
    return {
      providers: [],
      market_base_url: marketBaseUrl,
      degraded: true,
      sync_warning: formatMarketServiceError(res.status, message || res.statusText, marketBaseUrl),
    } as MarketLlmCatalogData & { degraded?: boolean; sync_warning?: string };
  }
  if (!j.success || !j.data) {
    if (res.status === 401) {
      throw new Error(formatMarketServiceError(401, message, marketBaseUrl));
    }
    throw new Error(message || '模型目录同步失败');
  }
  return j.data;
}

/** 从当前 FHD 会话取出服务端绑定的修茈 JWT（登录时已写入进程内映射），用于写入 localStorage 并拼接 ``xcagi_mt`` 跨域跳转。 */
export async function fetchSessionMarketHandoff(): Promise<MarketAuthResult | null> {
  const res = await apiFetch('/api/market/session-handoff');
  const j = (await res.json()) as {
    success?: boolean;
    message?: string;
    data?: {
      market_access_token?: string;
      market_refresh_token?: string;
      market_base_url?: string;
    };
  };
  if (!res.ok || !j.success || !j.data?.market_access_token) {
    return null;
  }
  const refresh =
    typeof j.data.market_refresh_token === 'string' ? j.data.market_refresh_token.trim() : '';
  if (refresh && typeof window !== 'undefined') {
    window.localStorage.setItem(LS_MARKET_REFRESH_TOKEN, refresh);
  }
  return {
    token: j.data.market_access_token.trim(),
    market_base_url: String(j.data.market_base_url || ''),
    refresh_token: refresh || undefined,
  };
}

/** 将服务端会话绑定的修茈令牌写入 localStorage（启动时与登录后调用）。 */
export function persistMarketTokensFromHandoff(handoff: MarketAuthResult | null): void {
  if (typeof window === 'undefined' || !handoff?.token) return;
  window.localStorage.setItem(LS_MARKET_ACCESS_TOKEN, handoff.token);
  if (handoff.refresh_token) {
    window.localStorage.setItem(LS_MARKET_REFRESH_TOKEN, handoff.refresh_token);
  }
}

function readTokenField(payload: Record<string, unknown> | undefined, key: string): string {
  if (!payload) return '';
  const v = payload[key];
  return typeof v === 'string' ? v.trim() : '';
}

/**
 * FHD 登录/注册成功后统一写入市场 token：优先响应字段，否则 session-handoff。
 * 各 View 勿再各自解析 market_access_token。
 */
export async function applyMarketTokensAfterFhdLogin(
  raw: Record<string, unknown>,
): Promise<void> {
  if (typeof window === 'undefined') return;
  const data =
    raw?.data && typeof raw.data === 'object' && !Array.isArray(raw.data)
      ? (raw.data as Record<string, unknown>)
      : undefined;
  const access =
    readTokenField(raw, 'market_access_token') || readTokenField(data, 'market_access_token');
  const refresh =
    readTokenField(raw, 'market_refresh_token') || readTokenField(data, 'market_refresh_token');
  if (access) {
    window.localStorage.setItem(LS_MARKET_ACCESS_TOKEN, access);
    if (refresh) {
      window.localStorage.setItem(LS_MARKET_REFRESH_TOKEN, refresh);
    }
    return;
  }
  const handoff = await fetchSessionMarketHandoff();
  persistMarketTokensFromHandoff(handoff);
}

export async function loginMarketAccount(username: string, password: string): Promise<MarketAuthResult> {
  const res = await apiFetch('/api/market/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const j = (await res.json()) as {
    success?: boolean;
    detail?: string;
    message?: string;
    data?: MarketAuthResult;
  };
  if (!j.success || !j.data?.token) {
    throw new Error(j.detail || j.message || '市场登录失败');
  }
  return j.data;
}

export async function registerMarketAccount(
  username: string,
  password: string,
  email: string,
  verificationCode = '',
): Promise<MarketAuthResult> {
  const res = await apiFetch('/api/market/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username,
      password,
      email,
      verification_code: verificationCode,
    }),
  });
  const j = (await res.json()) as {
    success?: boolean;
    detail?: string;
    message?: string;
    data?: MarketAuthResult;
  };
  if (!j.success || !j.data?.token) {
    throw new Error(j.detail || j.message || '市场注册失败');
  }
  return j.data;
}
