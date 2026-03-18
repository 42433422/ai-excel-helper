import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useProductQueryStore } from '@/stores/productQuery'

export function useProductQuery() {
  const store = useProductQueryStore()
  
  const loading = computed(() => store.loading)
  const error = computed(() => store.error)
  const companies = computed(() => store.companies)
  const products = computed(() => store.products)
  const selectedCompany = computed(() => store.selectedCompany)
  const selectedProduct = computed(() => store.selectedProduct)
  const searchQuery = computed(() => store.searchQuery)
  const filteredProducts = computed(() => store.filteredProducts)
  
  const loadCompanies = async () => {
    await store.loadCompanies()
  }
  
  const loadProducts = async (companyId) => {
    await store.loadProducts(companyId)
  }
  
  const loadAllProducts = async () => {
    await store.loadAllProducts()
  }
  
  const selectCompany = (company) => {
    store.selectCompany(company)
  }
  
  const selectProduct = (product) => {
    store.selectProduct(product)
  }
  
  const searchProducts = (query) => {
    store.searchProducts(query)
  }
  
  const updateProduct = async (productId, data) => {
    await store.updateProduct(productId, data)
  }
  
  const exportProducts = async (companyId = null) => {
    await store.exportProducts(companyId)
  }
  
  const getCompanyProducts = (companyId) => {
    return store.companyProducts(companyId)
  }
  
  const reset = () => {
    store.reset()
  }
  
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
  }
}
