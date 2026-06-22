import axios, { type AxiosInstance, type AxiosError } from 'axios';
import { useAuthStore } from '@/stores/auth.store';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

class ApiService {
  private axiosInstance: AxiosInstance;
  private refreshTokenPromise: Promise<string> | null = null;
  private requestQueue: Array<() => void> = [];

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // --- Request Interceptor: attach Access Token ---
    this.axiosInstance.interceptors.request.use(
      (config) => {
        const authStore = useAuthStore();
        if (authStore.accessToken) {
          config.headers.Authorization = `Bearer ${authStore.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    // --- Response Interceptor: 401 Refresh Queue ---
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const authStore = useAuthStore();
        const config = error.config;

        // Never retry refresh itself — prevents infinite loop
        if (config?.url === '/auth/refresh') {
          authStore.clearAuth();
          return Promise.reject(error);
        }

        // Only retry on 401 and if we have a refresh token
        if (error.response?.status === 401 && authStore.refreshToken && config) {
          // Queue this failed request; it will be retried after refresh
          return new Promise((resolve, reject) => {
            this.requestQueue.push(() => {
              this.axiosInstance(config)
                .then(resolve)
                .catch(reject);
            });

            // If no refresh is in progress, start one
            if (!this.refreshTokenPromise) {
              this.refreshTokenPromise = this.performTokenRefresh()
                .then(() => {
                  // Token refreshed — drain the queue
                  this.requestQueue.forEach((callback) => callback());
                  this.requestQueue = [];
                  this.refreshTokenPromise = null;
                })
                .catch((refreshError) => {
                  // Refresh failed — clear auth state
                  authStore.clearAuth();
                  this.requestQueue = [];
                  this.refreshTokenPromise = null;
                  // Redirect handled by router guard on next navigation
                  return Promise.reject(refreshError);
                });
            }
          });
        }

        return Promise.reject(error);
      },
    );
  }

  /**
   * Calls POST /auth/refresh with the current refreshToken.
   * **Backend wraps all responses in { code, data, msg }** — so the
   * actual tokens live at response.data.data, not response.data.
   */
  private async performTokenRefresh(): Promise<string> {
    const authStore = useAuthStore();
    try {
      const response = await this.axiosInstance.post('/auth/refresh', {
        refreshToken: authStore.refreshToken,
      });

      const { accessToken, refreshToken } = response.data.data; // data.data — TransformInterceptor wrapper
      authStore.setTokens(accessToken, refreshToken);
      return accessToken;
    } catch (error) {
      authStore.clearAuth();
      throw error;
    }
  }

  getAxios(): AxiosInstance {
    return this.axiosInstance;
  }
}

export const apiService = new ApiService();
export const api = apiService.getAxios();
