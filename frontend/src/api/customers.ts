import { api } from './index';
import type { ApiResponse } from '@/types/api';
import type { Customer, CustomerCreateDTO, CustomerUpdateDTO } from '@/types/customer';

export const customersApi = {
  getCustomers(params: Record<string, any> = {}): Promise<ApiResponse<Customer[]>> {
    return api.get<ApiResponse<Customer[]>>('/api/customers/list', params);
  },

  getCustomer(id: number | string): Promise<ApiResponse<Customer>> {
    return api.get<ApiResponse<Customer>>(`/api/customers/${id}`);
  },

  createCustomer(data: CustomerCreateDTO): Promise<ApiResponse<Customer>> {
    return api.post<ApiResponse<Customer>>('/api/customers', data);
  },

  updateCustomer(id: number | string, data: CustomerUpdateDTO): Promise<ApiResponse<Customer>> {
    return api.put<ApiResponse<Customer>>(`/api/customers/${id}`, data);
  },

  deleteCustomer(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(`/api/customers/${id}`);
  },

  batchDeleteCustomers(customerIds: (number | string)[]): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/customers/batch-delete', { ids: customerIds });
  },

  exportCustomersXlsx(): Promise<Response> {
    return api.download('/api/customers/export');
  },

  importCustomersExcel(formData: FormData): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/customers/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

export default customersApi;
