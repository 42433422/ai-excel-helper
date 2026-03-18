import api from './index';

export const ordersApi = {
  getOrders(params = {}) {
    return api.get('/api/shipment/list', params);
  },

  getOrder(id) {
    return api.get(`/api/shipment/${id}`);
  },

  createOrder(data) {
    return api.post('/api/shipment/generate', data);
  },

  updateOrder(id, data) {
    return api.post('/api/shipment/update', { id, ...data });
  },

  deleteOrder(id) {
    return api.post('/api/shipment/delete', { id });
  },

  printOrder(data) {
    return api.post('/api/shipment/print', data);
  },

  downloadOrder(filename) {
    return api.download(`/api/shipment/download/${encodeURIComponent(filename)}`);
  },

  searchOrders(query, date) {
    const params = {};
    if (query) params.keyword = query;
    if (date) params.date = date;
    return api.get('/api/shipment/list', params);
  }
};

export default ordersApi;
