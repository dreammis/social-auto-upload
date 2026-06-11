<template>
  <div class="config-page">
    <el-card class="config-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <h2>配置中心</h2>
            <p>动态调整浏览器无头模式，不再需要手动修改配置文件。</p>
          </div>
        </div>
      </template>

      <el-skeleton v-if="loading" :rows="4" animated />

      <el-form
        v-else
        label-position="top"
        class="config-form"
      >
        <el-form-item>
          <template #label>
            <div class="label-wrap">
              <span>LOCAL_CHROME_HEADLESS</span>
              <span class="field-desc">控制平台上传、打开上传页、cookie 检测等通用浏览器是否无头运行。</span>
            </div>
          </template>
          <el-switch v-model="form.localChromeHeadless" />
        </el-form-item>

        <el-form-item>
          <template #label>
            <div class="label-wrap">
              <span>登录浏览器 headless</span>
              <span class="field-desc">控制 login.py 中 `get_browser_options` 返回的 headless，用于扫码登录流程。</span>
            </div>
          </template>
          <el-switch v-model="form.loginBrowserHeadless" />
        </el-form-item>

        <div class="actions">
          <el-button type="primary" :loading="saving" @click="handleSave">
            保存配置
          </el-button>
          <el-button :disabled="saving" @click="loadConfig">
            刷新
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '@/api/config'

const loading = ref(false)
const saving = ref(false)

const form = reactive({
  localChromeHeadless: false,
  loginBrowserHeadless: false
})

const applyConfig = (config = {}) => {
  form.localChromeHeadless = !!config.localChromeHeadless
  form.loginBrowserHeadless = !!config.loginBrowserHeadless
}

const loadConfig = async () => {
  loading.value = true
  try {
    const res = await configApi.getConfig()
    applyConfig(res.data || {})
  } catch (error) {
    console.error('加载配置失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    const res = await configApi.updateConfig({
      localChromeHeadless: form.localChromeHeadless,
      loginBrowserHeadless: form.loginBrowserHeadless
    })
    applyConfig(res.data || {})
    ElMessage.success('配置已保存')
  } catch (error) {
    console.error('保存配置失败:', error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped lang="scss">
.config-page {
  max-width: 880px;
}

.config-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 600;
    color: #1f2937;
  }

  p {
    margin: 0;
    color: #6b7280;
    font-size: 14px;
  }
}

.config-form {
  margin-top: 8px;
}

.label-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.5;
}

.field-desc {
  font-size: 13px;
  color: #6b7280;
  font-weight: 400;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}
</style>
