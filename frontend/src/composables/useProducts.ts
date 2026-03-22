import { ref, computed, type Ref, type ComputedRef } from 'vue';
import productsApi from '../api/products';
import { useApi, useMutation } from './useApi';
import type { Product, ProductCreateDTO, ProductUpdateDTO, ProductQueryParams } from '@/types/product';
import type { ApiResponse } from '@/types/api';

export interface UseProductsReturn {
  products: Ref<Product[]>;
  loading: Ref<boolean>;
  error: Ref<Error | null>;
  searchQuery: Ref<string>;
  selectedUnit: Ref<string>;
  filteredProducts: ComputedRef<Product[]>;
  loadProducts: (params?: ProductQueryParams) => Promise<ApiResponse<Product[]> | null>;
  createProduct: (data: ProductCreateDTO) => Promise<Product | null>;
  updateProduct: (id: number, data: ProductUpdateDTO) => Promise<Product | null>;
  deleteProduct: (id: number, data?: Record<string, any>) => Promise<void | null>;
  batchDeleteProducts: (ids: (number | string)[]) => Promise<void | null>;
  refreshProducts: () => Promise<ApiResponse<Product[]> | null>;
}

export function useProducts(): UseProductsReturn {
  const products = ref<Product[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const searchQuery = ref('');
  const selectedUnit = ref('');

  const filteredProducts = computed<Product[]>(() => {
    if (!searchQuery.value) {
      return products.value;
    }
    const query = searchQuery.value.toLowerCase();
    return products.value.filter(p => 
      (p.model_number && p.model_number.toLowerCase().includes(query)) ||
      (p.name && p.name.toLowerCase().includes(query))
    );
  });

  const loadProducts = async (params: ProductQueryParams = {}): Promise<ApiResponse<Product[]> | null> => {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await productsApi.getProducts({
        unit: selectedUnit.value,
        search: searchQuery.value,
        ...params
      });
      if (result.success && Array.isArray(result.data)) {
        products.value = result.data as Product[];
      }
      return result;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      return null;
    } finally {
      loading.value = false;
    }
  };

  const createProduct = async (data: ProductCreateDTO): Promise<Product | null> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await productsApi.createProduct(data);
      if (result.success && result.data) {
        await loadProducts();
        return result.data as unknown as Product;
      }
      return null;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      return null;
    } finally {
      loading.value = false;
    }
  };

  const updateProduct = async (id: number, data: ProductUpdateDTO): Promise<Product | null> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await productsApi.updateProduct(id, data);
      if (result.success && result.data) {
        await loadProducts();
        return result.data as unknown as Product;
      }
      return null;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      return null;
    } finally {
      loading.value = false;
    }
  };

  const deleteProduct = async (id: number, data?: Record<string, any>): Promise<void | null> => {
    loading.value = true;
    error.value = null;
    try {
      await productsApi.deleteProduct(id, data);
      await loadProducts();
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      return null;
    } finally {
      loading.value = false;
    }
  };

  const batchDeleteProducts = async (ids: (number | string)[]): Promise<void | null> => {
    loading.value = true;
    error.value = null;
    try {
      await productsApi.batchDeleteProducts(ids);
      await loadProducts();
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      return null;
    } finally {
      loading.value = false;
    }
  };

  const refreshProducts = async (): Promise<ApiResponse<Product[]> | null> => {
    return loadProducts({});
  };

  return {
    products,
    loading,
    error,
    searchQuery,
    selectedUnit,
    filteredProducts,
    loadProducts,
    createProduct,
    updateProduct,
    deleteProduct,
    batchDeleteProducts,
    refreshProducts
  };
}

export interface UseProductDetailReturn {
  product: Ref<Product | null>;
  error: Ref<Error | null>;
  loading: Ref<boolean>;
  refresh: () => Promise<Product | null>;
}

export function useProductDetail(id: number | string): UseProductDetailReturn {
  const { data, error, loading, execute } = useApi<Product>(
    async () => {
      const result = await productsApi.getProduct(id);
      return result.data as unknown as Product;
    },
    { immediate: !!id }
  );

  return {
    product: data,
    error,
    loading,
    refresh: execute
  };
}
