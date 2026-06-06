import { api } from './core';

export const kittenApi = {
  getBusinessSnapshot: () => api.get('/api/ai/kitten/business-snapshot'),

  getCharts: () => api.get('/api/ai/kitten/charts/all'),

  getRevenueChart: (months = 6) => api.get(`/api/ai/kitten/charts/revenue?months=${months}`),

  getProductChart: () => api.get('/api/ai/kitten/charts/products'),

  getCustomerChart: () => api.get('/api/ai/kitten/charts/customers'),

  getProfitChart: (months = 6) => api.get(`/api/ai/kitten/charts/profit?months=${months}`),

  getInventoryChart: () => api.get('/api/ai/kitten/charts/inventory'),

  generateFinancialReport: (metadata = {}) =>
    api.post('/api/ai/kitten/financial/report', { metadata }),

  exportReport: (payload: Record<string, any> = {}) =>
    api.post('/api/ai/kitten/report/export', payload, { responseType: 'blob' }),

  getSavedAnalyses: (type?: string) =>
    api.get(`/api/ai/kitten/saved/list${type ? `?type=${type}` : ''}`),

  getSavedAnalysis: (id: string) => api.get(`/api/ai/kitten/saved/${id}`),

  exportSavedAnalysis: (id: string) =>
    api.get(`/api/ai/kitten/saved/${id}/export`, { responseType: 'blob' }),

  deleteSavedAnalysis: (id: string) => api.delete(`/api/ai/kitten/saved/${id}`),
}

export default kittenApi
