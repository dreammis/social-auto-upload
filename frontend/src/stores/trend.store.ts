import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api';

export interface TrendItem {
  id: number;
  keyword: string;
  volume: number;
  extracted_at: string;
}

export interface GroupedTrend {
  platform: string;
  trends: TrendItem[];
}

export const useTrendStore = defineStore('trends', () => {
  const trends = ref<GroupedTrend[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchLatestTrends() {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.get('/trends/latest');
      trends.value = response.data.data;
    } catch (err: any) {
      error.value = err.response?.data?.msg || err.response?.data?.message || 'Failed to fetch trends';
    } finally {
      isLoading.value = false;
    }
  }

  return {
    trends,
    isLoading,
    error,
    fetchLatestTrends,
  };
});
