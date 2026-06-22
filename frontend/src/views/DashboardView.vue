<template>
  <div class="dashboard-page">
    <div class="card">
      <h2>Dashboard</h2>
      <p>You have successfully authenticated via Phase 1 Auth Gate!</p>
      <div class="user-details" v-if="authStore.user">
        <p><strong>Display Name:</strong> {{ authStore.user.displayName }}</p>
        <p><strong>Email:</strong> {{ authStore.user.email }}</p>
      </div>
    </div>

    <div class="quick-links">
      <router-link to="/app/accounts" class="quick-card">
        <span class="quick-icon">👤</span>
        <span class="quick-label">Manage Accounts</span>
        <span class="quick-arrow">→</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth.store';

const authStore = useAuthStore();
</script>

<style scoped>
.dashboard-page {
  max-width: 800px;
  margin: 0 auto;
}

.card {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

h2 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 22px;
  color: #f1f5f9;
}

p {
  color: #94a3b8;
  line-height: 1.6;
}

.user-details {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.user-details p {
  margin: 8px 0;
  color: #cbd5e1;
}

/* Quick links */
.quick-links {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(148, 163, 184, 0.08);
  border-radius: 10px;
  text-decoration: none;
  transition: all 0.15s;
}

.quick-card:hover {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.2);
  transform: translateY(-2px);
}

.quick-icon {
  font-size: 24px;
}

.quick-label {
  color: #e2e8f0;
  font-size: 15px;
  font-weight: 500;
  flex: 1;
}

.quick-arrow {
  color: #64748b;
  font-size: 16px;
}
</style>
