import { api } from './core';
import type { ApiResponse } from '@/types/api';
import type { Product, ProductCreateDTO, ProductUpdateDTO, ProductQueryParams } from '@/types/product';
import { resolveErpApiBase, resolveErpApiPath } from '@/utils/erpDomainPaths';

function erpBase(): string {
  return resolveErpApiBase();
}

export const productsApi = {
  getProducts(params: ProductQueryParams = {}): Promise<ApiResponse<Product[]>> {
    return api.get<ApiResponse<Product[]>>(`${erpBase()}/products/list`, params);
  },

  async getProductUnits(): Promise<{ success: boolean; data: string[]; count: number }> {
    const resp = await api.get(resolveErpApiPath('/api/products/units'));
    const raw = resp?.data;
    const list = Array.isArray(raw) ? raw : Array.isArray(raw?.units) ? raw.units : [];
    return {
      success: true,
      data: list.map((u: unknown) => String(u ?? '').trim()).filter(Boolean),
      count: list.length,
    };
  },

  getProduct(id: number | string): Promise<ApiResponse<Product>> {
    return api.get<ApiResponse<Product>>(`${erpBase()}/products/${id}`);
  },

  createProduct(data: ProductCreateDTO): Promise<ApiResponse<Product>> {
    return api.post<ApiResponse<Product>>(`${erpBase()}/products/add`, data);
  },

  updateProduct(id: number | string, data: ProductUpdateDTO): Promise<ApiResponse<Product>> {
    return api.post<ApiResponse<Product>>(`${erpBase()}/products/update`, { id, ...data });
  },

  deleteProduct(id: number | string, data: Record<string, any> = {}): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>(`${erpBase()}/products/delete`, { id, ...data });
  },

  batchDeleteProducts(productIds: (number | string)[]): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>(`${erpBase()}/products/batch-delete`, { ids: productIds });
  },

  exportUnitProductsXlsx(params: Record<string, any> = {}): Promise<Response> {
    return api.download(`${erpBase()}/products/export.xlsx`, params);
  },

  exportUnitProductsDocx(params: Record<string, any> = {}): Promise<Response> {
    return api.download(`${erpBase()}/products/export.docx`, params);
  },

  searchProducts(query: string, unit?: string): Promise<ApiResponse<Product[]>> {
    const params: Record<string, any> = { page: 1, per_page: 20 };
    const q = String(query || '').trim();
    if (q) params.keyword = q;
    if (unit) params.unit = unit;
    return api.get<ApiResponse<Product[]>>(`${erpBase()}/products/list`, params);
  },

  getProductNames(params: Record<string, any> = {}): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>(`${erpBase()}/products/product_names`, params);
  },

  searchProductNames(keyword: string): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>(`${erpBase()}/products/product_names/search`, { keyword });
  },

  batchAddProducts(products: ProductCreateDTO[]): Promise<ApiResponse<Product[]>> {
    return api.post<ApiResponse<Product[]>>(`${erpBase()}/products/batch`, { products });
  }
};

export default productsApi;
