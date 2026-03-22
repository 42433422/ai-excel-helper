import { api } from './index'

export const systemApi = {
  getIndustries() {
    return api.get('/api/system/industries')
  },

  getCurrentIndustry() {
    return api.get('/api/system/industry')
  },

  setIndustry(industryId) {
    return api.post('/api/system/industry', { industry_id: industryId })
  },

  getIndustryDetail(industryId) {
    return api.get(`/api/system/industry/${industryId}`)
  },

  getSystemConfig() {
    return api.get('/api/system/config')
  }
}

export default systemApi
