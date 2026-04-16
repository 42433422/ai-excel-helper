import api from './index';

export const ordersApi = {
  getOrders(params = {}) {
    return api.get('/api/orders', params);
  },

  getOrder(id) {
    return api.get(`/api/orders/${id}`);
  },

  createOrder(data) {
    return api.post('/api/orders', data);
  },

  updateOrder(id, data) {
    return api.put(`/api/orders/${id}`, data);
  },

  deleteOrder(id) {
    return api.delete(`/api/orders/${id}`);
  },

  clearAllOrders() {
    return api.post('/api/orders/clear-all');
  },

  searchOrders(query, date) {
    const params = {};
    if (query) params.search = query;
    if (date) params.date = date;
    return api.get('/api/orders', params);
  },

  getShipmentRecords(params = {}) {
    return api.get('/api/shipment-records', params);
  },

  exportShipmentRecords(params = {}) {
    return api.download('/api/shipment-records/export', params);
  },

  updateShipmentRecord(id, data) {
    return api.put(`/api/shipment-records/${id}`, data);
  }
};

export default ordersApi;
