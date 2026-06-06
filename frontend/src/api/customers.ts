import { api } from './core';
import type { ApiResponse } from '@/types/api';
import type { Customer, CustomerCreateDTO, CustomerUpdateDTO } from '@/types/customer';
import { resolveErpApiBase } from '@/utils/erpDomainPaths';

function erpBase(): string {
  return resolveErpApiBase();
}

export const customersApi = {
  getCustomers(params: Record<string, any> = {}): Promise<ApiResponse<Customer[]>> {
    return api.get<ApiResponse<Customer[]>>(`${erpBase()}/customers/list`, params);
  },

  getCustomer(id: number | string): Promise<ApiResponse<Customer>> {
    return api.get<ApiResponse<Customer>>(`${erpBase()}/customers/${id}`);
  },

  createCustomer(data: CustomerCreateDTO): Promise<ApiResponse<Customer>> {
    return api.post<ApiResponse<Customer>>(`${erpBase()}/customers`, data);
  },

  updateCustomer(id: number | string, data: CustomerUpdateDTO): Promise<ApiResponse<Customer>> {
    return api.put<ApiResponse<Customer>>(`${erpBase()}/customers/${id}`, data);
  },

  deleteCustomer(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(`${erpBase()}/customers/${id}`);
  },

  batchDeleteCustomers(customerIds: (number | string)[]): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>(`${erpBase()}/customers/batch-delete`, { ids: customerIds });
  },

  exportCustomersXlsx(templateId?: string): Promise<Response> {
    const params: Record<string, any> = {};
    if (templateId) {
      params.template_id = templateId;
    }
    return api.download(`${erpBase()}/customers/export`, params);
  },

  importCustomersExcel(formData: FormData): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(`${erpBase()}/customers/import`, formData);
  }
};

export default customersApi;
