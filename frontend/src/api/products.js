import api from './index';

export const productsApi = {
  getProducts(params = {}) {
    return api.get('/api/products/', params);
  },

  getProduct(id) {
    return api.get(`/api/products/${id}`);
  },

  createProduct(data) {
    return api.post('/api/products/add', data);
  },

  updateProduct(id, data) {
    return api.post('/api/products/update', { id, ...data });
  },

  deleteProduct(id, data = {}) {
    return api.post('/api/products/delete', { id, ...data });
  },

  batchDeleteProducts(productIds) {
    return api.post('/api/products/batch-delete', { ids: productIds });
  },

  exportUnitProductsXlsx(params = {}) {
    return api.download('/api/products/export.xlsx', params);
  },

  searchProducts(query, unit) {
    const params = {};
    if (query) params.keyword = query;
    if (unit) params.unit = unit;
    return api.get('/api/products/search', params);
  },

  getProductNames(params = {}) {
    return api.get('/api/products/product_names', params);
  },

  searchProductNames(keyword) {
    return api.get('/api/products/product_names/search', { keyword });
  },

  batchAddProducts(products) {
    return api.post('/api/products/batch', { products });
  }
};

export default productsApi;
