<template>
  <div v-if="visible" class="login-modal-overlay" @click.self="closeModal">
    <div class="login-modal">
      <div class="login-header">
        <h2>用户登录</h2>
        <button class="close-btn" @click="closeModal">×</button>
      </div>
      <div class="login-body">
        <div class="form-group">
          <label for="username">用户名</label>
          <input 
            type="text" 
            id="username" 
            v-model="username" 
            :class="{'error': errors.username}"
            placeholder="请输入用户名"
          />
          <span class="error-message" v-if="errors.username">{{ errors.username }}</span>
        </div>
        <div class="form-group">
          <label for="password">密码</label>
          <input 
            type="password" 
            id="password" 
            v-model="password" 
            :class="{'error': errors.password}"
            placeholder="请输入密码"
          />
          <span class="error-message" v-if="errors.password">{{ errors.password }}</span>
        </div>
        <div class="form-actions">
          <button class="login-btn" @click="handleLogin">登录</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';


const props = defineProps();
const emit = defineEmits(['close', 'login-success']);

const username = ref('');
const password = ref('');
const errors = reactive({
  username: '',
  password: ''
});

const validateForm = () => {
  let isValid = true;
  
  // 重置错误信息
  errors.username = '';
  errors.password = '';
  
  // 验证用户名
  if (!username.value) {
    errors.username = '请输入用户名';
    isValid = false;
  } else if (username.value.length < 3) {
    errors.username = '用户名长度不能少于3个字符';
    isValid = false;
  }
  
  // 验证密码
  if (!password.value) {
    errors.password = '请输入密码';
    isValid = false;
  } else if (password.value.length < 6) {
    errors.password = '密码长度不能少于6个字符';
    isValid = false;
  }
  
  return isValid;
};

const handleLogin = () => {
  if (validateForm()) {
    // 模拟登录成功
    setTimeout(() => {
      // 这里可以添加实际的登录逻辑
      console.log('登录成功', { username: username.value, password: password.value });
      
      // 发送登录成功事件
      emit('login-success', { username: username.value });
      
      // 关闭模态窗
      closeModal();
      
      // 清空表单
      username.value = '';
      password.value = '';
    }, 500);
  }
};

const closeModal = () => {
  emit('close');
};
</script>

<style scoped>
.login-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.login-modal {
  background-color: white;
  border-radius: 8px;
  width: 400px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.login-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

.login-header h2 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
}

.login-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
}

.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #4e6ef2;
}

.form-group input.error {
  border-color: #f56c6c;
}

.error-message {
  display: block;
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
}

.form-actions {
  margin-top: 24px;
}

.login-btn {
  width: 100%;
  background-color: #4e6ef2;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 12px 0;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.login-btn:hover {
  background-color: #3c5ae4;
}
</style>