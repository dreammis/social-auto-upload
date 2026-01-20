<template>
  <div class="home">
    <div class="welcome-section">
      <h1>欢迎使用 Vue3 + Vite 项目</h1>
      <p>这是一个集成了 Vue3、Vite、Element Plus、Pinia、Vue Router 和 Axios 的现代化前端项目</p>
      
      <!-- 快捷操作区域 -->
      <div class="quick-actions">
        <h2>快捷操作</h2>
        <div class="features">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card class="feature-card quick-action-card" @click="goToMaterialManagement">
                <template #header>
                  <div class="card-header">
                    <el-icon><Upload /></el-icon>
                    <span>内容上传</span>
                  </div>
                </template>
                <p>上传和管理视频素材，支持多平台发布</p>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="feature-card quick-action-card" @click="goToPublishCenter">
                <template #header>
                  <div class="card-header">
                    <el-icon><Clock /></el-icon>
                    <span>定时发布</span>
                  </div>
                </template>
                <p>设置定时发布计划，自动发布视频内容</p>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="feature-card quick-action-card" @click="goToDataAnalysis">
                <template #header>
                  <div class="card-header">
                    <el-icon><DataAnalysis /></el-icon>
                    <span>数据分析</span>
                  </div>
                </template>
                <p>查看发布数据统计和分析报告</p>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </div>
      
      <div class="features">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card class="feature-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Lightning /></el-icon>
                  <span>快速开发</span>
                </div>
              </template>
              <p>基于 Vite 构建，提供极速的开发体验</p>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="feature-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Star /></el-icon>
                  <span>现代化</span>
                </div>
              </template>
              <p>使用 Vue3 Composition API 和 setup 语法</p>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card class="feature-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Setting /></el-icon>
                  <span>完整配置</span>
                </div>
              </template>
              <p>集成路由、状态管理、HTTP请求等完整解决方案</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
    
    <div class="demo-section">
      <HelloWorld msg="Vue3 + Vite + Element Plus" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import HelloWorld from '../components/HelloWorld.vue'
import { Lightning, Star, Setting, Upload, Clock, DataAnalysis } from '@element-plus/icons-vue'

const router = useRouter()

// 跳转到素材管理页面
const goToMaterialManagement = () => {
  router.push('/material-management')
}

// 跳转到发布中心页面
const goToPublishCenter = () => {
  router.push('/publish-center')
}

// 跳转到数据分析页面
const goToDataAnalysis = () => {
  router.push('/data')
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.home {
  .welcome-section {
    text-align: center;
    margin-bottom: 3rem;
    
    h1 {
      color: #2c3e50;
      margin-bottom: 1rem;
      font-size: 2.5rem;
    }
    
    h2 {
      color: #2c3e50;
      margin-bottom: 1.5rem;
      font-size: 2rem;
    }
    
    p {
      color: #7f8c8d;
      font-size: 1.2rem;
      margin-bottom: 2rem;
    }
    
    .quick-actions {
      margin-bottom: 3rem;
    }
    
    .features {
      margin-top: 2rem;
      
      .feature-card {
        height: 200px;
        
        .card-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: bold;
          
          .el-icon {
            color: #409eff;
          }
        }
        
        p {
          color: #666;
          font-size: 1rem;
          line-height: 1.6;
        }
      }
      
      .quick-action-card {
        cursor: pointer;
        transition: all 0.3s ease;
        
        &:hover {
          transform: translateY(-5px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
          
          .card-header .el-icon {
            color: #67c23a;
          }
        }
        
        &:active {
          transform: translateY(-2px);
        }
      }
    }
  }
  
  .demo-section {
    margin-top: 3rem;
  }
}
</style>