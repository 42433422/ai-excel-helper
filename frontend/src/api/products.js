import api from './index';

export const productsApi = {
  getProducts(params = {}) {
    return api.get('/api/products/', params);
  },

  async getProductUnits() {
    // 语义上“产品单位”在该系统里等价于“购买单位/客户”，统一从 customers 取。
    // 返回形状与旧接口保持一致：{ success, data: string[] }
    const resp = await api.get('/api/customers/list', { page: 1, per_page: 1000 });
    const list = resp?.data || [];
    return {
      success: true,
      data: (Array.isArray(list) ? list.map(c => c.customer_name).filter(Boolean) : []),
      count: Array.isArray(list) ? list.length : 0
    };
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
