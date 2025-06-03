<template>
  <div class="article-publish-view">
    <h1>发布图文</h1>
    
    <!-- 标题 -->
    <div class="form-group">
      <label>标题：</label>
      <div class="input-wrapper">
        <input type="text" class="form-input" placeholder="请输入标题" />
        <span class="character-count">0/30</span>
      </div>
    </div>
    
    <!-- 图片 -->
    <div class="form-group">
      <label>图片：</label>
      <div class="image-upload-area">
        <div class="upload-box">
          <div class="plus-icon">+</div>
        </div>
      </div>
    </div>
    
    <!-- 活动 -->
    <div class="form-group">
      <label>活动：</label>
      <div class="input-wrapper">
        <input type="text" class="form-input" placeholder="请输入活动..." />
      </div>
    </div>
    
    <!-- 按钮区域 -->
    <div class="action-buttons">
      <button class="btn btn-preview">预览内容</button>
      <button class="btn btn-publish">零点发布</button>
    </div>
  </div>
</template>

<script setup>
// 这里可以添加组件逻辑
</script>

<style scoped>
.article-publish-view {
  padding: 20px;
}

h1 {
  margin-bottom: 30px;
  font-size: 24px;
  font-weight: 500;
}

.form-group {
  margin-bottom: 25px;
}

label {
  display: block;
  margin-bottom: 10px;
  font-weight: 500;
}

.input-wrapper {
  position: relative;
}

.form-input {
  width: 100%;
  padding: 10px 15px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
}

.character-count {
  position: absolute;
  right: 10px;
  top: 10px;
  color: #999;
  font-size: 12px;
}

.image-upload-area {
  display: flex;
  gap: 15px;
}

.upload-box {
  width: 150px;
  height: 150px;
  border: 1px dashed #ccc;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background-color: #f9f9f9;
}

.plus-icon {
  font-size: 40px;
  color: #ccc;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 30px;
}

.btn {
  padding: 10px 20px;
  border-radius: 4px;
  border: none;
  font-size: 14px;
  cursor: pointer;
}

.btn-preview {
  background-color: #fff;
  border: 1px solid #e0e0e0;
}

.btn-publish {
  background-color: #6366f1;
  color: white;
}
</style>