import { api } from './index';
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
    return api.post<ApiResponse<MediaFile>>('/api/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
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
