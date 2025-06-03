<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="logo">
        <img src="@/assets/logo.svg" alt="Logo" class="logo-img" />
        <span>SAU自媒体自动化运营系统</span>
      </div>
      <div class="header-tabs">
        <!-- <div class="tab-item" v-for="tab in tabs" :key="tab.id">{{ tab.name }}</div> -->
      </div>
      <!-- <div class="user-info">
        <button class="btn-upgrade" @click="showLoginModal">登录</button>
        <div class="avatar">
          <img src="@/assets/tudong.jpg" alt="Avatar" />
        </div>
      </div> -->
      <LoginModal :visible="isLoginModalVisible" @close="closeLoginModal" @login-success="handleLoginSuccess" />
    </header>
    
    <!-- 主体内容区 -->
    <div class="content-container">
      <!-- 左侧导航栏 -->
      <aside class="sidebar">
        <nav>
          <!-- 静态路由 -->
          <router-link 
            v-for="route in staticRoutes" 
            :key="route.path" 
            :to="route.path"
            class="nav-item"
            active-class="active"
          >
            <i :class="route.meta.icon"></i>
            <span>{{ route.meta.title }}</span>
          </router-link>
          
          <!-- 动态视频发布路由 -->
          <div 
            v-for="route in videoRoutes" 
            :key="route.id"
            class="nav-item-with-close"
          >
            <router-link 
              :to="`/video-publish/${route.id}`" 
              class="nav-item"
              active-class="active"
            >
              <i class="icon-video"></i>
              <span>{{ route.meta.title }}</span>
            </router-link>
            <button 
              class="close-btn" 
              @click="handleRemoveVideoRoute(route.id)"
              title="删除路由"
            >×</button>
          </div>
        </nav>
      </aside>
      
      <!-- 右侧内容区 -->
      <main class="main-content">
        <router-view></router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import LoginModal from '@/components/LoginModal.vue';
import { videoRoutes, removeVideoRoute } from '@/router';

const router = useRouter();

// 静态路由
const staticRoutes = computed(() => router.options.routes.filter(route => route.meta?.title));

// 动态视频发布路由已从router导入

// 监听视频路由变化，动态添加/删除路由
watch(videoRoutes, (newRoutes) => {
  // 确保路由已添加到router中
  newRoutes.forEach(route => {
    if (!router.hasRoute(route.name)) {
      router.addRoute(route);
    }
  });
}, { immediate: true });

// 删除视频发布路由
const handleRemoveVideoRoute = (id) => {
  const route = videoRoutes.value.find(r => r.id === id);
  if (route && router.currentRoute.value.path === route.path) {
    // 如果当前在要删除的路由页面，先跳转到其他页面
    router.push('/publish');
  }
  // 调用router中的removeVideoRoute函数
  removeVideoRoute(id);
};

// 登录模态窗口控制
const isLoginModalVisible = ref(false);

const showLoginModal = () => {
  isLoginModalVisible.value = true;
};

const closeLoginModal = () => {
  isLoginModalVisible.value = false;
};

const handleLoginSuccess = (userData) => {
  console.log('用户登录成功:', userData);
  // 这里可以添加登录成功后的逻辑，比如更新用户状态等
};

const tabs = [
  { id: 1, name: '抖音' },
  { id: 2, name: '小红书' },
  { id: 3, name: '微信视频号' },
  { id: 4, name: '快手' },
  { id: 5, name: '视频号小店' },
  { id: 6, name: 'TikTok' }
];
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #333;
  background-color: #f5f7fa;
}

.main-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.header {
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.logo {
  display: flex;
  align-items: center;
  font-weight: bold;
  font-size: 18px;
  margin-right: 40px;
}

.logo-img {
  width: 30px;
  height: 30px;
  margin-right: 10px;
}

.header-tabs {
  display: flex;
  flex: 1;
}

.tab-item {
  padding: 0 15px;
  cursor: pointer;
  height: 60px;
  display: flex;
  align-items: center;
}

.tab-item:hover {
  color: #4e6ef2;
}

.user-info {
  display: flex;
  align-items: center;
}

.btn-upgrade {
  background-color: #f0f2ff;
  color: #4e6ef2;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  margin-right: 15px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.btn-upgrade:hover {
  background-color: #e0e5ff;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.content-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  background-color: #f8f9fc;
  border-right: 1px solid #eee;
  padding: 20px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: #333;
  text-decoration: none;
  margin-bottom: 5px;
}

.nav-item i {
  margin-right: 10px;
  font-size: 18px;
}

/* 图标样式 */
.icon-account, .icon-publish, .icon-website, .icon-data, .icon-video, .icon-multi-publish, .icon-material {
  display: inline-block;
  width: 18px;
  height: 18px;
  position: relative;
}

.icon-multi-publish::before {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  background-color: #8b5cf6;
  border-radius: 50%;
  top: 3px;
  left: 3px;
}

.icon-material::before {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  background-color: #10b981;
  border-radius: 50%;
  top: 3px;
  left: 3px;
}

.nav-item.active {
  background-color: #e6f7ff;
  color: #4e6ef2;
  border-right: 3px solid #4e6ef2;
}

/* 带关闭按钮的导航项 */
.nav-item-with-close {
  position: relative;
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.nav-item-with-close .nav-item {
  flex: 1;
  margin-bottom: 0;
}

.close-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: #999;
  font-size: 16px;
  cursor: pointer;
  display: none;
  width: 20px;
  height: 20px;
  line-height: 18px;
  text-align: center;
  border-radius: 50%;
}

.close-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
  color: #666;
}

.nav-item-with-close:hover .close-btn {
  display: block;
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
</style>
