<template>
  <div class="publish-center">
    <div class="tab-management">
      <div class="tab-header">
        <div class="tab-list">
          <button
            v-for="tab in tabs"
            :key="tab.name"
            :class="['tab-item', { active: activeTab === tab.name }]"
            type="button"
            @click="activeTab = tab.name"
          >
            <span>{{ tab.label }}</span>
            <el-icon v-if="tabs.length > 1" class="close-icon" @click.stop="removeTab(tab.name)">
              <Close />
            </el-icon>
          </button>
        </div>
        <div class="tab-actions">
          <el-button type="primary" size="small" @click="addTab">
            <el-icon><Plus /></el-icon>
            添加发布页
          </el-button>
          <el-button type="success" size="small" :loading="batchPublishing" @click="batchPublish">
            批量发布
          </el-button>
        </div>
      </div>
    </div>

    <div class="publish-content">
      <section v-for="tab in tabs" :key="tab.name" v-show="activeTab === tab.name" class="publish-form">
        <el-alert
          v-if="tab.publishStatus"
          :title="tab.publishStatus.message"
          :type="tab.publishStatus.type"
          :closable="false"
          show-icon
          class="status-alert"
        />

        <div class="form-section">
          <h3>内容类型</h3>
          <el-segmented
            v-model="tab.contentType"
            :options="contentTypeOptions"
            @change="handleContentTypeChange(tab)"
          />
        </div>

        <div class="form-section">
          <div class="section-title-row">
            <h3>{{ contentTypeLabel(tab) }}</h3>
            <el-tag :type="tab.contentType === 'note' ? 'success' : 'primary'" effect="plain">
              {{ tab.fileList.length }} 个文件
            </el-tag>
          </div>
          <div class="upload-options">
            <el-button type="primary" @click="showUploadOptions(tab)">
              <el-icon><Upload /></el-icon>
              上传{{ contentTypeLabel(tab) }}
            </el-button>
          </div>

          <div v-if="tab.fileList.length > 0" class="uploaded-files">
            <div v-for="(file, index) in tab.fileList" :key="file.path" class="file-item">
              <el-link :href="file.url" target="_blank" type="primary">{{ file.name }}</el-link>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <el-button type="danger" size="small" plain @click="removeFile(tab, index)">删除</el-button>
            </div>
          </div>
        </div>

        <div class="form-section">
          <h3>账号</h3>
          <div class="tag-field">
            <div class="tag-list">
              <el-tag
                v-for="(account, index) in tab.selectedAccounts"
                :key="account"
                closable
                @close="removeAccount(tab, index)"
              >
                {{ getAccountDisplayName(account) }}
              </el-tag>
            </div>
            <el-button type="primary" plain @click="openAccountDialog(tab)">选择账号</el-button>
          </div>
        </div>

        <div class="form-section">
          <h3>平台</h3>
          <el-radio-group v-model="tab.selectedPlatform" class="platform-radios" @change="handlePlatformChange(tab)">
            <el-radio
              v-for="platform in platforms"
              :key="platform.key"
              :label="platform.key"
              :disabled="tab.contentType === 'note' && !platform.supportsNote"
            >
              {{ platform.name }}
              <span v-if="tab.contentType === 'note' && !platform.supportsNote" class="muted">暂不支持图文</span>
            </el-radio>
          </el-radio-group>
        </div>

        <div class="form-section compact-options">
          <el-checkbox v-model="tab.isOriginal">声明原创</el-checkbox>
          <el-checkbox v-if="tab.contentType === 'video' && tab.selectedPlatform === 2" v-model="tab.isDraft">
            视频号仅保存草稿
          </el-checkbox>
        </div>

        <div v-if="tab.contentType === 'video' && tab.selectedPlatform === 3" class="form-section">
          <h3>商品链接</h3>
          <el-input v-model="tab.productTitle" placeholder="商品名称" maxlength="200" clearable />
          <el-input v-model="tab.productLink" placeholder="商品链接" maxlength="200" clearable class="mt-8" />
        </div>

        <div class="form-section">
          <h3>标题</h3>
          <el-input
            v-model="tab.title"
            type="textarea"
            :rows="3"
            placeholder="请输入标题"
            maxlength="100"
            show-word-limit
          />
        </div>

        <div v-if="tab.contentType === 'note'" class="form-section">
          <h3>正文</h3>
          <el-input
            v-model="tab.note"
            type="textarea"
            :rows="5"
            placeholder="请输入图文正文"
            maxlength="2000"
            show-word-limit
          />
        </div>

        <div class="form-section">
          <h3>话题</h3>
          <div class="tag-field">
            <div class="tag-list">
              <el-tag
                v-for="(topic, index) in tab.selectedTopics"
                :key="topic"
                closable
                @close="removeTopic(tab, index)"
              >
                #{{ topic }}
              </el-tag>
            </div>
            <el-button type="primary" plain @click="openTopicDialog(tab)">添加话题</el-button>
          </div>
        </div>

        <div class="form-section">
          <h3>定时发布</h3>
          <div class="schedule-controls">
            <el-switch v-model="tab.scheduleEnabled" active-text="定时发布" inactive-text="立即发布" />
            <div v-if="tab.scheduleEnabled" class="schedule-settings">
              <div class="schedule-item">
                <span class="label">每天发布数量</span>
                <el-select v-model="tab.videosPerDay" placeholder="数量">
                  <el-option v-for="num in 55" :key="num" :label="num" :value="num" />
                </el-select>
              </div>
              <div class="schedule-item schedule-times">
                <span class="label">发布时间</span>
                <el-time-select
                  v-for="(_, index) in tab.dailyTimes"
                  :key="index"
                  v-model="tab.dailyTimes[index]"
                  start="00:00"
                  step="00:30"
                  end="23:30"
                  placeholder="选择时间"
                />
                <el-button
                  v-if="tab.dailyTimes.length < tab.videosPerDay"
                  type="primary"
                  size="small"
                  @click="tab.dailyTimes.push('10:00')"
                >
                  添加时间
                </el-button>
              </div>
              <div class="schedule-item">
                <span class="label">开始日期</span>
                <el-select v-model="tab.startDays" placeholder="开始日期">
                  <el-option label="明天" :value="0" />
                  <el-option label="后天" :value="1" />
                </el-select>
              </div>
            </div>
          </div>
        </div>

        <div class="action-buttons">
          <el-button size="small" @click="cancelPublish">取消</el-button>
          <el-button size="small" type="primary" :loading="tab.publishing" @click="confirmPublish(tab)">
            {{ tab.publishing ? '发布中...' : `发布${contentTypeLabel(tab)}` }}
          </el-button>
        </div>
      </section>
    </div>

    <el-dialog v-model="uploadOptionsVisible" title="选择上传方式" width="400px">
      <div class="upload-options-content">
        <el-button type="primary" @click="selectLocalUpload">
          <el-icon><Upload /></el-icon>
          本地上传
        </el-button>
        <el-button type="success" @click="selectMaterialLibrary">
          <el-icon><Folder /></el-icon>
          素材库
        </el-button>
      </div>
    </el-dialog>

    <el-dialog v-model="localUploadVisible" :title="`本地上传${contentTypeLabel(currentUploadTab)}`" width="600px">
      <el-upload
        class="local-upload"
        drag
        multiple
        :auto-upload="true"
        :action="`${apiBaseUrl}/upload`"
        :accept="acceptTypes(currentUploadTab)"
        :headers="authHeaders"
        :on-success="(response, file) => handleUploadSuccess(response, file, currentUploadTab)"
        :on-error="handleUploadError"
      >
        <el-icon class="el-icon--upload"><Upload /></el-icon>
        <div class="el-upload__text">
          将{{ contentTypeLabel(currentUploadTab) }}文件拖到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">{{ uploadTip(currentUploadTab) }}</div>
        </template>
      </el-upload>
    </el-dialog>

    <el-dialog v-model="materialLibraryVisible" :title="`选择${contentTypeLabel(currentUploadTab)}素材`" width="800px">
      <el-empty v-if="filteredMaterials.length === 0" description="暂无可用素材" />
      <el-checkbox-group v-else v-model="selectedMaterials">
        <div class="material-list">
          <label v-for="material in filteredMaterials" :key="material.id" class="material-item">
            <el-checkbox :label="material.id">
              <div class="material-info">
                <div class="material-name">{{ material.filename }}</div>
                <div class="material-details">
                  <span>{{ material.filesize }}MB</span>
                  <span>{{ material.upload_time }}</span>
                </div>
              </div>
            </el-checkbox>
          </label>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="materialLibraryVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMaterialSelection">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="accountDialogVisible" title="选择账号" width="600px">
      <el-empty v-if="availableAccounts.length === 0" description="当前平台暂无账号" />
      <el-checkbox-group v-else v-model="tempSelectedAccounts">
        <div class="account-list">
          <el-checkbox v-for="account in availableAccounts" :key="account.id" :label="account.id" class="account-item">
            <span class="account-name">{{ account.name }}</span>
            <el-tag size="small" effect="plain">{{ account.status }}</el-tag>
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="accountDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAccountSelection">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="topicDialogVisible" title="添加话题" width="600px">
      <div class="custom-topic-input">
        <el-input v-model="customTopic" placeholder="输入自定义话题" @keyup.enter="addCustomTopic">
          <template #prepend>#</template>
        </el-input>
        <el-button type="primary" @click="addCustomTopic">添加</el-button>
      </div>
      <div class="topic-grid">
        <el-button
          v-for="topic in recommendedTopics"
          :key="topic"
          :type="currentTab?.selectedTopics?.includes(topic) ? 'primary' : 'default'"
          @click="toggleRecommendedTopic(topic)"
        >
          {{ topic }}
        </el-button>
      </div>
      <template #footer>
        <el-button @click="topicDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmTopicSelection">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="batchPublishDialogVisible"
      title="批量发布进度"
      width="520px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="publishProgress === 100"
    >
      <div class="publish-progress">
        <el-progress :percentage="publishProgress" :status="publishProgress === 100 ? 'success' : ''" />
        <div v-if="currentPublishingTab" class="current-publishing">
          正在发布：{{ currentPublishingTab.label }}
        </div>
        <div v-if="publishResults.length > 0" class="publish-results">
          <div v-for="(result, index) in publishResults" :key="index" :class="['result-item', result.status]">
            <el-icon v-if="result.status === 'success'"><Check /></el-icon>
            <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
            <el-icon v-else><InfoFilled /></el-icon>
            <span class="label">{{ result.label }}</span>
            <span class="message">{{ result.message }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button :disabled="publishProgress === 100" @click="cancelBatchPublish">取消发布</el-button>
        <el-button v-if="publishProgress === 100" type="primary" @click="batchPublishDialogVisible = false">
          关闭
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Check, Close, Folder, InfoFilled, Plus, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { materialApi } from '@/api/material'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { http } from '@/utils/request'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'
const authHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`
}))

const appStore = useAppStore()
const accountStore = useAccountStore()

const contentTypeOptions = [
  { label: '发视频', value: 'video' },
  { label: '发图文', value: 'note' }
]

const platforms = [
  { key: 3, name: '抖音', supportsNote: true },
  { key: 4, name: '快手', supportsNote: true },
  { key: 2, name: '视频号', supportsNote: false },
  { key: 1, name: '小红书', supportsNote: true }
]

const platformNames = {
  1: '小红书',
  2: '视频号',
  3: '抖音',
  4: '快手'
}

const recommendedTopics = [
  '游戏', '电影', '音乐', '美食', '旅行', '文化',
  '科技', '生活', '娱乐', '体育', '教育', '艺术',
  '健康', '时尚', '美妆', '摄影', '汽车'
]

let tabCounter = 1
const activeTab = ref('tab1')

const makeNewTab = () => ({
  name: 'tab1',
  label: '发布1',
  contentType: 'video',
  fileList: [],
  selectedAccounts: [],
  selectedPlatform: 3,
  title: '',
  note: '',
  productLink: '',
  productTitle: '',
  selectedTopics: [],
  scheduleEnabled: false,
  videosPerDay: 1,
  dailyTimes: ['10:00'],
  startDays: 0,
  publishStatus: null,
  publishing: false,
  isDraft: false,
  isOriginal: false
})

const tabs = reactive([makeNewTab()])

const uploadOptionsVisible = ref(false)
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const currentUploadTab = ref(null)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)

const accountDialogVisible = ref(false)
const tempSelectedAccounts = ref([])
const currentTab = ref(null)

const topicDialogVisible = ref(false)
const customTopic = ref('')

const batchPublishing = ref(false)
const batchPublishDialogVisible = ref(false)
const currentPublishingTab = ref(null)
const publishProgress = ref(0)
const publishResults = ref([])
const isCancelled = ref(false)

const isImageFile = (filename = '') => /\.(png|jpe?g|webp|gif|bmp)$/i.test(filename)
const isVideoFile = (filename = '') => /\.(mp4|mov|avi|mkv|flv|webm)$/i.test(filename)

const contentTypeLabel = (tab) => (tab?.contentType === 'note' ? '图文' : '视频')
const acceptTypes = (tab) => (tab?.contentType === 'note' ? 'image/*' : 'video/*')
const uploadTip = (tab) => (
  tab?.contentType === 'note'
    ? '支持 JPG、PNG、WEBP 等图片，可一次上传多张'
    : '支持 MP4、MOV、AVI 等视频格式，可一次上传多个'
)

const filteredMaterials = computed(() => {
  if (!currentUploadTab.value) return materials.value
  const matcher = currentUploadTab.value.contentType === 'note' ? isImageFile : isVideoFile
  return materials.value.filter(material => matcher(material.filename || material.file_path))
})

const availableAccounts = computed(() => {
  if (!currentTab.value) return []
  const type = currentTab.value.selectedPlatform
  return accountStore.accounts.filter(acc => acc.type === type || acc.platform === platformNames[type])
})

const addTab = () => {
  tabCounter += 1
  const newTab = makeNewTab()
  newTab.name = `tab${tabCounter}`
  newTab.label = `发布${tabCounter}`
  tabs.push(newTab)
  activeTab.value = newTab.name
}

const removeTab = (tabName) => {
  const index = tabs.findIndex(tab => tab.name === tabName)
  if (index === -1) return
  tabs.splice(index, 1)
  if (activeTab.value === tabName && tabs.length > 0) {
    activeTab.value = tabs[0].name
  }
}

const handleContentTypeChange = (tab) => {
  tab.fileList = []
  tab.publishStatus = null
  if (tab.contentType === 'note') {
    tab.productLink = ''
    tab.productTitle = ''
    tab.isDraft = false
    if (tab.selectedPlatform === 2) {
      tab.selectedPlatform = 3
      tab.selectedAccounts = []
    }
  }
}

const handlePlatformChange = (tab) => {
  tab.selectedAccounts = []
  if (tab.contentType === 'note' && tab.selectedPlatform === 2) {
    tab.selectedPlatform = 3
    ElMessage.warning('视频号暂不支持图文发布，已切换到抖音')
  }
}

const showUploadOptions = (tab) => {
  currentUploadTab.value = tab
  uploadOptionsVisible.value = true
}

const selectLocalUpload = () => {
  uploadOptionsVisible.value = false
  localUploadVisible.value = true
}

const selectMaterialLibrary = async () => {
  uploadOptionsVisible.value = false
  try {
    const response = await materialApi.getAllMaterials()
    if (response.code === 200) {
      appStore.setMaterials(response.data)
      selectedMaterials.value = []
      materialLibraryVisible.value = true
    } else {
      ElMessage.error(response.msg || '获取素材列表失败')
    }
  } catch (error) {
    console.error('获取素材列表失败:', error)
    ElMessage.error('获取素材列表失败')
  }
}

const handleUploadSuccess = (response, file, tab) => {
  if (!tab) return
  if (response.code !== 200) {
    ElMessage.error(response.msg || '上传失败')
    return
  }

  const filePath = response.data?.filepath || response.data?.path || response.data
  const filename = String(filePath).split('/').pop()
  const fileInfo = {
    name: file.name,
    url: materialApi.getMaterialPreviewUrl(filename),
    path: filePath,
    size: file.size,
    type: file.type
  }

  const matcher = tab.contentType === 'note' ? isImageFile : isVideoFile
  if (!matcher(file.name)) {
    ElMessage.warning(`当前是${contentTypeLabel(tab)}模式，已忽略不匹配的文件`)
    return
  }

  if (!tab.fileList.some(item => item.path === fileInfo.path)) {
    tab.fileList.push(fileInfo)
  }
  ElMessage.success('文件上传成功')
}

const handleUploadError = () => {
  ElMessage.error('文件上传失败')
}

const confirmMaterialSelection = () => {
  if (!currentUploadTab.value) return
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('请选择至少一个素材')
    return
  }

  const tab = currentUploadTab.value
  let addedCount = 0
  selectedMaterials.value.forEach(materialId => {
    const material = materials.value.find(item => item.id === materialId)
    if (!material) return
    const fileInfo = {
      name: material.filename,
      url: materialApi.getMaterialPreviewUrl(String(material.file_path).split('/').pop()),
      path: material.file_path,
      size: Number(material.filesize || 0) * 1024 * 1024,
      type: tab.contentType === 'note' ? 'image/*' : 'video/*'
    }
    if (!tab.fileList.some(item => item.path === fileInfo.path)) {
      tab.fileList.push(fileInfo)
      addedCount += 1
    }
  })

  materialLibraryVisible.value = false
  selectedMaterials.value = []
  currentUploadTab.value = null
  ElMessage.success(`已添加 ${addedCount} 个素材`)
}

const removeFile = (tab, index) => {
  tab.fileList.splice(index, 1)
}

const openAccountDialog = (tab) => {
  currentTab.value = tab
  tempSelectedAccounts.value = [...tab.selectedAccounts]
  accountDialogVisible.value = true
}

const confirmAccountSelection = () => {
  if (currentTab.value) {
    currentTab.value.selectedAccounts = [...tempSelectedAccounts.value]
  }
  accountDialogVisible.value = false
  currentTab.value = null
}

const removeAccount = (tab, index) => {
  tab.selectedAccounts.splice(index, 1)
}

const getAccountDisplayName = (accountId) => {
  const account = accountStore.accounts.find(acc => acc.id === accountId)
  return account ? account.name : accountId
}

const openTopicDialog = (tab) => {
  currentTab.value = tab
  topicDialogVisible.value = true
}

const addCustomTopic = () => {
  const topic = customTopic.value.trim().replace(/^#/, '')
  if (!topic) {
    ElMessage.warning('请输入话题内容')
    return
  }
  if (currentTab.value && !currentTab.value.selectedTopics.includes(topic)) {
    currentTab.value.selectedTopics.push(topic)
    customTopic.value = ''
  } else {
    ElMessage.warning('话题已存在')
  }
}

const toggleRecommendedTopic = (topic) => {
  if (!currentTab.value) return
  const index = currentTab.value.selectedTopics.indexOf(topic)
  if (index > -1) {
    currentTab.value.selectedTopics.splice(index, 1)
  } else {
    currentTab.value.selectedTopics.push(topic)
  }
}

const removeTopic = (tab, index) => {
  tab.selectedTopics.splice(index, 1)
}

const confirmTopicSelection = () => {
  topicDialogVisible.value = false
  customTopic.value = ''
  currentTab.value = null
}

const cancelPublish = () => {
  ElMessage.info('已取消发布')
}

const buildPublishData = (tab) => ({
  type: tab.selectedPlatform,
  title: tab.title.trim(),
  note: tab.note.trim(),
  tags: tab.selectedTopics,
  fileList: tab.fileList.map(file => file.path),
  accountList: tab.selectedAccounts.map(accountId => {
    const account = accountStore.accounts.find(acc => acc.id === accountId)
    return account ? account.filePath : accountId
  }),
  enableTimer: tab.scheduleEnabled ? 1 : 0,
  videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1,
  dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'],
  startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0,
  category: tab.isOriginal ? 1 : 0,
  productLink: tab.productLink.trim(),
  productTitle: tab.productTitle.trim(),
  isDraft: tab.isDraft
})

const validatePublish = (tab) => {
  const label = contentTypeLabel(tab)
  if (tab.fileList.length === 0) throw new Error(`请先上传${label}文件`)
  if (!tab.title.trim()) throw new Error('请输入标题')
  if (tab.contentType === 'note' && tab.selectedPlatform === 2) throw new Error('视频号暂不支持图文发布')
  if (!tab.selectedPlatform) throw new Error('请选择发布平台')
  if (tab.selectedAccounts.length === 0) throw new Error('请选择发布账号')
}

const confirmPublish = async (tab) => {
  if (tab.publishing) throw new Error('正在发布中，请稍候')
  tab.publishing = true
  try {
    validatePublish(tab)
    const endpoint = tab.contentType === 'note' ? '/postNote' : '/postVideo'
    await http.post(endpoint, buildPublishData(tab))
    tab.publishStatus = {
      message: `${contentTypeLabel(tab)}发布任务已提交`,
      type: 'success'
    }
    tab.fileList = []
    tab.title = ''
    tab.note = ''
    tab.selectedTopics = []
    tab.selectedAccounts = []
    tab.scheduleEnabled = false
    ElMessage.success(tab.publishStatus.message)
  } catch (error) {
    const message = error.message || '请检查网络连接'
    tab.publishStatus = {
      message: `发布失败：${message}`,
      type: 'error'
    }
    ElMessage.error(tab.publishStatus.message)
    throw error
  } finally {
    tab.publishing = false
  }
}

const cancelBatchPublish = () => {
  isCancelled.value = true
  ElMessage.info('正在取消发布...')
}

const batchPublish = async () => {
  if (batchPublishing.value) return
  batchPublishing.value = true
  currentPublishingTab.value = null
  publishProgress.value = 0
  publishResults.value = []
  isCancelled.value = false
  batchPublishDialogVisible.value = true

  try {
    for (let i = 0; i < tabs.length; i++) {
      const tab = tabs[i]
      if (isCancelled.value) {
        publishResults.value.push({ label: tab.label, status: 'cancelled', message: '已取消' })
        continue
      }
      currentPublishingTab.value = tab
      publishProgress.value = Math.floor((i / tabs.length) * 100)
      try {
        await confirmPublish(tab)
        publishResults.value.push({ label: tab.label, status: 'success', message: '发布任务已提交' })
      } catch (error) {
        publishResults.value.push({ label: tab.label, status: 'error', message: error.message || '发布失败' })
      }
    }
    publishProgress.value = 100
  } finally {
    batchPublishing.value = false
    isCancelled.value = false
  }
}

const formatFileSize = (size) => {
  const mb = Number(size || 0) / 1024 / 1024
  return `${mb.toFixed(2)}MB`
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.publish-center {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tab-management,
.publish-content {
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.tab-management {
  margin-bottom: 20px;
  padding: 15px 20px;
}

.tab-header,
.tab-list,
.tab-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tab-header {
  justify-content: space-between;
  align-items: flex-start;
}

.tab-list {
  flex: 1;
  flex-wrap: wrap;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #f5f7fa;
  color: #606266;
  cursor: pointer;
}

.tab-item.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.close-icon {
  font-size: 12px;
}

.publish-content {
  flex: 1;
  padding: 20px;
}

.publish-form {
  max-width: 820px;
  margin: 0 auto;
}

.status-alert,
.form-section {
  margin-bottom: 24px;
}

.form-section h3 {
  margin: 0 0 10px;
  color: $text-primary;
  font-size: 16px;
  font-weight: 600;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.uploaded-files,
.material-list,
.account-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.uploaded-files {
  margin-top: 14px;
}

.file-item,
.material-item,
.account-item {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 4px;
  background: #f5f7fa;
}

.file-item {
  gap: 12px;
}

.file-item .el-link {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  margin-right: auto;
  color: #909399;
  font-size: 13px;
}

.tag-field {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tag-list {
  display: flex;
  min-height: 32px;
  flex-wrap: wrap;
  gap: 8px;
}

.platform-radios {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}

.muted {
  margin-left: 4px;
  color: #909399;
  font-size: 12px;
}

.compact-options {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}

.mt-8 {
  margin-top: 8px;
}

.schedule-controls,
.schedule-settings {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.schedule-settings {
  padding: 15px;
  border-radius: 4px;
  background: #f5f7fa;
}

.schedule-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.schedule-item .label {
  width: 90px;
  color: #606266;
}

.schedule-times {
  flex-wrap: wrap;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.upload-options-content,
.custom-topic-input {
  display: flex;
  gap: 12px;
}

.upload-options-content .el-button {
  flex: 1;
}

.local-upload {
  width: 100%;
}

:deep(.local-upload .el-upload-dragger) {
  width: 100%;
}

.material-info {
  min-width: 0;
}

.material-name {
  max-width: 620px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #303133;
}

.material-details {
  display: flex;
  gap: 14px;
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}

.account-item {
  justify-content: space-between;
}

.account-name {
  margin-right: 10px;
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 10px;
  margin-top: 18px;
}

.publish-progress {
  padding: 10px 0;
}

.current-publishing {
  margin: 14px 0;
  text-align: center;
  color: #606266;
}

.publish-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
  padding-top: 10px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
}

.result-item.success {
  color: #67c23a;
}

.result-item.error {
  color: #f56c6c;
}

.result-item.cancelled {
  color: #909399;
}

.result-item .label {
  font-weight: 600;
}

@media (max-width: 720px) {
  .tab-header,
  .schedule-item {
    align-items: stretch;
    flex-direction: column;
  }

  .tab-actions,
  .upload-options-content,
  .custom-topic-input {
    width: 100%;
  }

  .schedule-item .label {
    width: auto;
  }
}
</style>
