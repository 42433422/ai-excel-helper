import api from './index';

export const ordersApi = {
  getOrders(params = {}) {
    return api.get('/api/orders', params);
  },

  getOrder(orderNumber) {
    return api.get(`/api/orders/${encodeURIComponent(orderNumber)}`);
  },

  getLatestOrders() {
    return api.get('/api/orders/latest');
  },

  searchOrders(query) {
    return api.get('/api/orders/search', { q: query || '' });
  },

  deleteOrder(orderNumber) {
    // 实际删除接口在出货/Shipment 服务：/api/shipment/orders/<order_number>
    return api.delete(`/api/shipment/orders/${encodeURIComponent(orderNumber)}`);
  },

  clearAllOrders() {
    return api.delete('/api/orders/clear-all');
  },

  // New shipment-records APIs (Excel workbook style)
  getShipmentRecordUnits() {
    return api.get('/api/shipment/shipment-records/units');
  },

  getShipmentRecords(purchaseUnit) {
    return api.get('/api/shipment/shipment-records/records', { unit: purchaseUnit });
  },

  updateShipmentRecord(payload) {
    return api.patch('/api/shipment/shipment-records/record', payload);
  },

  deleteShipmentRecord(payload) {
    return api.delete('/api/shipment/shipment-records/record', payload);
  },

  exportShipmentRecords(purchaseUnit) {
    return api.download('/api/shipment/shipment-records/export', { unit: purchaseUnit });
  }
};

export default ordersApi;
