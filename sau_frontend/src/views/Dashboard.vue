<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>自媒体自动化运营系统</h1>
    </div>

    <div class="dashboard-content">
      <el-row :gutter="20">
        <!-- 账号统计卡片 -->
        <el-col :span="8">
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
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon platform-icon">
                <el-icon><Platform /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ platformStats.total }}</div>
                <div class="stat-label">已接入平台</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <el-tooltip content="快手账号" placement="top">
                  <el-tag size="small" type="success">{{ platformStats.kuaishou }}</el-tag>
                </el-tooltip>
                <el-tooltip content="抖音账号" placement="top">
                  <el-tag size="small" type="danger">{{ platformStats.douyin }}</el-tag>
                </el-tooltip>
                <el-tooltip content="视频号账号" placement="top">
                  <el-tag size="small" type="warning">{{ platformStats.channels }}</el-tag>
                </el-tooltip>
                <el-tooltip content="小红书账号" placement="top">
                  <el-tag size="small" type="info">{{ platformStats.xiaohongshu }}</el-tag>
                </el-tooltip>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 素材统计卡片 -->
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon content-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contentStats.total }}</div>
                <div class="stat-label">素材总数</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <span>视频: {{ contentStats.videos }}</span>
                <span>图片: {{ contentStats.images }}</span>
                <span>其他: {{ contentStats.others }}</span>
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
              <div class="action-title">素材管理</div>
              <div class="action-desc">上传和管理视频素材</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/publish-center')">
              <div class="action-icon">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="action-title">发布中心</div>
              <div class="action-desc">发布内容到各平台</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/about')">
              <div class="action-icon">
                <el-icon><DataAnalysis /></el-icon>
              </div>
              <div class="action-title">关于系统</div>
              <div class="action-desc">查看系统信息</div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 素材列表 -->
      <div class="recent-tasks">
        <div class="section-header">
          <h2>最近上传素材</h2>
          <el-button text @click="navigateTo('/material-management')">查看全部</el-button>
        </div>

        <el-table :data="recentMaterials" style="width: 100%" v-loading="loading">
          <el-table-column prop="filename" label="文件名" width="300" />
          <el-table-column prop="filesize" label="文件大小" width="120">
            <template #default="scope">
              {{ scope.row.filesize }} MB
            </template>
          </el-table-column>
          <el-table-column prop="upload_time" label="上传时间" width="200" />
          <el-table-column label="类型" width="100">
            <template #default="scope">
              <el-tag
                :type="getFileTypeTag(scope.row.filename)"
                effect="plain"
                size="small"
              >
                {{ getFileType(scope.row.filename) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && recentMaterials.length === 0" description="暂无素材数据" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  User, UserFilled, Platform, Document,
  Upload, Timer, DataAnalysis
} from '@element-plus/icons-vue'
import { accountApi } from '@/api/account'
import { materialApi } from '@/api/material'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const accountStore = useAccountStore()
const appStore = useAppStore()
const loading = ref(false)

// 账号统计数据 - 从真实数据计算
const accountStats = computed(() => {
  const accounts = accountStore.accounts
  const normal = accounts.filter(a => a.status === '正常').length
  const abnormal = accounts.filter(a => a.status !== '正常' && a.status !== '验证中').length
  return {
    total: accounts.length,
    normal,
    abnormal
  }
})

// 平台统计数据 - 从真实数据计算
const platformStats = computed(() => {
  const accounts = accountStore.accounts
  const kuaishou = accounts.filter(a => a.platform === '快手').length
  const douyin = accounts.filter(a => a.platform === '抖音').length
  const channels = accounts.filter(a => a.platform === '视频号').length
  const xiaohongshu = accounts.filter(a => a.platform === '小红书').length
  // 统计有账号的平台数量
  const total = [kuaishou, douyin, channels, xiaohongshu].filter(n => n > 0).length
  return { total, kuaishou, douyin, channels, xiaohongshu }
})

// 素材统计数据 - 从真实数据计算
const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

const contentStats = computed(() => {
  const materials = appStore.materials
  const videos = materials.filter(m => videoExtensions.some(ext => m.filename.toLowerCase().endsWith(ext))).length
  const images = materials.filter(m => imageExtensions.some(ext => m.filename.toLowerCase().endsWith(ext))).length
  return {
    total: materials.length,
    videos,
    images,
    others: materials.length - videos - images
  }
})

// 最近上传的素材（最多显示5条）
const recentMaterials = computed(() => {
  return [...appStore.materials]
    .sort((a, b) => new Date(b.upload_time) - new Date(a.upload_time))
    .slice(0, 5)
})

// 获取文件类型
const getFileType = (filename) => {
  if (videoExtensions.some(ext => filename.toLowerCase().endsWith(ext))) return '视频'
  if (imageExtensions.some(ext => filename.toLowerCase().endsWith(ext))) return '图片'
  return '其他'
}

// 获取文件类型标签颜色
const getFileTypeTag = (filename) => {
  const type = getFileType(filename)
  return { '视频': 'success', '图片': 'warning', '其他': 'info' }[type] || 'info'
}

// 导航到指定路由
const navigateTo = (path) => {
  router.push(path)
}

// 加载数据
const fetchDashboardData = async () => {
  loading.value = true
  try {
    // 并行获取账号和素材数据
    const [accountRes, materialRes] = await Promise.allSettled([
      accountApi.getAccounts(),
      materialApi.getAllMaterials()
    ])

    if (accountRes.status === 'fulfilled' && accountRes.value.code === 200) {
      accountStore.setAccounts(accountRes.value.data)
    }
    if (materialRes.status === 'fulfilled' && materialRes.value.code === 200) {
      appStore.setMaterials(materialRes.value.data)
    }
  } catch (error) {
    console.error('获取仪表盘数据失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
})
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

          .el-tag {
            margin-right: 5px;
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

    .recent-tasks {
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
