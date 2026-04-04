import { computed } from 'vue';
import { useProductQueryStore } from '@/stores/productQuery';

export function useProductQuery(): any {
  const store = useProductQueryStore();

  const loading = computed(() => store.loading);
  const error = computed(() => store.error);
  const companies = computed(() => store.companies);
  const products = computed(() => store.products);
  const selectedCompany = computed(() => store.selectedCompany);
  const selectedProduct = computed(() => store.selectedProduct);
  const searchQuery = computed(() => store.searchQuery);
  const filteredProducts = computed(() => store.filteredProducts);

  const loadCompanies = async () => {
    await store.loadCompanies();
  };

  const loadProducts = async (companyId: number | string) => {
    await store.loadProducts(companyId);
  };

  const loadAllProducts = async () => {
    await store.loadAllProducts();
  };

  const selectCompany = (company: any) => {
    store.selectCompany(company);
  };

  const selectProduct = (product: any) => {
    store.selectProduct(product);
  };

  const searchProducts = (query: string) => {
    store.searchProducts(query);
  };

  const updateProduct = async (productId: number | string, data: Record<string, any>) => {
    await store.updateProduct(productId, data);
  };

  const exportProducts = async (companyId: number | string | null = null) => {
    await store.exportProducts(companyId);
  };

  const getCompanyProducts = (companyId: number | string) => {
    return store.companyProducts(companyId);
  };

  const reset = () => {
    store.reset();
  };

  return {
    loading,
    error,
    companies,
    products,
    selectedCompany,
    selectedProduct,
    searchQuery,
    filteredProducts,
    loadCompanies,
    loadProducts,
    loadAllProducts,
    selectCompany,
    selectProduct,
    searchProducts,
    updateProduct,
    exportProducts,
    getCompanyProducts,
    reset
  };
}
