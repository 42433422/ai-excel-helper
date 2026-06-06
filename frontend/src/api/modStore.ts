import { apiFetch } from '@/utils/apiBase';
import { clearDeliverableStatusCache } from '@/utils/platformShellApi';

export interface ModInfo {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  package_file?: string;
  pkg_id?: string;
  download_url?: string;
  source?: 'remote' | 'local' | string;
  catalog_base_url?: string;
  is_installed: boolean;
  download_count?: number;
  total_downloads?: number;
  avg_rating?: number;
  rating_count?: number;
  created_at?: string;
  dependencies?: Record<string, string>;
  installationInProgress?: boolean;
  uninstallationInProgress?: boolean;
  updateInProgress?: boolean;
}

export interface ModCatalog {
  installed: ModInfo[];
  available: ModInfo[];
  indexed_count: number;
}

export interface ModSearchResult {
  data: ModInfo[];
  count: number;
}

export interface ModStatistics {
  total_downloads: number;
  total_installs: number;
  total_uninstalls: number;
  total_updates: number;
  avg_rating: number;
  rating_count: number;
}

export interface ModRating {
  id: number;
  mod_id: string;
  user_id: string;
  rating: number;
  comment: string;
  created_at: string;
}

export interface ModDetails {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  statistics: ModStatistics | null;
  ratings: ModRating[];
  rating_count: number;
}

export interface InstallResult {
  success: boolean;
  message: string;
  data: {
    id: string;
    name: string;
    version: string;
  };
}

export interface UploadResult {
  success: boolean;
  message: string;
  data: ModInfo;
}

/**
 * 获取 MOD 目录
 */
export async function getModCatalog(): Promise<ModCatalog> {
  const response = await apiFetch('/api/mod-store/catalog');
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '获取 MOD 目录失败');
  }
  
  return data.data;
}

/**
 * 搜索 MOD
 */
export async function searchMods(
  query?: string,
  author?: string,
  installed?: boolean,
  limit: number = 50
): Promise<ModSearchResult> {
  const params = new URLSearchParams();
  
  if (query) params.append('q', query);
  if (author) params.append('author', author);
  if (installed) params.append('installed', 'true');
  params.append('limit', limit.toString());
  
  const response = await apiFetch(`/api/mod-store/search?${params}`);
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '搜索失败');
  }
  
  return data.data;
}

/**
 * 获取热门 MOD
 */
export async function getPopularMods(limit: number = 10): Promise<ModInfo[]> {
  const response = await apiFetch(`/api/mod-store/popular?limit=${limit}`);
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '获取热门 MOD 失败');
  }
  
  return data.data;
}

/**
 * 获取最新 MOD
 */
export async function getRecentMods(limit: number = 10): Promise<ModInfo[]> {
  const response = await apiFetch(`/api/mod-store/recent?limit=${limit}`);
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '获取最新 MOD 失败');
  }
  
  return data.data;
}

/**
 * 获取 MOD 详情
 */
export async function getModDetails(modId: string): Promise<ModDetails> {
  const response = await apiFetch(`/api/mod-store/mod/${modId}/details`);
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '获取 MOD 详情失败');
  }
  
  return data.data;
}

/**
 * 上传 MOD 包
 */
export async function uploadModPackage(
  file: File,
  activate: boolean = false
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('activate', activate.toString());
  
  const response = await apiFetch('/api/mod-store/upload', {
    method: 'POST',
    body: formData,
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.detail || data.error || '上传失败');
  }
  
  return data;
}

/**
 * 安装 MOD
 */
export async function installMod(mod: string | Pick<ModInfo, 'id' | 'pkg_id' | 'version' | 'package_file'>): Promise<InstallResult> {
  const payload = typeof mod === 'string'
    ? { package_file: mod, activate: true, verify_signature: false }
    : {
        pkg_id: mod.pkg_id || mod.id,
        version: mod.version,
        package_file: mod.package_file,
        activate: true,
        verify_signature: false,
      };
  
  const response = await apiFetch('/api/mod-store/install', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.detail || data.error || '安装失败');
  }
  
  return data;
}

/**
 * 卸载 MOD
 */
export async function uninstallMod(modId: string): Promise<{ success: boolean; message: string }> {
  const formData = new FormData();
  formData.append('mod_id', modId);
  formData.append('remove_files', 'true');
  
  const response = await apiFetch('/api/mod-store/uninstall', {
    method: 'POST',
    body: formData,
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.detail || data.error || '卸载失败');
  }
  
  return data;
}

/**
 * 更新 MOD
 */
export async function updateMod(
  modId: string,
  packageFile: string
): Promise<InstallResult> {
  const payload = {
    mod_id: modId,
    package_file: packageFile,
    verify_signature: false,
  };
  
  const response = await apiFetch('/api/mod-store/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.detail || data.error || '更新失败');
  }
  
  return data;
}

/**
 * 验证 MOD 包
 */
