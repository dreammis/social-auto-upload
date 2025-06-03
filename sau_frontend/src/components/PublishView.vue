<template>
  <div class="publish-view">
    <h1>发布记录</h1>
    
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-items">
        <div class="filter-item">
          <select class="filter-select" v-model="selectedPublisher">
            <option value="">全部发布人</option>
            <option v-for="account in accountsList" :key="account.id" :value="account.id">
              {{ account.name }}
            </option>
          </select>
        </div>
        
        <div class="filter-item">
          <select class="filter-select">
            <option value="">全部发布类型</option>
            <option value="video">视频</option>
            <option value="image">图文</option>
          </select>
        </div>
        
        <!-- <div class="filter-item">
          <select class="filter-select">
            <option value="">全部推送状态</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
            <option value="pending">待发布</option>
          </select>
        </div> -->
      </div>
      
      <div class="action-buttons">

        
        <!-- 新增发布按钮及下拉菜单 -->
        <div class="dropdown" 
             @mouseenter="showDropdown" 
             @mouseleave="hideDropdown">
          <button class="btn btn-add">
            <i class="add-icon">+</i> 新增发布
          </button>
          <div class="dropdown-menu" :class="{ 'show': dropdownVisible }">
            <div class="dropdown-item" @click="addVideoPublishRoute">
              <div class="item-icon video-icon"></div>
              <span>视频</span>
            </div>
            <div class="dropdown-item">
              <div class="item-icon image-icon"></div>
              <span>图文</span>
            </div>
            <div class="dropdown-item" @click="goToMultiPublish">
              <div class="item-icon multi-icon"></div>
              <span>多平台发布</span>
            </div>
            <!-- <div class="dropdown-item">
              <div class="item-icon article-icon"></div>
              <span>文章</span>
            </div>
            <div class="dropdown-item">
              <div class="item-icon wechat-icon"></div>
              <span>公众号</span>
            </div> -->
          </div>
        </div>
      </div>
    </div>
    
    <!-- 空状态提示 -->
    <div class="empty-state">
      <div class="empty-image"></div>
      <p class="empty-text">暂无发布记录，点击新增发布任务吧～</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { addVideoRoute } from '@/router';
import { globalAccountsCache } from '../config';
import axios from 'axios';
import tx from '@assets/fengbaobao.png'

const router = useRouter();

// 控制下拉菜单的显示状态
const dropdownVisible = ref(false);

// 选中的发布人
const selectedPublisher = ref('');

// 账号列表
const accountsList = ref([]);

// 显示下拉菜单
const showDropdown = () => {
  dropdownVisible.value = true;
};

// 隐藏下拉菜单
const hideDropdown = () => {
  dropdownVisible.value = false;
};

// 添加视频发布路由
const addVideoPublishRoute = () => {
  const newRoute = addVideoRoute();
  router.push(newRoute.path);
  hideDropdown();
};

// 跳转到多平台发布页面
const goToMultiPublish = () => {
  router.push('/multi-publish');
  hideDropdown();
};

// 获取账号列表
const fetchAccounts = async () => {
  try {
    // 如果全局缓存有效，则使用缓存数据
    if (globalAccountsCache.isValid()) {
      processAccountsData(globalAccountsCache.accounts);
      return;
    }
    
    // 否则从API获取数据
    const response = await axios.get(`/api/getValidAccounts`);
    if (response.data.code === 200 && response.data.data) {
      // 更新全局缓存
      globalAccountsCache.updateCache(response.data.data);
      // 处理账号数据
      processAccountsData(response.data.data);
    }
  } catch (error) {
    console.error('获取账号列表失败:', error);
    accountsList.value = [];
  }
};

// 处理账号数据
const processAccountsData = (data) => {
  // 提取所有账号的昵称信息
  accountsList.value = data.map(account => ({
    id: account[0] || Math.random().toString(36).substr(2, 9),
    name: account[3] || '未命名账号',
    type: account[1]
    
  }));
};

// 组件挂载时获取账号列表
onMounted(() => {
  fetchAccounts();
});

</script>

<style scoped>
.publish-view {
  padding: 20px;
}

h1 {
  margin-bottom: 20px;
  font-size: 24px;
  font-weight: 500;
}

/* 筛选栏样式 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.filter-items {
  display: flex;
  gap: 15px;
}

.filter-select {
  padding: 8px 15px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #fff;
  min-width: 150px;
  font-size: 14px;
  outline: none;
}

/* 按钮样式 */
.action-buttons {
  display: flex;
  gap: 15px;
}

.btn {
  padding: 8px 15px;
  border-radius: 4px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-export, .btn-delete {
  background-color: #fff;
  border: 1px solid #e0e0e0;
}

.btn-add {
  background-color: #6366f1;
  color: white;
  position: relative;
}

.add-icon {
  margin-right: 5px;
  font-size: 16px;
}

/* 下拉菜单样式 */
.dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  width: 200px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-top: 5px;
  z-index: 10;
  overflow: hidden;
  display: none;
  padding-top: 5px; /* 添加顶部内边距 */
}

/* 添加一个看不见的连接区域 */
.dropdown::after {
  content: '';
  position: absolute;
  height: 10px;
  width: 100%;
  bottom: -10px;
  left: 0;
}

.dropdown-menu.show {
  display: block;
}

.dropdown-item {
  padding: 12px 15px;
  display: flex;
  align-items: center;
  cursor: pointer;
}

.dropdown-item:hover {
  background-color: #f5f5f5;
}

.item-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  margin-right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-icon {
  background-color: #e0f2fe;
  position: relative;
}

.video-icon::before {
  content: '';
  width: 10px;
  height: 10px;
  background-color: #0ea5e9;
  border-radius: 50%;
}

.image-icon {
  background-color: #dcfce7;
  position: relative;
}

.image-icon::before {
  content: '';
  width: 10px;
  height: 10px;
  background-color: #22c55e;
  border-radius: 50%;
}

.multi-icon {
  background-color: #f0e7fe;
  position: relative;
}

.multi-icon::before {
  content: '';
  width: 10px;
  height: 10px;
  background-color: #8b5cf6;
  border-radius: 50%;
}

.article-icon {
  background-color: #fef2f2;
  position: relative;
}

.article-icon::before {
  content: '';
  width: 10px;
  height: 10px;
  background-color: #ef4444;
  border-radius: 50%;
}

.wechat-icon {
  background-color: #ecfdf5;
  position: relative;
}

.wechat-icon::before {
  content: '';
  width: 10px;
  height: 10px;
  background-color: #10b981;
  border-radius: 50%;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  background-color: #fff;
  border-radius: 8px;
  margin-top: 20px;
}

.empty-image {
  width: 120px;
  height: 120px;
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23d1d5db" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>');
  background-repeat: no-repeat;
  background-position: center;
  background-size: contain;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-text {
  color: #9ca3af;
  font-size: 14px;
}
</style>