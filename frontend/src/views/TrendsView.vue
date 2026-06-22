<template>
  <div class="trends-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1>🔥 Trend Engine</h1>
        <p class="subtitle">Latest trending keywords across platforms — updated every 2 hours</p>
      </div>
      <button class="btn-refresh" @click="handleRefresh" :disabled="store.isLoading">
        {{ store.isLoading ? 'Refreshing...' : '🔄 Refresh' }}
      </button>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="error-banner">
      {{ store.error }}
    </div>

    <!-- Loading -->
    <div v-if="store.isLoading && store.trends.length === 0" class="loading-state">
      <div class="spinner"></div>
      <p>Loading trends...</p>
    </div>

    <!-- Platform Tabs -->
    <div v-if="store.trends.length > 0" class="tabs">
      <button
        v-for="(group, idx) in store.trends"
        :key="group.platform"
        class="tab"
        :class="{ 'tab--active': activeTab === idx, [`tab-${group.platform}`]: true }"
        @click="activeTab = idx"
      >
        {{ platformLabel(group.platform) }}
        <span class="tab-count">{{ group.trends.length }}</span>
      </button>
    </div>

    <!-- Trend Grid -->
    <div v-if="activeGroup" class="trend-grid">
      <div
        v-for="trend in activeGroup.trends"
        :key="trend.id"
        class="trend-card"
        :class="{ 'trend-card--hot': trend.volume >= 800000 }"
      >
        <div class="trend-rank" :class="getRankClass(trend, activeGroup)">
          #{{ getRank(trend, activeGroup) }}
        </div>
        <div class="trend-info">
          <div class="trend-keyword">
            {{ trend.keyword }}
            <span v-if="trend.volume >= 800000" class="hot-badge">HOT</span>
          </div>
          <div class="trend-volume">
            {{ formatVolume(trend.volume) }} searches
          </div>
        </div>
        <div class="trend-bar">
          <div
            class="trend-bar-fill"
            :class="`bar-${activeGroup.platform}`"
            :style="{ width: barWidth(trend, activeGroup) + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!store.isLoading && store.trends.length === 0 && !store.error" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>No trend data yet</p>
      <p class="empty-hint">The AI Worker collects trends every 2 hours. Check back soon!</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useTrendStore, type GroupedTrend, type TrendItem } from '@/stores/trend.store';

const store = useTrendStore();

const activeTab = ref(0);

const activeGroup = computed<GroupedTrend | null>(() => {
  if (store.trends.length === 0) return null;
  return store.trends[activeTab.value] || null;
});

// Platform display
function platformLabel(platform: string): string {
  const labels: Record<string, string> = {
    tiktok: 'TikTok',
    facebook: 'Facebook',
    youtube: 'YouTube',
  };
  return labels[platform] || platform;
}

// Volume formatting
function formatVolume(volume: number): string {
  if (volume >= 1_000_000) return (volume / 1_000_000).toFixed(1) + 'M';
  if (volume >= 1_000) return (volume / 1_000).toFixed(1) + 'K';
  return volume.toString();
}

// Rank within platform group
function getRank(trend: TrendItem, group: GroupedTrend): number {
  return group.trends.findIndex((t) => t.id === trend.id) + 1;
}

function getRankClass(trend: TrendItem, group: GroupedTrend): string {
  const rank = getRank(trend, group);
  if (rank === 1) return 'rank-1';
  if (rank === 2) return 'rank-2';
  if (rank === 3) return 'rank-3';
  return '';
}

// Bar width relative to max volume in group
function barWidth(trend: TrendItem, group: GroupedTrend): number {
  const maxVol = group.trends[0]?.volume || 1;
  return Math.round((trend.volume / maxVol) * 100);
}

// Refresh
async function handleRefresh() {
  await store.fetchLatestTrends();
}

// Initial load
onMounted(() => {
  store.fetchLatestTrends();
});
</script>

<style scoped>
.trends-page {
  max-width: 1100px;
  margin: 0 auto;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h1 {
  color: #f1f5f9;
  font-size: 24px;
  margin: 0 0 4px 0;
}

.subtitle {
  color: #64748b;
  font-size: 14px;
  margin: 0;
}

.btn-refresh {
  padding: 10px 20px;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn-refresh:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Error */
.error-banner {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}

/* Loading */
.loading-state {
  text-align: center;
  padding: 60px 20px;
  color: #94a3b8;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(148, 163, 184, 0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Platform Tabs */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.08);
  border-radius: 10px;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.tab:hover {
  color: #e2e8f0;
  background: rgba(30, 41, 59, 0.8);
}

.tab--active {
  color: #fff;
  border-color: rgba(148, 163, 184, 0.15);
  background: rgba(30, 41, 59, 0.9);
}

.tab--active.tab-tiktok   { border-color: rgba(255, 255, 255, 0.25); box-shadow: 0 0 15px rgba(255,255,255,0.05); }
.tab--active.tab-facebook { border-color: rgba(24, 119, 242, 0.4);  box-shadow: 0 0 15px rgba(24,119,242,0.1); }
.tab--active.tab-youtube  { border-color: rgba(255, 0, 0, 0.4);    box-shadow: 0 0 15px rgba(255,0,0,0.1); }

.tab-count {
  font-size: 12px;
  padding: 2px 8px;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 10px;
}

/* Trend Grid */
.trend-grid {
  display: grid;
  gap: 12px;
}

.trend-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.06);
  border-radius: 10px;
  transition: all 0.15s;
}

.trend-card:hover {
  background: rgba(30, 41, 59, 0.7);
  border-color: rgba(148, 163, 184, 0.12);
}

.trend-card--hot {
  border-left: 3px solid #ef4444;
  background: rgba(30, 41, 59, 0.6);
}

/* Rank */
.trend-rank {
  font-size: 14px;
  font-weight: 700;
  color: #64748b;
  min-width: 32px;
  text-align: center;
  flex-shrink: 0;
}

.rank-1 { color: #fbbf24; }
.rank-2 { color: #94a3b8; }
.rank-3 { color: #d97706; }

/* Trend info */
.trend-info {
  flex: 1;
  min-width: 0;
}

.trend-keyword {
  color: #e2e8f0;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.hot-badge {
  padding: 2px 8px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  letter-spacing: 0.5px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.trend-volume {
  color: #64748b;
  font-size: 13px;
}

/* Trend bar */
.trend-bar {
  width: 120px;
  height: 6px;
  background: rgba(148, 163, 184, 0.08);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.trend-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.bar-tiktok   { background: linear-gradient(90deg, #fff, #94a3b8); }
.bar-facebook { background: linear-gradient(90deg, #1877F2, #60a5fa); }
.bar-youtube  { background: linear-gradient(90deg, #FF0000, #f87171); }

/* Empty */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.empty-state p {
  color: #94a3b8;
  font-size: 15px;
  margin: 4px 0;
}

.empty-hint {
  font-size: 13px !important;
  color: #64748b !important;
}
</style>
