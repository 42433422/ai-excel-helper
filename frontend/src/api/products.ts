import { api } from './index';
import type { ApiResponse } from '@/types/api';
import type { Product, ProductCreateDTO, ProductUpdateDTO, ProductQueryParams } from '@/types/product';

export const productsApi = {
  getProducts(params: ProductQueryParams = {}): Promise<ApiResponse<Product[]>> {
    return api.get<ApiResponse<Product[]>>('/api/products/', params);
  },

  async getProductUnits(): Promise<{ success: boolean; data: string[]; count: number }> {
    // 语义上"产品单位"在该系统里等价于"购买单位/客户"，统一从 customers 取。
    // 返回形状与旧接口保持一致：{ success, data: string[] }
    const resp = await api.get('/api/customers/list', { page: 1, per_page: 1000 });
    const list = resp?.data || [];
    return {
      success: true,
      data: (Array.isArray(list) ? list.map((c: any) => c.customer_name).filter(Boolean) : []),
      count: Array.isArray(list) ? list.length : 0
    };
  },

  getProduct(id: number | string): Promise<ApiResponse<Product>> {
    return api.get<ApiResponse<Product>>(`/api/products/${id}`);
  },

  createProduct(data: ProductCreateDTO): Promise<ApiResponse<Product>> {
    return api.post<ApiResponse<Product>>('/api/products/add', data);
  },

  updateProduct(id: number | string, data: ProductUpdateDTO): Promise<ApiResponse<Product>> {
    return api.post<ApiResponse<Product>>('/api/products/update', { id, ...data });
  },

  deleteProduct(id: number | string, data: Record<string, any> = {}): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/products/delete', { id, ...data });
  },

  batchDeleteProducts(productIds: (number | string)[]): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/products/batch-delete', { ids: productIds });
  },

  exportUnitProductsXlsx(params: Record<string, any> = {}): Promise<Response> {
    return api.download('/api/products/export.xlsx', params);
  },

  searchProducts(query: string, unit: string): Promise<ApiResponse<Product[]>> {
    const params: Record<string, any> = {};
    if (query) params.keyword = query;
    if (unit) params.unit = unit;
    return api.get<ApiResponse<Product[]>>('/api/products/search', params);
  },

  getProductNames(params: Record<string, any> = {}): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>('/api/products/product_names', params);
  },

  searchProductNames(keyword: string): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>('/api/products/product_names/search', { keyword });
  },

  batchAddProducts(products: ProductCreateDTO[]): Promise<ApiResponse<Product[]>> {
    return api.post<ApiResponse<Product[]>>('/api/products/batch', { products });
  }
};

export default productsApi;
