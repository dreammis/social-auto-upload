import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '@/api';

export interface User {
  id: string;
  email: string;
  displayName: string;
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null);
  const accessToken = ref<string | null>(null);
  const refreshToken = ref<string | null>(null);
  const initialized = ref(false);

  const isAuthenticated = computed(() => !!accessToken.value);

  //  Hydrate: load tokens from localStorage on app init.
  //  Wrapped in try/catch to survive corrupted localStorage entries.
  async function hydrate(): Promise<void> {
    try {
      const storedAccessToken = localStorage.getItem('accessToken');
      const storedRefreshToken = localStorage.getItem('refreshToken');
      const storedUser = localStorage.getItem('user');

      if (storedAccessToken && storedRefreshToken) {
        accessToken.value = storedAccessToken;
        refreshToken.value = storedRefreshToken;
        if (storedUser) {
          try {
            user.value = JSON.parse(storedUser);
          } catch {
            // Corrupted user JSON — discard it, keep tokens
            localStorage.removeItem('user');
          }
        }
      }
    } catch {
      // localStorage entirely inaccessible — nothing to hydrate
    }

    initialized.value = true;
  }

  function setTokens(newAccessToken: string, newRefreshToken: string) {
    accessToken.value = newAccessToken;
    refreshToken.value = newRefreshToken;
    localStorage.setItem('accessToken', newAccessToken);
    localStorage.setItem('refreshToken', newRefreshToken);
  }

  function setUser(newUser: User) {
    user.value = newUser;
    localStorage.setItem('user', JSON.stringify(newUser));
  }

  async function login(email: string, password: string) {
    try {
      const response = await api.post('/auth/login', { email, password });

      // Backend TransformInterceptor wraps: { code, data, msg }
      const { accessToken: newAccessToken, refreshToken: newRefreshToken, user: newUser } =
        response.data.data;

      setTokens(newAccessToken, newRefreshToken);
      setUser(newUser);
      return { success: true };
    } catch (error: any) {
      const message = error.response?.data?.msg || error.response?.data?.message || 'Login failed';
      return { success: false, message };
    }
  }

  async function register(email: string, password: string, displayName: string) {
    try {
      const response = await api.post('/auth/register', { email, password, displayName });

      // Backend TransformInterceptor wraps: { code, data, msg }
      const { accessToken: newAccessToken, refreshToken: newRefreshToken, user: newUser } =
        response.data.data;

      setTokens(newAccessToken, newRefreshToken);
      setUser(newUser);
      return { success: true };
    } catch (error: any) {
      const message = error.response?.data?.msg || error.response?.data?.message || 'Registration failed';
      return { success: false, message };
    }
  }

  function logout() {
    clearAuth();
  }

  function clearAuth() {
    user.value = null;
    accessToken.value = null;
    refreshToken.value = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
  }

  return {
    user,
    accessToken,
    refreshToken,
    initialized,
    isAuthenticated,
    hydrate,
    setTokens,
    setUser,
    login,
    register,
    logout,
    clearAuth,
  };
});
