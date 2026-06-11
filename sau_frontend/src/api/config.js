import { http } from '@/utils/request'

export const configApi = {
  getConfig() {
    return http.get('/getConfig')
  },

  updateConfig(data) {
    return http.post('/updateConfig', data)
  }
}
