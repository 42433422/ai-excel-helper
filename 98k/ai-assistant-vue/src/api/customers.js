import api from './index';

export const customersApi = {
  getCustomers(params = {}) {
    return api.get('/api/customers', params);
  },

  getCustomer(id) {
    return api.get(`/api/customers/${id}`);
  },

  createCustomer(data) {
    return api.post('/api/customers', data);
  },

  updateCustomer(id, data) {
    return api.put(`/api/customers/${id}`, data);
  },

  deleteCustomer(id) {
    return api.delete(`/api/customers/${id}`);
  },

  batchDeleteCustomers(customerIds) {
    return api.post('/api/customers/batch-delete', { customer_ids: customerIds });
  },

  exportCustomersXlsx() {
    return api.download('/api/customers/export.xlsx');
  },

  importCustomersExcel(formData) {
    return api.post('/api/customers/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

export default customersApi;
