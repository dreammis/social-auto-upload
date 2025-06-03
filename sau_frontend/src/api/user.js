import { http } from '@/utils/request'

// 用户相关API
export const userApi = {
  // 获取用户信息
  getUserInfo(id) {
    return http.get(`/user/${id}`)
  },
  
  // 获取用户列表
  getUserList(params) {
    return http.get('/user/list', params)
  },
  
  // 创建用户
  createUser(data) {
    return http.post('/user', data)
  },
  
  // 更新用户信息
  updateUser(id, data) {
    return http.put(`/user/${id}`, data)
  },
  
  // 删除用户
  deleteUser(id) {
    return http.delete(`/user/${id}`)
  },
  
  // 用户登录
  login(data) {
    return http.post('/auth/login', data)
  },
  
  // 用户注册
  register(data) {
    return http.post('/auth/register', data)
  },
  
  // 用户登出
  logout() {
    return http.post('/auth/logout')
  },
  
  // 刷新token
  refreshToken() {
    return http.post('/auth/refresh')
  }
}