import api from './index';

export const mediaApi = {
  uploadFile(formData) {
    return api.post('/api/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  getImages() {
    return api.get('/api/media/images');
  },

  getVideos() {
    return api.get('/api/media/videos');
  },

  downloadFile(url) {
    return api.download(url);
  }
};

export default mediaApi;
