import { notifyDbReadTokenRequiredAfter403, notifyDbWriteTokenRequiredAfter403 } from '@/fhd/dbTokenHeaders';
import { getApiBase } from '@/utils/apiBase';
import { readCsrfTokenFromCookie, shouldAttachCsrfHeader } from '@/utils/csrfCookie';

/**
 * 后端 LanLicenseGuard 返回 401 + error=license_* 时派发；
 * App.vue 侧监听并弹出 GlobalLanGateModal（避免每个业务页各自处理未授权跳转）。
 */
export const XCAGI_PROMPT_LAN_GATE_EVENT = 'xcagi:prompt-lan-gate';

const LAN_GATE_ERROR_CODES = new Set([
  'license_required',
  'license_invalid',
  'license_expired',
  'license_revoked',
  'license_misconfigured',
]);

function maybeNotifyLanGate(status: number, errorData: any): void {
  if (status !== 401 && status !== 503) return;
  if (typeof window === 'undefined') return;
  const code = String(errorData?.error || '').trim();
  if (!LAN_GATE_ERROR_CODES.has(code)) return;
  window.dispatchEvent(
    new CustomEvent(XCAGI_PROMPT_LAN_GATE_EVENT, {
      detail: {
        status,
        code,
        message: errorData?.message || '',
      },
    })
  );
}

function buildApiUrl(url: string): string {
  const normalizedUrl = String(url || '');
  if (/^https?:\/\//i.test(normalizedUrl)) {
    return normalizedUrl;
  }
  const base = getApiBase();
  if (!base) {
    return normalizedUrl;
  }
  return normalizedUrl.startsWith('/') ? `${base}${normalizedUrl}` : `${base}/${normalizedUrl}`;
}

/** 当前解析到的 API 基址（含 ``window.__XCMAX_API_BASE__``），随页面注入变化。 */
export function getRuntimeApiBase(): string {
  return getApiBase();
}

/** 与 api.post/get 同源；用于 fetch 健康检查等，避免已配置 API 基址时仍请求到错误源。 */
export function buildFullApiUrl(url: string): string {
  return buildApiUrl(url);
}

/**
 * 冷启动后首个变更请求（如登录 POST）前，须先有一次安全方法请求，后端 ``CSRFMiddleware``
 * 才会下发可读 ``csrf_token`` Cookie；否则 ``X-CSRF-Token`` 无法对齐 → 403「CSRF token missing」。
 */
export async function primeCsrfCookie(): Promise<void> {
  if (typeof window === 'undefined') return;
  const paths = ['/health', '/api/health'];
  for (let attempt = 0; attempt < 3; attempt++) {
    for (const p of paths) {
      try {
        const r = await fetch(buildFullApiUrl(p), { method: 'GET', credentials: 'include' });
        if (r.ok && readCsrfTokenFromCookie()) return;
      } catch {
        /* 下一路径或重试 */
      }
    }
    await new Promise((resolve) => window.setTimeout(resolve, 80));
    if (readCsrfTokenFromCookie()) return;
  }
  // Vite 代理时 Set-Cookie 常不落进当前页的 document.cookie，readCsrfTokenFromCookie 仍为空属常见现象。
  // 登录/登出已由后端 CSRF 豁免；其它变更请求仍可能依赖 Cookie，需排查时再开 VITE_DEBUG_CSRF=1。
  if (import.meta.env.DEV && import.meta.env.VITE_DEBUG_CSRF === '1') {
    console.debug('[primeCsrfCookie] 无 csrf_token Cookie（可忽略若仅登录）。API_BASE=', getApiBase() || '(空)');
  }
}

const defaultHeaders: Record<string, string> = {
  'Content-Type': 'application/json'
};

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export interface RequestOptions extends RequestInit {
  skipDefaultJsonHeader?: boolean;
  responseType?: 'json' | 'blob';
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  total?: number;
}

async function request(url: string, options: RequestOptions = {}): Promise<any> {
  const fullUrl = buildApiUrl(url);
  const { skipDefaultJsonHeader = false, ...requestOptions } = options;
  const config: RequestOptions = {
    credentials: 'include',
    ...requestOptions
  };
  const baseHeaders = skipDefaultJsonHeader ? {} : defaultHeaders;
  config.headers = {
    ...baseHeaders,
    ...(requestOptions.headers || {})
  };

  const method = String(config.method || 'GET');
  const headerRecord: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(config.headers as Record<string, unknown>)) {
    headerRecord[k] = v == null ? undefined : String(v);
  }
  if (shouldAttachCsrfHeader(method, headerRecord)) {
    const tok = readCsrfTokenFromCookie();
    if (tok) {
      (config.headers as Record<string, string>)['X-CSRF-Token'] = tok;
    }
  }

  try {
    const response = await fetch(fullUrl, config);
    const contentType = response.headers.get('content-type') || '';

    if (!response.ok) {
      let errorData = null;
      let errorMessage = `请求失败：${response.status}`;
      
      if (contentType.includes('application/json')) {
        try {
          errorData = await response.json();
          const m =
            (typeof errorData?.message === 'string' && errorData.message) ||
            (typeof errorData?.error?.message === 'string' && errorData.error.message) ||
            (typeof errorData?.detail === 'string' && errorData.detail);
          errorMessage = m || errorMessage;
        } catch (_) {}
      }

      const method = String(config.method || 'GET').toUpperCase();
      notifyDbReadTokenRequiredAfter403(response.status, fullUrl, method);
      notifyDbWriteTokenRequiredAfter403(response.status, fullUrl, method);
      maybeNotifyLanGate(response.status, errorData);

      throw new ApiError(errorMessage, response.status, errorData);
    }

    if (options.responseType === 'blob') {
      return response;
    }

    if (contentType.includes('application/json')) {
      return await response.json();
    }

    return response;
  } catch (error: any) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError((error as any).message || '网络错误', 0, null);
    }
}

export const api = {
  get<T = any>(url: string, params: Record<string, any> = {}, options: RequestOptions = {}): Promise<T> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    return request(fullUrl, {
      method: 'GET',
      ...options
    });
  },

  post<T = any>(url: string, data: any = {}, options: RequestOptions = {}): Promise<T> {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const headers = { ...(options.headers || {}) };
    return request(url, {
      method: 'POST',
      body: isFormData ? data : JSON.stringify(data),
      headers,
      skipDefaultJsonHeader: isFormData,
      ...options
    });
  },

  put<T = any>(url: string, data: any = {}, options: RequestOptions = {}): Promise<T> {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const headers = { ...(options.headers || {}) };
    return request(url, {
      method: 'PUT',
      body: isFormData ? data : JSON.stringify(data),
      headers,
      skipDefaultJsonHeader: isFormData,
      ...options
    });
  },

  patch<T = any>(url: string, data: any = {}, options: RequestOptions = {}): Promise<T> {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const headers = { ...(options.headers || {}) };
    return request(url, {
      method: 'PATCH',
      body: isFormData ? data : JSON.stringify(data),
      headers,
      skipDefaultJsonHeader: isFormData,
      ...options
    });
  },

  delete<T = any>(url: string, data: any = {}, options: RequestOptions = {}): Promise<T> {
    const config: RequestOptions = {
      method: 'DELETE',
      ...options
    };
    if (Object.keys(data).length > 0) {
      config.body = JSON.stringify(data);
    }
    return request(url, config);
  },

  download(url: string, params: Record<string, any> = {}, options: RequestOptions = {}): Promise<Response> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    return request(fullUrl, {
      method: 'GET',
      responseType: 'blob',
      ...options
    });
  }
};

export default api;
