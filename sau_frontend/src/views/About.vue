<template>
  <div class="about">
    <h1>关于我们</h1>
    <p>这是关于页面</p>
  </div>
</template>

<script setup>
// 关于页面组件
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.about {
  text-align: center;
  padding: 2rem;
  
  h1 {
    color: #2c3e50;
    margin-bottom: 1rem;
  }
  
  p {
    color: #7f8c8d;
  }
}
</style>