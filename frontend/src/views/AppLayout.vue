<template>
  <div class="layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">SocialFlow AI</div>

      <nav class="sidebar-nav">
        <router-link to="/app/dashboard" class="nav-item" active-class="nav-item--active">
          <span class="nav-icon">📊</span>
          Dashboard
        </router-link>
        <router-link to="/app/accounts" class="nav-item" active-class="nav-item--active">
          <span class="nav-icon">👤</span>
          Accounts
        </router-link>
        <router-link to="/app/trends" class="nav-item" active-class="nav-item--active">
          <span class="nav-icon">🔥</span>
          Trends
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info" v-if="authStore.user">
          <span class="user-avatar">{{ authStore.user.displayName?.charAt(0)?.toUpperCase() }}</span>
          <span class="user-name">{{ authStore.user.displayName }}</span>
        </div>
        <button class="btn-logout" @click="handleLogout">Logout</button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store';

const router = useRouter();
const authStore = useAuthStore();

function handleLogout() {
  authStore.logout();
  router.push('/login');
}
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  background: #0f172a;
}

/* Sidebar */
.sidebar {
  width: 240px;
  background: rgba(15, 23, 42, 0.95);
  border-right: 1px solid rgba(148, 163, 184, 0.08);
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  flex-shrink: 0;
}

.sidebar-brand {
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  padding: 0 24px 24px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
  margin-bottom: 8px;
}

.sidebar-nav {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s;
}

.nav-item:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #e2e8f0;
}

.nav-item--active {
  background: rgba(59, 130, 246, 0.12);
  color: #3b82f6;
}

.nav-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
}

/* Sidebar footer */
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.user-name {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-logout {
  width: 100%;
  padding: 8px;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
  color: #fca5a5;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.btn-logout:hover {
  background: rgba(239, 68, 68, 0.15);
}

/* Main */
.main {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}
</style>
