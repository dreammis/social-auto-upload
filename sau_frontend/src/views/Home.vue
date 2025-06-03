<template>
  <div class="home">
    <div class="welcome-section">
      <h1>欢迎使用 Vue3 + Vite 项目</h1>
      <p>这是一个集成了 Vue3、Vite、Element Plus、Pinia、Vue Router 和 Axios 的现代化前端项目</p>
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
import HelloWorld from '../components/HelloWorld.vue'
import { Lightning, Star, Setting } from '@element-plus/icons-vue'
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
    
    p {
      color: #7f8c8d;
      font-size: 1.2rem;
      margin-bottom: 2rem;
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
    }
  }
  
  .demo-section {
    margin-top: 3rem;
  }
}
</style>