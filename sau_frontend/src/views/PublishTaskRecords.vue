<template>
  <div class="publish-task-records">
    <div class="page-header">
      <h1>任务发布记录</h1>
    </div>
    
    <div class="search-filter">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-input
            v-model="searchKeyword"
            placeholder="输入文件名搜索"
            prefix-icon="Search"
            clearable
            @clear="handleSearch"
            @input="handleSearch"
          />
        </el-col>
        <el-col :span="4">
          <el-select
            v-model="filterPlatform"
            placeholder="选择平台"
            clearable
            @change="handleSearch"
          >
            <el-option
              v-for="platform in platforms"
              :key="platform.value"
              :label="platform.label"
              :value="platform.value"
            />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select
            v-model="filterStatus"
            placeholder="选择状态"
            clearable
            @change="handleSearch"
          >
            <el-option
              v-for="status in statuses"
              :key="status.value"
              :label="status.label"
              :value="status.label"
            />
          </el-select>
        </el-col>
        <el-col :span="2">
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
        </el-col>
        <el-col :span="2">
          <el-button @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-col>
      </el-row>
    </div>
    
    <div class="task-records-table">
      <el-table :data="filteredRecords" style="width: 100%" v-loading="loading">
        <el-table-column prop="fileName" label="文件名" width="200" />
        <el-table-column prop="platformName" label="平台" width="120">
          <template #default="scope">
            <el-tag
              :type="getPlatformTagType(getDisplayPlatformName(scope.row.platformName))"
              effect="plain"
            >
              {{ getDisplayPlatformName(scope.row.platformName) }}
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
        <el-table-column prop="updateTime" label="更新时间" width="180" />
        <el-table-column label="操作" width="350">
          <template #default="scope">
            <el-button size="small" @click="viewTaskDetail(scope.row)">查看详情</el-button>
            <el-button 
              size="small" 
              type="warning" 
              @click="deletePublishTask(scope.row)"
            >
              删除
            </el-button>
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
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalRecords"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { publishApi } from '@/api/publish'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'

// 平台映射：平台类型 -> 平台名称
const platformTypeMap = {
  1: '小红书',
  2: '视频号',
  3: '抖音',
  4: '快手',
  5: 'TikTok',
  6: 'Instagram',
  7: 'Facebook',
  8: '哔哩哔哩',
  9: '百家号'
}

// 平台名称映射：平台key -> 平台名称
const platformNameMap = {
  'douyin': '抖音',
  'kuaishou': '快手',
  'xiaohongshu': '小红书',
  'tencent': '视频号',
  'tiktok': 'TikTok',
  'instagram': 'Instagram',
  'facebook': 'Facebook',
  'bilibili': '哔哩哔哩',
  'baijiahao': '百家号'
}

// 平台列表
const platforms = [
  { label: '抖音', value: 3 },
  { label: '快手', value: 4 },
  { label: '小红书', value: 1 },
  { label: '视频号', value: 2 },
  { label: 'TikTok', value: 5 },
  { label: 'Instagram', value: 6 },
  { label: 'Facebook', value: 7 },
  { label: '哔哩哔哩', value: 8 },
  { label: '百家号', value: 9 }
]

// 状态列表
const statuses = [
  { label: '待发布', value: '待发布' },
  { label: '发布中', value: '发布中' },
  { label: '发布成功', value: '发布成功' },
  { label: '发布失败', value: '发布失败' },
  { label: '已取消', value: '已取消' }
]

// 搜索和筛选条件
const searchKeyword = ref('')
const filterPlatform = ref('')
const filterStatus = ref('')

// 分页参数
const currentPage = ref(1)
const pageSize = ref(10)
const totalRecords = ref(0)
const loading = ref(false)

// 发布任务记录数据
const publishTaskRecords = ref([])

// 计算过滤后的记录
const filteredRecords = computed(() => {
  let records = publishTaskRecords.value || []
  
  // 根据搜索关键词过滤
  if (searchKeyword.value) {
    records = records.filter(record => 
      record.fileName.includes(searchKeyword.value)
    )
  }
  
  // 根据平台类型过滤
  if (filterPlatform.value) {
    records = records.filter(record => 
      record.platformType === filterPlatform.value
    )
  }
  
  // 根据状态过滤
  if (filterStatus.value) {
    records = records.filter(record => 
      record.status === filterStatus.value
    )
  }
  
  totalRecords.value = records.length
  return records
})

