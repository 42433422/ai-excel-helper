import { api } from './index';
import type { ApiResponse } from '@/types/api';
import type { Order, OrderCreateDTO } from '@/types/order';

export const ordersApi = {
  getOrders(params: Record<string, any> = {}): Promise<ApiResponse<Order[]>> {
    return api.get<ApiResponse<Order[]>>('/api/orders', params);
  },

  getOrder(orderNumber: string): Promise<ApiResponse<Order>> {
    return api.get<ApiResponse<Order>>(`/api/orders/${encodeURIComponent(orderNumber)}`);
  },

  getLatestOrders(): Promise<ApiResponse<Order[]>> {
    return api.get<ApiResponse<Order[]>>('/api/orders/latest');
  },

  searchOrders(query: string): Promise<ApiResponse<Order[]>> {
    return api.get<ApiResponse<Order[]>>('/api/orders/search', { q: query || '' });
  },

  deleteOrder(orderNumber: string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(`/api/shipment/orders/${encodeURIComponent(orderNumber)}`);
  },

  clearAllOrders(): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>('/api/orders/clear-all');
  },

  // New shipment-records APIs (Excel workbook style)
  getShipmentRecordUnits(): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>('/api/shipment/shipment-records/units');
  },

  getShipmentRecords(purchaseUnit: string): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>('/api/shipment/shipment-records/records', { unit: purchaseUnit });
  },

  updateShipmentRecord(payload: any): Promise<ApiResponse<any>> {
    return api.patch<ApiResponse<any>>('/api/shipment/shipment-records/record', payload);
  },

  deleteShipmentRecord(payload: any): Promise<ApiResponse<any>> {
    return api.delete<ApiResponse<any>>('/api/shipment/shipment-records/record', payload);
  },

  exportShipmentRecords(purchaseUnit: string, templateId?: string, statusFilter?: string): Promise<Response> {
    return api.download('/api/shipment/shipment-records/export', {
      unit: purchaseUnit,
      template_id: templateId || '',
      status: statusFilter || ''
    });
  }
};

export default ordersApi;
