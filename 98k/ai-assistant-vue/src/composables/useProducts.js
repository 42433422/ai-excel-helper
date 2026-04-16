import { ref, computed } from 'vue';
import productsApi from '../api/products';
import { useApi, useMutation } from './useApi';

export function useProducts() {
  const products = ref([]);
  const loading = ref(false);
  const error = ref(null);
  const searchQuery = ref('');
  const selectedUnit = ref('');

  const filteredProducts = computed(() => {
    if (!searchQuery.value) {
      return products.value;
    }
    const query = searchQuery.value.toLowerCase();
    return products.value.filter(p => 
      (p.model_number && p.model_number.toLowerCase().includes(query)) ||
      (p.name && p.name.toLowerCase().includes(query))
    );
  });

  const loadProducts = async (params = {}) => {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await productsApi.getProducts({
        unit: selectedUnit.value,
        search: searchQuery.value,
        ...params
      });
      if (result.success && Array.isArray(result.data)) {
        products.value = result.data;
      }
      return result;
    } catch (err) {
      error.value = err;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const createProduct = useMutation(productsApi.createProduct, {
    onSuccess: () => {
      loadProducts();
    }
  });

  const updateProduct = useMutation(
    ({ id, data }) => productsApi.updateProduct(id, data),
    {
      onSuccess: () => {
        loadProducts();
      }
    }
  );

  const deleteProduct = useMutation(
    ({ id, data }) => productsApi.deleteProduct(id, data),
    {
      onSuccess: () => {
        loadProducts();
      }
    }
  );

  const batchDeleteProducts = useMutation(productsApi.batchDeleteProducts, {
    onSuccess: () => {
      loadProducts();
    }
  });

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
    batchDeleteProducts
  };
}

export function useProductDetail(id) {
  const { data, error, loading, execute } = useApi(
    () => productsApi.getProduct(id),
    { immediate: !!id }
  );

  return {
    product: data,
    error,
    loading,
    refresh: execute
  };
}