export async function validateModPackage(packageFile: string): Promise<{
  success: boolean;
  message: string;
  data: any;
}> {
  const response = await apiFetch(`/api/mod-store/validate?package_file=${encodeURIComponent(packageFile)}`);
  const data = await response.json();
  return data;
}

/**
 * 检查可用更新
 */
export async function checkUpdates(): Promise<{
  updates_available: Array<{
    mod_id: string;
    current_version: string;
    new_version: string;
    package_file: string;
    name: string;
  }>;
  count: number;
}> {
  const response = await apiFetch('/api/mod-store/updates');
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '检查更新失败');
  }
  
  return data.data;
}

/**
 * 解析依赖关系
 */
export async function resolveDependencies(packageFile: string): Promise<{
  mod_id: string;
  dependencies: string[];
  satisfied: Array<{ id: string; version_spec: string; status: string; type: string }>;
  missing: Array<{ id: string; version_spec: string; status: string; type: string }>;
  can_install: boolean;
}> {
  const response = await apiFetch(`/api/mod-store/dependencies?package_file=${encodeURIComponent(packageFile)}`);
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '依赖解析失败');
  }
  
  return data.data;
}

/**
 * 对 MOD 评分
 */
export async function rateMod(
  modId: string,
  rating: number,
  comment: string = '',
  userId: string = ''
): Promise<{ success: boolean; message: string }> {
  const formData = new FormData();
  formData.append('rating', rating.toString());
  formData.append('comment', comment);
  formData.append('user_id', userId);
  
  const response = await apiFetch(`/api/mod-store/mod/${modId}/rate`, {
    method: 'POST',
    body: formData,
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.detail || data.error || '评分失败');
  }
  
  return data;
}

/**
 * 下载 MOD 包
 */
export async function downloadModPackage(packageFile: string): Promise<Blob> {
  const response = await apiFetch(`/api/mod-store/package/${packageFile}/download`);
  
  if (!response.ok) {
    throw new Error('下载失败');
  }
  
  return await response.blob();
}

/**
 * 删除 MOD 包
 */
export async function deleteModPackage(packageFile: string): Promise<{ success: boolean; message: string }> {
  const response = await apiFetch(`/api/mod-store/package/${encodeURIComponent(packageFile)}`, {
    method: 'DELETE',
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.detail || data.error || '删除失败');
  }
  
  return data;
}

/**
 * 重建 MOD 索引
 */
export async function rebuildIndex(): Promise<{
  success: boolean;
  data: { indexed: number; failed: number };
  message: string;
}> {
  const response = await apiFetch('/api/mod-store/index/rebuild', {
    method: 'POST',
  });
  
  const data = await response.json();
  
  if (!data.success) {
    throw new Error(data.error || '重建索引失败');
  }
  
  return data;
}

/** 使用修茈 PAT（mod:sync）从线上 /v1/mod-sync 拉 zip 并由本机后端安装到 mods/ */
export async function syncModstoreLibraryFromRemote(payload: {
  base_url?: string;
  baseUrl?: string;
  token: string;
  mod_ids?: string[] | string;
  all?: boolean;
}): Promise<{
  success: boolean;
  message?: string;
  data?: { installed: string[]; errors: string[] };
}> {
  const response = await apiFetch('/api/mod-store/sync-modstore-library', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = (data && (data.detail || data.message)) || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  clearDeliverableStatusCache();
  return data;
}

/** 一键装齐当前 edition 所需 Mod（先内置种子，再尝试 Catalog） */
/**
 * 安装「宿主基础能力（预装员工）」并 materialize 全部 bridge（非逐项 Mod）。
 */
export async function installHostFoundation(
  edition?: 'minimal' | 'generic' | 'full',
): Promise<{ success: boolean; message: string; data?: Record<string, unknown> }> {
  const q = edition ? `?edition=${encodeURIComponent(edition)}` : '';
  const response = await apiFetch(`/api/mod-store/install-host-foundation${q}`, {
    method: 'POST',
  });
  let data: { success?: boolean; message?: string; detail?: string; error?: string; data?: Record<string, unknown> } =
    {};
  try {
    data = (await response.json()) as typeof data;
  } catch {
    /* 非 JSON 响应 */
  }
  const errMsg =
    (typeof data.message === 'string' && data.message) ||
    (typeof data.detail === 'string' && data.detail) ||
    (typeof data.error === 'string' && data.error) ||
    '';
  if (!response.ok) {
    throw new Error(errMsg || response.statusText || '安装宿主基础员工包失败');
  }
  return {
    success: Boolean(data.success),
    message: errMsg || '安装完成',
    data: data.data,
  };
}

export async function bootstrapEditionPack(
  edition: 'minimal' | 'generic' | 'full' = 'generic',
): Promise<{ success: boolean; message?: string; data?: Record<string, unknown> }> {
  const response = await apiFetch(
    `/api/mod-store/bootstrap-edition-pack?edition=${encodeURIComponent(edition)}`,
    { method: 'POST' },
  );
  const data = await response.json();
  clearDeliverableStatusCache();
  if (!response.ok) {
    const detail = (data && (data.detail || data.message)) || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}
