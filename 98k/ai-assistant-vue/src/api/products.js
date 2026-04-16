import api from './index';

export const productsApi = {
  getProducts(params = {}) {
    return api.get('/api/products', params);
  },

  getProduct(id) {
    return api.get(`/api/products/${id}`);
  },

  createProduct(data) {
    return api.post('/api/products', data);
  },

  updateProduct(id, data) {
    return api.put(`/api/products/${id}`, data);
  },

  deleteProduct(id, data = {}) {
    return api.delete(`/api/products/${id}`, data);
  },

  batchDeleteProducts(productIds) {
    return api.post('/api/products/batch-delete', { product_ids: productIds });
  },

  exportUnitProductsXlsx(params = {}) {
    return api.download('/api/export_unit_products_xlsx', params);
  },

  searchProducts(query, unit) {
    const params = {};
    if (query) params.search = query;
    if (unit) params.unit = unit;
    return api.get('/api/products', params);
  }
};

export default productsApi;
