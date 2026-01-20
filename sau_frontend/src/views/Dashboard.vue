<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>自媒体发布平台</h1>
    </div>
    
    <div class="dashboard-content">
      <el-row :gutter="20">
        <!-- 账号统计卡片 -->
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon">
                <el-icon><User /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ accountStats.total }}</div>
                <div class="stat-label">账号总数</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <span>正常: {{ accountStats.normal }}</span>
                <span>异常: {{ accountStats.abnormal }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- 平台统计卡片 -->
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon platform-icon">
                <el-icon><Platform /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ platformStats.total }}</div>
                <div class="stat-label">平台总数</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <template v-if="platformStats.distribution && platformStats.distribution.length > 0">
                  <el-tooltip
                    v-for="item in platformStats.distribution"
                    :key="item.platform"
                    :content="item.platform + '账号'"
                    placement="top"
                  >
                    <el-tag
                      size="small"
                      :type="getPlatformTagType(item.platform)"
                    >
                      {{ item.platform }}: {{ item.count }}
                    </el-tag>
                  </el-tooltip>
                </template>
                <div v-else class="no-data">暂无平台数据</div>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- 任务统计卡片 -->
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon task-icon">
                <el-icon><List /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ taskStats.total }}</div>
                <div class="stat-label">任务总数</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <span>完成: {{ taskStats.completed }}</span>
                <span>进行中: {{ taskStats.inProgress }}</span>
                <span>失败: {{ taskStats.failed }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
        
        <!-- 内容统计卡片 -->
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon content-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contentStats.total }}</div>
                <div class="stat-label">内容总数</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <span>已发布: {{ contentStats.published }}</span>
                <span>草稿: {{ contentStats.draft }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 快捷操作区域 -->
      <div class="quick-actions">
        <h2>快捷操作</h2>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/account-management')">
              <div class="action-icon">
                <el-icon><UserFilled /></el-icon>
              </div>
              <div class="action-title">账号管理</div>
              <div class="action-desc">管理所有平台账号</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/material-management')">
              <div class="action-icon">
                <el-icon><Upload /></el-icon>
              </div>
              <div class="action-title">内容上传</div>
              <div class="action-desc">上传视频和图文内容</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/publish-center')">
              <div class="action-icon">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="action-title">定时发布</div>
              <div class="action-desc">设置内容发布时间</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/data')">
              <div class="action-icon">
                <el-icon><DataAnalysis /></el-icon>
              </div>
              <div class="action-title">数据分析</div>
              <div class="action-desc">查看内容数据分析</div>
            </el-card>
          </el-col>
        </el-row>
      </div>
      
      <!-- 发布任务记录 -->
      <div class="publish-task-records">
        <div class="section-header">
          <h2>最近发布任务</h2>
          <el-button text>查看全部</el-button>
        </div>
        
        <el-table :data="publishTaskRecords" style="width: 100%">
          <el-table-column prop="fileName" label="文件名" width="200" />
          <el-table-column prop="platformName" label="平台" width="120">
            <template #default="scope">
              <el-tag
                :type="getPlatformTagType(scope.row.platformName)"
                effect="plain"
              >
                {{ scope.row.platformName }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="accountName" label="账号" width="150" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="scope">
              <el-tag
                :type="getPublishStatusTagType(scope.row.status)"
                effect="plain"
              >
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createTime" label="创建时间" width="180" />
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button size="small" @click="viewPublishTaskDetail(scope.row)">查看详情</el-button>
              <el-button 
                size="small" 
                type="primary" 
                v-if="scope.row.status === '发布失败'"
                @click="retryPublishTask(scope.row)"
              >
                重试
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                v-if="scope.row.status === '发布中' || scope.row.status === '待发布'"
                @click="cancelPublishTask(scope.row)"
              >
                取消
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  User, UserFilled, Platform, List, Document, 
  Upload, Timer, DataAnalysis 
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { publishApi } from '@/api/publish'

const router = useRouter()

// 账号统计数据
const accountStats = reactive({
  total: 0,
  normal: 0,
  abnormal: 0
})

// 平台统计数据
const platformStats = reactive({
  total: 0,
  kuaishou: 0,
  douyin: 0,
  channels: 0,
  xiaohongshu: 0,
  tiktok: 0,
  distribution: []
})

// 任务统计数据
const taskStats = reactive({
  total: 0,
  completed: 0,
  inProgress: 0,
  failed: 0
})

// 内容统计数据
const contentStats = reactive({
  total: 0,
  published: 0,
  draft: 0
})

// 发布任务记录数据
const publishTaskRecords = ref([])

// 平台映射
const platformMap = {
  1: { name: '小红书', type: 'xiaohongshu' },
  2: { name: '视频号', type: 'weixin' },
  3: { name: '抖音', type: 'douyin' },
  4: { name: '快手', type: 'kuaishou' },
  5: { name: 'TikTok', type: 'tiktok' },
  6: { name: 'Instagram', type: 'instagram' },
  7: { name: 'Facebook', type: 'facebook' },
  8: { name: '哔哩哔哩', type: 'bilibili' },
  9: { name: '百家号', type: 'baijiahao' }
}

// 获取平台统计数据
async function fetchPlatformStats() {
  try {
    const response = await fetch('/api/getPlatformStats')
    const data = await response.json()
    
    if (data.code === 200) {
      // 更新账号统计
      accountStats.total = data.data.overall.total_accounts || 0
      accountStats.normal = data.data.overall.valid_accounts || 0
      accountStats.abnormal = accountStats.total - accountStats.normal
      
      // 更新平台分布
      platformStats.total = data.data.platform_stats.length || 0  // 平台数量
      platformStats.distribution = []
      
      data.data.platform_stats.forEach(stat => {
        const platform = platformMap[stat.platform] || { name: '未知', type: 'unknown' }
        platformStats.distribution.push({
          platform: platform.name,
          count: stat.total,
          type: platform.type
        })
        
        // 更新原有格式的平台统计数据以兼容现有模板
        if (platform.name === '快手') platformStats.kuaishou = stat.total
        if (platform.name === '抖音') platformStats.douyin = stat.total
        if (platform.name === '视频号') platformStats.channels = stat.total
        if (platform.name === '小红书') platformStats.xiaohongshu = stat.total
        if (platform.name === 'TikTok') platformStats.tiktok = stat.total
        if (platform.name === 'Instagram') platformStats.instagram = stat.total
        if (platform.name === 'Facebook') platformStats.facebook = stat.total
        if (platform.name === '哔哩哔哩') platformStats.bilibili = stat.total
        if (platform.name === '百家号') platformStats.baijiahao = stat.total
      })
    }
  } catch (error) {
    console.error('获取平台统计数据失败:', error)
    ElMessage.error('获取平台统计数据失败')
  }
}

// 获取文件统计数据
async function fetchFileStats() {
  try {
    const response = await fetch('/api/getFileStats')
    const data = await response.json()
    
    if (data.code === 200) {
      // 这里可以根据实际需求更新文件相关统计
      // 暂时保持任务和内容统计的默认值，因为数据库中没有对应表
    }
  } catch (error) {
    console.error('获取文件统计数据失败:', error)
    ElMessage.error('获取文件统计数据失败')
  }
}

// 获取发布任务记录
async function fetchPublishTaskRecords() {
  try {
    const response = await publishApi.getPublishTaskRecords()
    const data = response
    
    if (data.code === 200) {
      publishTaskRecords.value = data.data.records || []
    }
  } catch (error) {
    console.error('获取发布任务记录失败:', error)
    ElMessage.error('获取发布任务记录失败')
    // 模拟数据
    publishTaskRecords.value = [
      { id: '1', fileName: '视频1.mp4', platformName: '抖音', accountName: '抖音1账号', status: '发布成功', createTime: '2026-01-14 10:00:00', updateTime: '2026-01-14 10:05:00' },
      { id: '2', fileName: '视频1.mp4', platformName: '抖音', accountName: '抖音2账号', status: '发布中', createTime: '2026-01-14 10:15:00', updateTime: '2026-01-14 10:16:00' },
      { id: '3', fileName: '视频1.mp4', platformName: '快手', accountName: '快手1账号', status: '发布失败', createTime: '2026-01-14 10:30:00', updateTime: '2026-01-14 10:32:00' },
      { id: '4', fileName: '视频2.mp4', platformName: '抖音', accountName: '抖音1账号', status: '待发布', createTime: '2026-01-14 11:00:00', updateTime: '2026-01-14 11:00:00' },
      { id: '5', fileName: '视频2.mp4', platformName: '抖音', accountName: '抖音2账号', status: '待发布', createTime: '2026-01-14 11:15:00', updateTime: '2026-01-14 11:15:00' },
      { id: '6', fileName: '视频2.mp4', platformName: '快手', accountName: '快手1账号', status: '发布成功', createTime: '2026-01-14 11:30:00', updateTime: '2026-01-14 11:35:00' }
    ]
  } finally {
    // 更新任务统计数据
    updateTaskStats()
  }
}

// 更新任务统计数据
function updateTaskStats() {
  const records = publishTaskRecords.value || []
  
  // 计算各状态任务数量
  const completedCount = records.filter(record => record.status === '发布成功').length
  const inProgressCount = records.filter(record => record.status === '发布中' || record.status === '待发布').length
  const failedCount = records.filter(record => record.status === '发布失败' || record.status === '已取消').length
  
  // 更新任务统计
  taskStats.total = records.length
  taskStats.completed = completedCount
  taskStats.inProgress = inProgressCount
  taskStats.failed = failedCount
}

// 组件挂载时获取数据
onMounted(() => {
  fetchPlatformStats()
  fetchFileStats()
  fetchPublishTaskRecords()
})

// 根据平台获取标签类型
const getPlatformTagType = (platform) => {
  const typeMap = {
    '快手': 'success',
    '抖音': 'danger',
    '视频号': 'warning',
    '小红书': 'info',
    'TikTok': 'primary',
    'Instagram': 'primary',
    'Facebook': 'primary',
    '哔哩哔哩': 'info',
    '百家号': 'warning',
    '未知': 'default'
  }
  return typeMap[platform] || 'default'
}

// 根据发布状态获取标签类型
const getPublishStatusTagType = (status) => {
  const typeMap = {
    '发布成功': 'success',
    '发布中': 'warning',
    '待发布': 'info',
    '发布失败': 'danger',
    '已取消': 'default'
  }
  return typeMap[status] || 'info'
}

// 导航到指定路由
const navigateTo = (path) => {
  router.push(path)
}

// 查看发布任务详情
const viewPublishTaskDetail = (task) => {
  ElMessage.info(`查看发布任务详情: ${task.fileName} - ${task.platformName} - ${task.accountName}`)
  // 实际应用中应该跳转到发布任务详情页面
}

// 重试发布任务
const retryPublishTask = (task) => {
  ElMessageBox.confirm(
    `确定要重试发布任务吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info',
    }
  )
    .then(() => {
      // 更新任务状态
      const index = publishTaskRecords.value.findIndex(t => t.id === task.id)
      if (index !== -1) {
        publishTaskRecords.value[index].status = '发布中'
        publishTaskRecords.value[index].updateTime = new Date().toLocaleString()
        // 更新任务统计
        updateTaskStats()
      }
      ElMessage({
        type: 'success',
        message: '发布任务已开始重试',
      })
    })
    .catch(() => {
      // 取消操作
    })
}

// 取消发布任务
const cancelPublishTask = (task) => {
  ElMessageBox.confirm(
    `确定要取消发布任务吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(() => {
      // 更新任务状态
      const index = publishTaskRecords.value.findIndex(t => t.id === task.id)
      if (index !== -1) {
        publishTaskRecords.value[index].status = '已取消'
        publishTaskRecords.value[index].updateTime = new Date().toLocaleString()
        // 更新任务统计
        updateTaskStats()
      }
      ElMessage({
        type: 'success',
        message: '发布任务已取消',
      })
    })
    .catch(() => {
      // 取消操作
    })
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.dashboard {
  .page-header {
    margin-bottom: 20px;
    
    h1 {
      font-size: 24px;
      color: $text-primary;
      margin: 0;
    }
  }
  
  .dashboard-content {
    .stat-card {
      height: 140px;
      margin-bottom: 20px;
      
      .stat-card-content {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        
        .stat-icon {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background-color: rgba($primary-color, 0.1);
          display: flex;
          justify-content: center;
          align-items: center;
          margin-right: 15px;
          
          .el-icon {
            font-size: 30px;
            color: $primary-color;
          }
          
          &.platform-icon {
            background-color: rgba($success-color, 0.1);
            
            .el-icon {
              color: $success-color;
            }
          }
          
          &.task-icon {
            background-color: rgba($warning-color, 0.1);
            
            .el-icon {
              color: $warning-color;
            }
          }
          
          &.content-icon {
            background-color: rgba($info-color, 0.1);
            
            .el-icon {
              color: $info-color;
            }
          }
        }
        
        .stat-info {
          .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: $text-primary;
            line-height: 1.2;
          }
          
          .stat-label {
            font-size: 14px;
            color: $text-secondary;
          }
        }
      }
      
      .stat-footer {
        border-top: 1px solid $border-lighter;
        padding-top: 10px;
        
        .stat-detail {
          display: flex;
          justify-content: space-between;
          color: $text-secondary;
          font-size: 13px;
          overflow-x: auto;
          white-space: nowrap;
          padding-bottom: 5px;
          
          .el-tag {
            margin-right: 5px;
            flex-shrink: 0;
          }
          
          &::-webkit-scrollbar {
            height: 4px;
          }
          
          &::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 2px;
          }
          
          &::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 2px;
            
            &:hover {
              background: #a8a8a8;
            }
          }
        }
      }
    }
    
    .quick-actions {
        margin: 20px 0 30px;
        
        h2 {
          font-size: 18px;
          margin-bottom: 15px;
          color: $text-primary;
        }
        
        .el-row {
          overflow-x: auto;
          white-space: nowrap;
          flex-wrap: nowrap;
          margin: 0 -10px;
          padding: 0 10px 10px;
          
          .el-col {
            flex-shrink: 0;
            padding: 0 10px;
          }
          
          &::-webkit-scrollbar {
            height: 4px;
          }
          
          &::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 2px;
          }
          
          &::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 2px;
            
            &:hover {
              background: #a8a8a8;
            }
          }
        }
      
      .action-card {
        height: 160px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s;
        
        &:hover {
          transform: translateY(-5px);
          box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .action-icon {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background-color: rgba($primary-color, 0.1);
          display: flex;
          justify-content: center;
          align-items: center;
          margin-bottom: 15px;
          
          .el-icon {
            font-size: 24px;
            color: $primary-color;
          }
        }
        
        .action-title {
          font-size: 16px;
          font-weight: bold;
          color: $text-primary;
          margin-bottom: 5px;
        }
        
        .action-desc {
          font-size: 13px;
          color: $text-secondary;
          text-align: center;
        }
      }
    }
    
    .publish-task-records {
      margin-top: 30px;
      
      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        
        h2 {
          font-size: 18px;
          color: $text-primary;
          margin: 0;
        }
      }
    }
  }
}
</style>