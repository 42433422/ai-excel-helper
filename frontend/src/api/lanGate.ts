import api from './core';
import { resolveLanApiPath } from '@/utils/lanPaths';

const lp = (path: string) => resolveLanApiPath(path);

export interface LanHostInfo {
  enabled: boolean;
  secret_ready: boolean;
  bootstrap_available: boolean;
  has_active_key: boolean;
  has_admin_key: boolean;
  cidrs: string[];
  cookie_name: string;
  token_ttl_seconds: number;
  is_admin_host: boolean;
  ip: string | null;
}

export interface LanStatus {
  success: boolean;
  enabled: boolean;
  ip: string | null;
  in_whitelist: boolean;
  in_static_cidr: boolean;
  in_dynamic_allowlist: boolean;
  is_admin_host: boolean;
  authorized: boolean;
  is_admin: boolean;
  expires_at: number | null;
}

export interface LicenseKey {
  id: number;
  label: string;
  created_at: number;
  created_by: string;
  expires_at: number | null;
  revoked_at: number | null;
  last_used_at: number | null;
  use_count: number;
  is_admin: boolean;
}

export interface LicenseSession {
  id: number;
  jti: string;
  key_id: number | null;
  kid: string;
  ip: string;
  user_agent: string;
  issued_at: number;
  expires_at: number;
  revoked_at: number | null;
  last_seen_at: number | null;
}

export interface AuditEntry {
  id: number;
  ts: number;
  actor: string;
  action: string;
  target: string;
  ip: string;
  detail: string;
}

export interface AccessRequestEntry {
  id: number;
  ip: string;
  device_label: string;
  note: string;
  user_agent: string;
  requested_at: number;
  status: 'pending' | 'approved' | 'rejected';
  reviewed_at: number | null;
  reviewed_by: string;
  review_note: string;
}

export interface AllowedClientEntry {
  id: number;
  ip: string;
  label: string;
  note: string;
  approved_at: number;
  approved_by: string;
  request_id: number | null;
  revoked_at: number | null;
  last_seen_at: number | null;
}

export interface ActivateResponse {
  success: boolean;
  expires_at: number;
  is_admin: boolean;
  kid: string;
}

export interface IssueKeyResponse {
  success: boolean;
  plaintext: string;
  key: LicenseKey;
}

export interface LanSettingsView {
  enabled: boolean;
  secret_ready: boolean;
  secret_length: number;
  secret_preview: string;
  bootstrap_set: boolean;
  bootstrap_length: number;
  bootstrap_preview: string;
  allowed_cidrs: string[];
  source: {
    enabled?: 'env' | 'file';
    license_secret?: 'env' | 'file' | 'unset';
    admin_bootstrap_key?: 'env' | 'file' | 'unset';
    allowed_cidrs?: 'env' | 'file' | 'default';
  };
}

export interface LanSettingsUpdate {
  enabled?: boolean | null;
  license_secret?: string | null;
  admin_bootstrap_key?: string | null;
  allowed_cidrs?: string[] | null;
}

export const lanGateApi = {
  hostInfo(): Promise<LanHostInfo> {
    return api.get<LanHostInfo>(lp('/api/lan/host-info'));
  },
  status(): Promise<LanStatus> {
    return api.get<LanStatus>(lp('/api/lan/status'));
  },
  activate(key: string, label?: string): Promise<ActivateResponse> {
    return api.post<ActivateResponse>(lp('/api/lan/activate'), { key, label });
  },
  requestAccess(payload: { device_label?: string; note?: string }): Promise<{ success: boolean; ip: string; already_allowed?: boolean; request: AccessRequestEntry | null }> {
    return api.post(lp('/api/lan/access-requests'), payload);
  },
  myAccessRequest(): Promise<{
    success: boolean;
    enabled: boolean;
    ip: string | null;
    in_whitelist: boolean;
    in_static_cidr: boolean;
    in_dynamic_allowlist: boolean;
    request: AccessRequestEntry | null;
  }> {
    return api.get(lp('/api/lan/access-requests/mine'));
  },
  logout(): Promise<{ success: boolean }> {
    return api.post(lp('/api/lan/logout'));
  },
  whoami(): Promise<{ success: boolean; ip: string; jti: string; key_id: number | null; is_admin_host: boolean; is_admin_key: boolean }> {
    return api.get(lp('/api/lan/admin/whoami'));
  },
  listKeys(includeRevoked = true): Promise<{ success: boolean; data: LicenseKey[] }> {
    return api.get(lp('/api/lan/admin/keys'), { include_revoked: includeRevoked });
  },
  issueKey(payload: {
    label?: string;
    is_admin?: boolean;
    expires_at?: number | null;
    plaintext?: string | null;
  }): Promise<IssueKeyResponse> {
    return api.post<IssueKeyResponse>(lp('/api/lan/admin/keys'), payload);
  },
  revokeKey(keyId: number): Promise<{ success: boolean }> {
    return api.delete(lp(`/api/lan/admin/keys/${keyId}`));
  },
  listSessions(activeOnly = true, limit = 200): Promise<{ success: boolean; data: LicenseSession[] }> {
    return api.get(lp('/api/lan/admin/sessions'), { active_only: activeOnly, limit });
  },
  kickSession(jti: string): Promise<{ success: boolean }> {
    return api.delete(lp(`/api/lan/admin/sessions/${encodeURIComponent(jti)}`));
  },
  audit(limit = 200): Promise<{ success: boolean; data: AuditEntry[] }> {
    return api.get(lp('/api/lan/admin/audit'), { limit });
  },
  listAccessRequests(status = 'pending', limit = 200): Promise<{ success: boolean; data: AccessRequestEntry[] }> {
    return api.get(lp('/api/lan/admin/access-requests'), { status, limit });
  },
  approveAccessRequest(requestId: number, note = ''): Promise<{ success: boolean; data: AccessRequestEntry }> {
    return api.post(lp(`/api/lan/admin/access-requests/${requestId}/approve`), { note });
  },
  rejectAccessRequest(requestId: number, note = ''): Promise<{ success: boolean; data: AccessRequestEntry }> {
    return api.post(lp(`/api/lan/admin/access-requests/${requestId}/reject`), { note });
  },
  listAllowlist(activeOnly = true, limit = 200): Promise<{ success: boolean; data: AllowedClientEntry[] }> {
    return api.get(lp('/api/lan/admin/allowlist'), { active_only: activeOnly, limit });
  },
  revokeAllowlist(clientId: number): Promise<{ success: boolean }> {
    return api.delete(lp(`/api/lan/admin/allowlist/${clientId}`));
  },
  getSettings(): Promise<LanSettingsView> {
    return api.get<LanSettingsView>(lp('/api/lan/admin/settings'));
  },
  async updateSettings(payload: LanSettingsUpdate): Promise<LanSettingsView> {
    try {
      return await api.post<LanSettingsView>(lp('/api/lan/admin/settings'), payload);
    } catch (error: any) {
      // 兼容旧服务端只接受 PUT 的情况，避免页面保存直接报 405。
      if (Number(error?.status) === 405) {
        return api.put<LanSettingsView>(lp('/api/lan/admin/settings'), payload);
      }
      throw error;
    }
  }
};

export default lanGateApi;