// 获取发布任务记录
async function fetchPublishTaskRecords() {
  loading.value = true
  try {
    const response = await publishApi.getPublishTaskRecords({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const data = response
    
    if (data.code === 200) {
      publishTaskRecords.value = data.data.records || []
      totalRecords.value = data.data.total || 0
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
      { id: '6', fileName: '视频2.mp4', platformName: '快手', accountName: '快手1账号', status: '发布成功', createTime: '2026-01-14 11:30:00', updateTime: '2026-01-14 11:35:00' },
      { id: '7', fileName: '视频3.mp4', platformName: '小红书', accountName: '小红书1账号', status: '发布成功', createTime: '2026-01-14 12:00:00', updateTime: '2026-01-14 12:05:00' },
      { id: '8', fileName: '视频3.mp4', platformName: '视频号', accountName: '视频号1账号', status: '发布失败', createTime: '2026-01-14 12:15:00', updateTime: '2026-01-14 12:18:00' },
      { id: '9', fileName: '视频4.mp4', platformName: 'TikTok', accountName: 'TikTok1账号', status: '发布中', createTime: '2026-01-14 13:00:00', updateTime: '2026-01-14 13:02:00' },
      { id: '10', fileName: '视频4.mp4', platformName: 'Instagram', accountName: 'Instagram1账号', status: '发布成功', createTime: '2026-01-14 13:30:00', updateTime: '2026-01-14 13:35:00' }
    ]
    totalRecords.value = publishTaskRecords.value.length
  } finally {
    loading.value = false
  }
}

// 根据平台获取标签类型，与账号管理页面保持一致
const getPlatformTagType = (platform) => {
  const typeMap = {
    '快手': 'primary',
    '抖音': 'primary',
    '视频号': 'primary',
    '小红书': 'primary',
    'TikTok': 'danger',
    'Instagram': 'danger',
    'Facebook': 'danger',
    '哔哩哔哩': 'primary',
    '百家号': 'primary',
    '未知': 'default'
  }
  return typeMap[platform] || 'default'
}

// 获取显示的平台名称
const getDisplayPlatformName = (platformName) => {
  // 如果已经是中文名称，直接返回
  if (['抖音', '快手', '小红书', '视频号', 'TikTok', 'Instagram', 'Facebook', '哔哩哔哩', '百家号'].includes(platformName)) {
    return platformName
  }
  // 否则根据平台key获取中文名称
  return platformNameMap[platformName] || platformName
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

// 查看发布任务详情
const viewTaskDetail = (task) => {
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
    .then(async () => {
      try {
        // 调用后端API重试发布任务
        const response = await publishApi.retryPublishTask(task.id)
        if (response.code === 200) {
          // 更新任务状态
          const index = publishTaskRecords.value.findIndex(t => t.id === task.id)
          if (index !== -1) {
            publishTaskRecords.value[index].status = '发布中'
            publishTaskRecords.value[index].updateTime = new Date().toLocaleString()
          }
          ElMessage({
            type: 'success',
            message: '发布任务已开始重试',
          })
        } else {
          ElMessage({
            type: 'error',
            message: response.msg || '重试发布任务失败',
          })
        }
      } catch (error) {
        console.error('重试发布任务失败:', error)
        ElMessage({
          type: 'error',
          message: '重试发布任务失败',
        })
      }
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
    .then(async () => {
      try {
        // 调用后端API取消任务
        const response = await publishApi.cancelPublishTask(task.id)
        if (response.code === 200) {
          // 更新本地任务状态
          const index = publishTaskRecords.value.findIndex(t => t.id === task.id)
          if (index !== -1) {
            publishTaskRecords.value[index].status = '已取消'
            publishTaskRecords.value[index].updateTime = new Date().toLocaleString()
          }
          ElMessage({
            type: 'success',
            message: '发布任务已取消',
          })
        } else {
          ElMessage({
            type: 'error',
            message: response.msg || '取消任务失败',
          })
        }
      } catch (error) {
        console.error('取消任务失败:', error)
        ElMessage({
          type: 'error',
          message: '取消任务失败',
        })
      }
    })
    .catch(() => {
      // 取消操作
    })
}

// 删除发布任务记录
const deletePublishTask = (task) => {
  ElMessageBox.confirm(
    `确定要删除这条发布任务记录吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        // 调用后端API删除任务
        const response = await publishApi.deletePublishTask(task.id)
        if (response.code === 200) {
          // 从本地列表中移除删除的任务
          const index = publishTaskRecords.value.findIndex(t => t.id === task.id)
          if (index !== -1) {
            publishTaskRecords.value.splice(index, 1)
          }
          ElMessage({
            type: 'success',
            message: '发布任务记录已删除',
          })
        } else {
          ElMessage({
            type: 'error',
            message: response.msg || '删除任务记录失败',
          })
        }
      } catch (error) {
        console.error('删除任务记录失败:', error)
        ElMessage({
          type: 'error',
          message: '删除任务记录失败',
        })
      }
    })
    .catch(() => {
      // 取消操作
    })
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  // 这里可以添加实际的搜索逻辑
}

// 刷新
const handleRefresh = () => {
  fetchPublishTaskRecords()
}

// 分页大小变化
const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
}

// 当前页变化
const handleCurrentChange = (page) => {
  currentPage.value = page
}

// 组件挂载时获取数据
onMounted(() => {
  fetchPublishTaskRecords()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.publish-task-records {
  .page-header {
    margin-bottom: 20px;
    
    h1 {
      font-size: 24px;
      color: $text-primary;
      margin: 0;
    }
  }
  
  .search-filter {
    margin-bottom: 20px;
  }
  
  .task-records-table {
    .pagination {
      margin-top: 20px;
      text-align: right;
    }
    
    // 确保操作按钮在同一行显示
    .el-button {
      margin-right: 8px;
    }
    
    .el-table__cell {
      white-space: nowrap;
    }
  }
}
</style>