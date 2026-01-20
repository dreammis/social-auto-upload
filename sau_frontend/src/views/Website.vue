<template>
  <div class="website-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span>网站管理</span>
        </div>
      </template>
      
      <div class="website-content">
        <!-- <el-descriptions :column="1" border>
          <el-descriptions-item label="功能说明">
            网站管理模块用于配置和管理各个平台的网站设置。
          </el-descriptions-item>
        </el-descriptions>
        
        <el-divider>平台配置</el-divider> -->
        
        <!-- 使用通用table组件 -->
        <Table
          :columns="tableColumns"
          :data="websiteData"
          :model-value="pagination"
          :total="total"
          :show-index="true"
          @clear="handleSearch"
        >
          <!-- 状态列自定义插槽 -->
          <template #status="{ data }">
            <el-tag :type="data.status === 'active' ? 'success' : 'danger'">
              {{ data.status === 'active' ? '活跃' : '未激活' }}
            </el-tag>
          </template>
          
          <!-- 操作列自定义插槽 -->
          <template #operation="{ data }">
            <div class="action-buttons">
              <el-button size="small" type="primary" @click="editWebsite(data)">编辑</el-button>
              <el-button size="small" :type="data.status === 'active' ? 'danger' : 'success'" 
                @click="toggleStatus(data)">
                {{ data.status === 'active' ? '停用' : '启用' }}
              </el-button>
            </div>
          </template>
        </Table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import Table from '@/components/table.vue'

// 分页配置
const pagination = reactive({
  pageNum: 1,
  pageSize: 10
})

// 总数
const total = ref(7)

// 表格列配置
const tableColumns = ref([
  {
    key: 'platform',
    title: '平台',
    // width: 120,
    align: 'center'
  },
  {
    key: 'url',
    title: '网站地址',
    // width: 100,
    align: 'center'
  },
  {
    key: 'status',
    title: '状态',
    // width: 100,
    align: 'center',
    slots: 'status'  // 使用自定义插槽
  },
  {
    key: 'operation',
    title: '操作',
    // width: 150,
    align: 'center',
    fixed: 'right',
    slots: 'operation'  // 使用自定义插槽
  }
])

// 网站数据
const websiteData = ref([
  {
    platform: '抖音',
    url: 'https://www.douyin.com',
    status: 'active'
  },
  {
    platform: '快手',
    url: 'https://www.kuaishou.com',
    status: 'active'
  },
  {
    platform: '视频号',
    url: 'https://channels.weixin.qq.com',
    status: 'active'
  },
  {
    platform: '小红书',
    url: 'https://www.xiaohongshu.com',
    status: 'active'
  },
  {
    platform: 'TikTok',
    url: 'https://www.tiktok.com',
    status: 'active'
  },
  {
    platform: 'Instagram',
    url: 'https://www.instagram.com',
    status: 'active'
  },
  {
    platform: 'Facebook',
    url: 'https://www.facebook.com',
    status: 'active'
  }
])

// 搜索/刷新数据
const handleSearch = (params) => {
  console.log('搜索参数:', params)
  // 这里可以添加实际的搜索逻辑
}

// 编辑网站配置
const editWebsite = (row) => {
  console.log('编辑网站配置:', row)
}

// 切换状态
const toggleStatus = (row) => {
  row.status = row.status === 'active' ? 'inactive' : 'active'
}
</script>

<style scoped>
.website-container {
  padding: 20px;
}

.page-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.website-content {
  margin-top: 20px;
}

/* 操作按钮横向排列 */
.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
}

/* 确保按钮在小屏幕上也能正常显示 */
.action-buttons .el-button {
  flex-shrink: 0;
}
</style>