import { api } from './index'

export const intentPackagesApi = {
  getPackages() {
    return api.get('/api/intent-packages')
  },

  updatePackages(packages) {
    return api.post('/api/intent-packages', packages)
  },

  updatePackage(packageId, enabled) {
    return api.put(`/api/intent-packages/${packageId}`, { enabled })
  }
}

export default intentPackagesApi
