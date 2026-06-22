import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/api';

export type Platform = 'tiktok' | 'facebook' | 'youtube' | 'instagram' | 'shopee';
export type AccountStatus = 'active' | 'dead' | 'checking';

export interface SocialAccount {
  id: number;
  platform: Platform;
  account_name: string;
  status: AccountStatus;
  last_health_check: string | null;
  created_at: string;
  updated_at: string;
  user_id: number;
}

export interface AddAccountPayload {
  platform: Platform;
  account_name: string;
  session_data: Record<string, any>;
}

export const useAccountStore = defineStore('accounts', () => {
  const accounts = ref<SocialAccount[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchAccounts() {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.get('/accounts');
      accounts.value = response.data.data;
    } catch (err: any) {
      error.value = err.response?.data?.msg || err.response?.data?.message || 'Failed to load accounts';
    } finally {
      isLoading.value = false;
    }
  }

  async function addAccount(payload: AddAccountPayload) {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await api.post('/accounts', payload);
      const newAccount: SocialAccount = response.data.data;
      accounts.value.unshift(newAccount); // prepend — newest first
      return { success: true, account: newAccount };
    } catch (err: any) {
      const message = err.response?.data?.msg || err.response?.data?.message || 'Failed to add account';
      error.value = message;
      return { success: false, message };
    } finally {
      isLoading.value = false;
    }
  }

  async function deleteAccount(id: number) {
    error.value = null;

    try {
      await api.delete(`/accounts/${id}`);
      accounts.value = accounts.value.filter((a) => a.id !== id);
      return { success: true };
    } catch (err: any) {
      const message = err.response?.data?.msg || err.response?.data?.message || 'Failed to delete account';
      error.value = message;
      return { success: false, message };
    }
  }

  async function checkHealth(id: number) {
    error.value = null;

    try {
      // Set local status to 'checking' immediately for UX feedback
      const account = accounts.value.find((a) => a.id === id);
      if (account) account.status = 'checking';

      const response = await api.patch(`/accounts/${id}/status`, { status: 'checking' });
      const updated: SocialAccount = response.data.data;

      // Replace with server response
      const index = accounts.value.findIndex((a) => a.id === id);
      if (index !== -1) accounts.value[index] = updated;

      return { success: true };
    } catch (err: any) {
      const message = err.response?.data?.msg || err.response?.data?.message || 'Health check failed';
      error.value = message;
      return { success: false, message };
    }
  }

  return {
    accounts,
    isLoading,
    error,
    fetchAccounts,
    addAccount,
    deleteAccount,
    checkHealth,
  };
});
