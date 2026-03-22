import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'
import { productsApi } from '@/api/products'

interface Company {
  id: number | string;
  name: string;
  [key: string]: any;
}

interface LocalProduct {
  id: number | string;
  name: string;
  model?: string;
  code?: string;
  companyId: number | string;
  companyName?: string;
  [key: string]: any;
}

interface ProductQueryState {
  companies: Company[];
  products: LocalProduct[];
  selectedCompany: Company | null;
  selectedProduct: LocalProduct | null;
  searchQuery: string;
  loading: boolean;
  error: string | null;
}

export const useProductQueryStore = defineStore('productQuery', () => {
  const companies = ref<Company[]>([])
  const products = ref<LocalProduct[]>([])
  const selectedCompany = ref<Company | null>(null)
  const selectedProduct = ref<LocalProduct | null>(null)
  const searchQuery = ref('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  const filteredProducts = computed(() => {
    if (!searchQuery.value) return products.value
    
    const query = searchQuery.value.toLowerCase()
    return products.value.filter(product => 
      product.name?.toLowerCase().includes(query) ||
      product.model?.toLowerCase().includes(query) ||
      product.code?.toLowerCase().includes(query)
    )
  })

  function companyProducts(companyId: number | string): LocalProduct[] {
    return products.value.filter(product => product.companyId === companyId)
  }

  async function loadCompanies() {
    loading.value = true
    error.value = null
    
    try {
      const response = await productsApi.getProducts()
      const productsData = response.data as unknown as LocalProduct[] || []
      products.value = productsData
      
      const uniqueCompanies = [...new Set(productsData.map(p => p.companyId))]
      companies.value = uniqueCompanies.map(id => ({
        id,
        name: productsData.find(p => p.companyId === id)?.companyName || `公司${id}`
      }))
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载公司列表失败'
      console.error('Failed to load companies:', err)
    } finally {
      loading.value = false
    }
  }

  async function loadProducts(companyId: number | string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await productsApi.getProducts()
      const allProducts = response.data as unknown as LocalProduct[] || []
      products.value = allProducts.filter(p => p.companyId === companyId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载产品列表失败'
      console.error('Failed to load products:', err)
    } finally {
      loading.value = false
    }
  }

  async function loadAllProducts() {
    loading.value = true
    error.value = null
    
    try {
      const response = await productsApi.getProducts()
      products.value = response.data as unknown as LocalProduct[] || []
      
      const uniqueCompanies = [...new Set(products.value.map(p => p.companyId))]
      companies.value = uniqueCompanies.map(id => ({
        id,
        name: products.value.find(p => p.companyId === id)?.companyName || `公司${id}`
      }))
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载产品列表失败'
      console.error('Failed to load products:', err)
    } finally {
      loading.value = false
    }
  }

  function selectCompany(company: Company) {
    selectedCompany.value = company
    selectedProduct.value = null
    
    if (company) {
      loadProducts(company.id)
    }
  }

  function selectProduct(product: LocalProduct) {
    selectedProduct.value = product
  }

  function searchProducts(query: string) {
    searchQuery.value = query
  }

  async function updateProduct(productId: number | string, data: any) {
    loading.value = true
    error.value = null
    
    try {
      await productsApi.updateProduct(productId, data)
      
      const index = products.value.findIndex(p => p.id === productId)
      if (index !== -1) {
        products.value[index] = { ...products.value[index], ...data }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '更新产品失败'
      console.error('Failed to update product:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function exportProducts(companyId: number | string | null = null) {
    try {
      const params: Record<string, any> = companyId ? { companyId } : {}
      await productsApi.exportUnitProductsXlsx(params)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '导出产品失败'
      console.error('Failed to export products:', err)
      throw err
    }
  }

  function reset() {
    companies.value = []
    products.value = []
    selectedCompany.value = null
    selectedProduct.value = null
    searchQuery.value = ''
    loading.value = false
    error.value = null
  }

  return {
    companies,
    products,
    selectedCompany,
    selectedProduct,
    searchQuery,
    loading,
    error,
    filteredProducts,
    companyProducts,
    loadCompanies,
    loadProducts,
    loadAllProducts,
    selectCompany,
    selectProduct,
    searchProducts,
    updateProduct,
    exportProducts,
    reset
  }
})
