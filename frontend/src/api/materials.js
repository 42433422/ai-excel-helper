import api from './index';

export const materialsApi = {
  getMaterials(params = {}) {
    return api.get('/api/materials', params);
  },

  getMaterial(id) {
    return api.get(`/api/materials/${id}`);
  },

  createMaterial(data) {
    return api.post('/api/materials', data);
  },

  updateMaterial(id, data) {
    return api.put(`/api/materials/${id}`, data);
  },

  deleteMaterial(id) {
    return api.delete(`/api/materials/${id}`);
  },

  batchDeleteMaterials(materialIds) {
    return api.post('/api/materials/batch-delete', { material_ids: materialIds });
  },

  getLowStockMaterials() {
    return api.get('/api/materials/low-stock');
  },

  searchMaterials(query, category) {
    const params = {};
    if (query) params.search = query;
    if (category) params.category = category;
    return api.get('/api/materials', params);
  }
};

export default materialsApi;
