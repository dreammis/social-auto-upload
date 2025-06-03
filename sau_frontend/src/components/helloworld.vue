<template>
  <div class="hello-world">
    <h1>{{ msg }}</h1>
    <div class="card">
      <el-button type="primary" @click="count++">
        点击次数: {{ count }}
      </el-button>
      <p class="mt-3">
        这是一个使用 Element Plus 的示例组件
      </p>
    </div>
    <div class="links mt-4">
      <el-link href="https://vuejs.org/" target="_blank" type="primary">
        Vue.js 官网
      </el-link>
      <el-link href="https://element-plus.org/" target="_blank" type="success">
        Element Plus 官网
      </el-link>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  msg: {
    type: String,
    default: 'Hello Vue 3 + Vite'
  }
})

const count = ref(0)
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.hello-world {
  text-align: center;
  padding: 2rem;
  
  h1 {
    color: #2c3e50;
    margin-bottom: 2rem;
  }
  
  .card {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
    
    p {
      color: #666;
    }
  }
  
  .links {
    display: flex;
    justify-content: center;
    gap: 1rem;
  }
}
</style>
