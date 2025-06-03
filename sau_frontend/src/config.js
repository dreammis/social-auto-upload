// 全局配置文件

// API基础URL
export const API_BASE_URL = 'http://localhost:5409';

// 全局账号列表缓存
export const globalAccountsCache = {
  accounts: null,  // 缓存的账号数据
  lastFetchTime: null,  // 最后一次获取数据的时间
  
  // 检查缓存是否有效
  isValid() {
    return this.accounts !== null;
  },
  
  // 更新缓存
  updateCache(accounts) {
    this.accounts = accounts;
    this.lastFetchTime = new Date().getTime();
  },
  
  // 清除缓存
  clearCache() {
    this.accounts = null;
    this.lastFetchTime = null;
  }
};