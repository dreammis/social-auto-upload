<template>
  <div class="about">
    <el-card class="about-card">
      <div class="about-header">
        <h1>自媒体自动化运营系统</h1>
        <p class="version">social-auto-upload</p>
      </div>

      <el-divider />

      <div class="about-section">
        <h3>系统简介</h3>
        <p>
          本系统是一款强大的自动化工具，帮助内容创作者和运营人员一键将视频内容高效发布到多个国内外主流社交媒体平台。
          支持视频上传、定时发布等功能。
        </p>
      </div>

      <div class="about-section">
        <h3>支持平台</h3>
        <div class="platform-tags">
          <el-tag type="danger">抖音</el-tag>
          <el-tag type="success">快手</el-tag>
          <el-tag type="warning">视频号</el-tag>
          <el-tag type="info">小红书</el-tag>
        </div>
      </div>

      <div class="about-section">
        <h3>核心功能</h3>
        <ul class="feature-list">
          <li>多平台账号管理与登录状态维护</li>
          <li>视频素材上传与管理</li>
          <li>一键多平台发布</li>
          <li>定时发布与批量发布</li>
          <li>Cookie 导入导出</li>
        </ul>
      </div>

      <div class="about-section">
        <h3>技术栈</h3>
        <div class="tech-tags">
          <el-tag effect="plain">Vue 3</el-tag>
          <el-tag effect="plain">Element Plus</el-tag>
          <el-tag effect="plain">Pinia</el-tag>
          <el-tag effect="plain">Flask</el-tag>
          <el-tag effect="plain">Playwright</el-tag>
          <el-tag effect="plain">SQLite</el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 关于页面组件
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.about {
  max-width: 700px;
  margin: 0 auto;

  .about-card {
    .about-header {
      text-align: center;

      h1 {
        color: $text-primary;
        margin: 0 0 8px 0;
        font-size: 24px;
      }

      .version {
        color: $text-secondary;
        font-size: 14px;
        margin: 0;
      }
    }

    .about-section {
      margin-bottom: 24px;

      h3 {
        font-size: 16px;
        color: $text-primary;
        margin: 0 0 12px 0;
      }

      p {
        color: $text-secondary;
        line-height: 1.8;
        margin: 0;
      }

      .platform-tags,
      .tech-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .feature-list {
        margin: 0;
        padding-left: 20px;
        color: $text-secondary;
        line-height: 2;
      }
    }
  }
}
</style>
