<template>
  <div class="data-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">数据分析</span>
          <el-button type="primary" @click="refreshData">
            <el-icon><Refresh /></el-icon>刷新数据
          </el-button>
        </div>
      </template>
      
      <div class="data-content">
        <!-- 数据概览 -->
        <div class="data-overview">
          <el-row :gutter="20">
            <el-col :span="6">
              <el-card shadow="hover" class="overview-card">
                <div class="overview-item">
                  <div class="overview-label">总播放量</div>
                  <div class="overview-value">{{ totalPlays.toLocaleString() }}</div>
                  <div class="overview-change" :class="{ positive: playsGrowth > 0, negative: playsGrowth < 0 }">
                    {{ playsGrowth > 0 ? '+' : '' }}{{ playsGrowth }}%
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="overview-card">
                <div class="overview-item">
                  <div class="overview-label">总点赞数</div>
                  <div class="overview-value">{{ totalLikes.toLocaleString() }}</div>
                  <div class="overview-change" :class="{ positive: likesGrowth > 0, negative: likesGrowth < 0 }">
                    {{ likesGrowth > 0 ? '+' : '' }}{{ likesGrowth }}%
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="overview-card">
                <div class="overview-item">
                  <div class="overview-label">总评论数</div>
                  <div class="overview-value">{{ totalComments.toLocaleString() }}</div>
                  <div class="overview-change" :class="{ positive: commentsGrowth > 0, negative: commentsGrowth < 0 }">
                    {{ commentsGrowth > 0 ? '+' : '' }}{{ commentsGrowth }}%
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="overview-card">
                <div class="overview-item">
                  <div class="overview-label">总粉丝数</div>
                  <div class="overview-value">{{ totalFollowers.toLocaleString() }}</div>
                  <div class="overview-change" :class="{ positive: followersGrowth > 0, negative: followersGrowth < 0 }">
                    {{ followersGrowth > 0 ? '+' : '' }}{{ followersGrowth }}%
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
        
        <!-- 平台选择 -->
        <div class="platform-selector" style="margin-top: 20px;">
          <el-select v-model="selectedPlatform" placeholder="选择平台" style="width: 200px;">
            <el-option label="全部平台" value="all"></el-option>
            <el-option label="抖音" value="douyin"></el-option>
            <el-option label="快手" value="kuaishou"></el-option>
            <el-option label="视频号" value="wechat"></el-option>
            <el-option label="小红书" value="xiaohongshu"></el-option>
            <el-option label="TikTok" value="tiktok"></el-option>
          </el-select>
        </div>
        
        <!-- 数据表格 -->
        <div class="data-table" style="margin-top: 20px;">
          <el-table :data="filteredData" style="width: 100%">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="platform" label="平台" width="100" />
            <el-table-column prop="plays" label="播放量">
              <template #default="scope">
                <span>{{ scope.row.plays.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="likes" label="点赞数">
              <template #default="scope">
                <span>{{ scope.row.likes.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="comments" label="评论数">
              <template #default="scope">
                <span>{{ scope.row.comments.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="followers" label="新增粉丝">
              <template #default="scope">
                <span>{{ scope.row.followers.toLocaleString() }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

// 概览数据
const totalPlays = ref(1258000)
const totalLikes = ref(48600)
const totalComments = ref(3200)
const totalFollowers = ref(15200)

// 增长率
const playsGrowth = ref(12.5)
const likesGrowth = ref(8.3)
const commentsGrowth = ref(5.7)
const followersGrowth = ref(15.2)

// 选中的平台
const selectedPlatform = ref('all')

// 模拟数据
const dataList = ref([
  { date: '2024-01-01', platform: '抖音', plays: 89000, likes: 3200, comments: 210, followers: 1200 },
  { date: '2024-01-01', platform: '快手', plays: 65000, likes: 2100, comments: 150, followers: 800 },
  { date: '2024-01-01', platform: '视频号', plays: 45000, likes: 1800, comments: 120, followers: 600 },
  { date: '2024-01-01', platform: '小红书', plays: 38000, likes: 2500, comments: 180, followers: 500 },
  { date: '2024-01-01', platform: 'TikTok', plays: 123000, likes: 4500, comments: 320, followers: 1500 },
  { date: '2024-01-02', platform: '抖音', plays: 92000, likes: 3400, comments: 230, followers: 1300 },
  { date: '2024-01-02', platform: '快手', plays: 68000, likes: 2300, comments: 160, followers: 850 },
  { date: '2024-01-02', platform: '视频号', plays: 48000, likes: 1900, comments: 130, followers: 650 },
  { date: '2024-01-02', platform: '小红书', plays: 41000, likes: 2700, comments: 190, followers: 550 },
  { date: '2024-01-02', platform: 'TikTok', plays: 128000, likes: 4700, comments: 340, followers: 1600 }
])

// 过滤数据
const filteredData = computed(() => {
  if (selectedPlatform.value === 'all') {
    return dataList.value
  }
  return dataList.value.filter(item => {
    const platformMap = {
      'douyin': '抖音',
      'kuaishou': '快手',
      'wechat': '视频号',
      'xiaohongshu': '小红书',
      'tiktok': 'TikTok'
    }
    return item.platform === platformMap[selectedPlatform.value]
  })
})

// 刷新数据
const refreshData = () => {
  console.log('刷新数据分析')
  // 这里可以添加实际的数据刷新逻辑
}
</script>

<style scoped>
.data-container {
  padding: 20px;
}

.page-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  
  .card-title {
    flex: 1;
  }
  
  /* 刷新数据按钮*/
  .el-button--primary {
    background-color: #1C9399 !important;
    border-color: #1C9399 !important;
    color: #FFFFFF !important;
    margin-left: auto;
    
    &:hover {
      background-color: #48D1CC !important;
      border-color: #48D1CC !important;
      color: #FFFFFF !important;
    }
    
    &:active {
      background-color: #166B6F !important;
      border-color: #166B6F !important;
      color: #FFFFFF !important;
    }
  }
}

.data-content {
  margin-top: 20px;
}

.data-overview {
  margin-bottom: 20px;
}

.overview-card {
  height: 100%;
}

.overview-item {
  text-align: center;
  padding: 10px 0;
}

.overview-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
}

.overview-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.overview-change {
  font-size: 12px;
}

.overview-change.positive {
  color: #67c23a;
}

.overview-change.negative {
  color: #f56c6c;
}

.platform-selector {
  margin: 20px 0;
}

.data-table {
  margin-top: 20px;
}
</style>