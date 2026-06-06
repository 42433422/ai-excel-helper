import { api } from './core';
import type { RequestOptions } from './core';

export interface FileInfo {
  name: string;
  is_dir: boolean;
  size: number;
  modified_time: string;
  type: string;
}

export interface ListResponse {
  path: string;
  files: FileInfo[];
}

export interface WatchData {
  files: Record<string, string>;
  checked_at: string;
}

export const traditionalApi = {
  list(path = ''): Promise<{ success: boolean; data?: ListResponse; error?: string }> {
    return api.get('/api/traditional-mode/list', { path });
  },

  read(
    file: string,
    options?: RequestOptions,
    /** 与列表里 size+mtime 一致的指纹，避免代理/浏览器缓存到旧内容 */
    cacheBust?: string
  ): Promise<{ success: boolean; data?: { type: string; content: any }; error?: string }> {
    const params: Record<string, string> = { file }
    if (cacheBust) params.v = cacheBust
    return api.get('/api/traditional-mode/read', params, options || {});
  },

  write(data: { file: string; data: any; type: string }): Promise<{ success: boolean; error?: string }> {
    return api.post('/api/traditional-mode/write', data);
  },

  mkdir(data: { path: string; name: string }): Promise<{ success: boolean; error?: string }> {
    return api.post('/api/traditional-mode/mkdir', data);
  },

  rename(data: { path: string; old_name: string; new_name: string }): Promise<{ success: boolean; error?: string }> {
    return api.post('/api/traditional-mode/rename', data);
  },

  delete(data: {
    path: string;
    name: string;
    /** 与 list/read 一致：相对 ROOT 的完整路径（优先于 path+name，避免目录状态不同步导致 404） */
    rel_target?: string;
  }): Promise<{ success: boolean; error?: string }> {
    return api.post('/api/traditional-mode/delete', data);
  },

  upload(path: string, file: File): Promise<{ success: boolean; error?: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);
    return api.post('/api/traditional-mode/upload', formData);
  },

  watch(path = ''): Promise<{ success: boolean; data?: WatchData; error?: string }> {
    return api.get('/api/traditional-mode/watch', { path });
  }
};

export default traditionalApi;
