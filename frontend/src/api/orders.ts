import { api } from './core';
import type { ApiResponse } from '@/types/api';
import type { Order, OrderCreateDTO } from '@/types/order';
import { resolveErpApiPath } from '@/utils/erpDomainPaths';

const erp = (path: string) => resolveErpApiPath(path);

export const ordersApi = {
  getOrders(params: Record<string, any> = {}): Promise<ApiResponse<Order[]>> {
    return api.get<ApiResponse<Order[]>>(erp('/api/orders'), params);
  },

  getOrder(orderNumber: string): Promise<ApiResponse<Order>> {
    return api.get<ApiResponse<Order>>(erp(`/api/orders/${encodeURIComponent(orderNumber)}`));
  },

  getLatestOrders(): Promise<ApiResponse<Order[]>> {
    return api.get<ApiResponse<Order[]>>(erp('/api/orders/latest'));
  },

  searchOrders(query: string): Promise<ApiResponse<Order[]>> {
    return api.get<ApiResponse<Order[]>>(erp('/api/orders/search'), { q: query || '' });
  },

  deleteOrder(orderNumber: string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(erp(`/api/shipment/orders/${encodeURIComponent(orderNumber)}`));
  },

  clearAllOrders(): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(erp('/api/orders/clear-all'));
  },

  async getShipmentRecordUnits(): Promise<ApiResponse<any[]>> {
    try {
      return await api.get<ApiResponse<any[]>>(erp('/api/shipment/shipment-records/units'));
    } catch (e: any) {
      const st = e?.status;
      if (st === 404) {
        return api.get<ApiResponse<any[]>>(erp('/api/purchase_units'));
      }
      throw e;
    }
  },

  getShipmentRecords(purchaseUnit: string): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>(erp('/api/shipment/shipment-records/records'), {
      unit_name: purchaseUnit,
    });
  },

  createShipmentRecord(payload: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/shipment/shipment-records/record'), payload);
  },

  updateShipmentRecord(payload: any): Promise<ApiResponse<any>> {
    return api.patch<ApiResponse<any>>(erp('/api/shipment/shipment-records/record'), payload);
  },

  deleteShipmentRecord(payload: any): Promise<ApiResponse<any>> {
    return api.delete<ApiResponse<any>>(erp('/api/shipment/shipment-records/record'), payload);
  },

  exportShipmentRecords(purchaseUnit: string, templateId?: string, statusFilter?: string): Promise<Response> {
    return api.download(erp('/api/shipment/shipment-records/export'), {
      unit: purchaseUnit,
      template_id: templateId || '',
      status: statusFilter || ''
    });
  }
};

export default ordersApi;
