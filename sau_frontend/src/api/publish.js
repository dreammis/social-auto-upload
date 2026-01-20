import { http } from '@/utils/request'

// 视频发布相关API
export const publishApi = {
  // 发布视频到单个平台
  postVideo(data) {
    return http.post('/postVideo', data)
  },
  
  // 批量发布多个文件到多个平台
  postVideosToMultiplePlatforms(data) {
    return http.post('/postVideosToMultiplePlatforms', data)
  },

  // 取消发布任务
  cancelPublishTask(taskId) {
    return http.post('/cancelPublishTask', { id: taskId })
  },

  // 删除发布任务记录
  deletePublishTask(taskId) {
    return http.post('/deletePublishTask', { id: taskId })
  },

  // 获取发布任务状态
  getPublishTaskStatus(taskId) {
    return http.get(`/taskStatus?id=${taskId}`)
  },

  // 获取平台特定参数配置
  getPlatformConfig(platformType) {
    return http.get(`/platformConfig?type=${platformType}`)
  },
  
  // 获取发布任务记录
  getPublishTaskRecords(params) {
    return http.get('/getPublishTaskRecords', params)
  },
  
  // 重试发布任务
  retryPublishTask(taskId) {
    return http.post('/retryPublishTask', { id: taskId })
  }
}