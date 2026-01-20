// 缓存工具模块
const cache = {
  // 本地存储
  local: {
    set(key, value) {
      localStorage.setItem(key, JSON.stringify(value));
    },
    get(key) {
      const value = localStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    },
    setJSON(key, value) {
      this.set(key, value);
    },
    getJSON(key) {
      return this.get(key);
    },
    remove(key) {
      localStorage.removeItem(key);
    },
    clear() {
      localStorage.clear();
    }
  },
  
  // 会话存储
  session: {
    set(key, value) {
      sessionStorage.setItem(key, JSON.stringify(value));
    },
    get(key) {
      const value = sessionStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    },
    setJSON(key, value) {
      this.set(key, value);
    },
    getJSON(key) {
      return this.get(key);
    },
    remove(key) {
      sessionStorage.removeItem(key);
    },
    clear() {
      sessionStorage.clear();
    }
  }
};

export default cache;