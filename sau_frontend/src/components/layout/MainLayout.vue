<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="logo">
        <img src="@/assets/favicon.ico" alt="Logo" class="logo-img" />
        <span>呃呃呃呃呃</span>
      </div>
      <div class="header-tabs">
        <div class="tab-item" v-for="tab in tabs" :key="tab.id">{{ tab.name }}</div>
      </div>
      <div class="user-info">
        <button class="btn-upgrade">联系客服</button>
        <div class="avatar">
          <img src="@/assets/tudong.jpg" alt="Avatar" />
        </div>
      </div>
    </header>
    
    <!-- 主体内容区 -->
    <div class="content-container">
      <!-- 修改后的左侧导航栏 -->
      <aside class="sidebar">
        <nav>
          <router-link 
            v-for="route in routes" 
            :key="route.path" 
            :to="route.path"
            class="nav-item"
            active-class="active"
          >
            <i :class="route.meta.icon"></i>
            <span>{{ route.meta.title }}</span>
          </router-link>
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
import { computed, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
// 修改后的响应式路由列表
const routes = computed(() => {
  return router.getRoutes()
    .filter(route => 
      route.meta?.title &&        // 必须有标题
      !route.meta.hidden &&       // 过滤隐藏路由
      route.path !== '/' &&       // 排除根重定向
      !route.redirect            // 排除其他重定向路由
    )
    .sort((a, b) => {            // 保持路由顺序稳定
      const order = ['/account', '/publish', '/website', '/data'];
      return order.indexOf(a.path) - order.indexOf(b.path);
    });
});
const filteredRoutes = computed(() => routes.value.filter(route => route.path !== '/video-publish'));

// 控制视频发布路由的显示
const showVideoPublishRoute = ref(false);

// 在组件挂载时检查本地存储
onMounted(() => {
  const shouldShow = localStorage.getItem('showVideoPublishRoute');
  if (shouldShow === 'true') {
    showVideoPublishRoute.value = true;
  }
});

// 移除视频发布路由
const removeVideoPublishRoute = () => {
  showVideoPublishRoute.value = false;
  localStorage.removeItem('showVideoPublishRoute');
  
  // 如果当前在视频发布页面，则导航到发布中心
  if (router.currentRoute.value.path === '/video-publish') {
    router.push('/publish');
  }
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

<style scoped>
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

.nav-item.active {
  background-color: #e6f7ff;
  color: #4e6ef2;
  border-right: 3px solid #4e6ef2;
}

.nav-divider {
  height: 1px;
  background-color: #e0e0e0;
  margin: 10px 20px;
}

.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.nav-item-with-close {
  position: relative;
  display: flex;
  align-items: center;
}

.close-btn {
  position: absolute;
  right: 10px;
  background: none;
  border: none;
  color: #999;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}
</style>