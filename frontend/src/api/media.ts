import { api } from './core';
import type { ApiResponse } from '@/types/api';

export interface MediaFile {
  id: number;
  filename: string;
  url: string;
  type: 'image' | 'video' | 'file';
  size: number;
  created_at?: string;
  [key: string]: any;
}

export const mediaApi = {
  uploadFile(formData: FormData): Promise<ApiResponse<MediaFile>> {
    return api.post<ApiResponse<MediaFile>>('/api/media/upload', formData);
  },

  getImages(): Promise<ApiResponse<MediaFile[]>> {
    return api.get<ApiResponse<MediaFile[]>>('/api/media/images');
  },

  getVideos(): Promise<ApiResponse<MediaFile[]>> {
    return api.get<ApiResponse<MediaFile[]>>('/api/media/videos');
  },

  downloadFile(url: string): Promise<Response> {
    return api.download(url);
  }
};

export default mediaApi;
