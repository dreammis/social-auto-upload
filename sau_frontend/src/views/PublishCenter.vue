<template>
  <div class="publish-center">
    <!-- Tab管理区域 -->
    <div class="tab-management">
      <div class="tab-header">
        <div class="tab-list">
          <div 
            v-for="tab in tabs" 
            :key="tab.name"
            :class="['tab-item', { active: activeTab === tab.name }]"
            @click="activeTab = tab.name"
          >
            <span>{{ tab.label }}</span>
            <el-icon 
              v-if="tabs.length > 1"
              class="close-icon" 
              @click.stop="removeTab(tab.name)"
            >
              <Close />
            </el-icon>
          </div>
        </div>
        <div class="tab-actions">
          <el-button 
            type="primary" 
            size="small" 
            @click="addTab"
            class="add-tab-btn"
          >
            <el-icon><Plus /></el-icon>
            添加Tab
          </el-button>
          <el-button 
            type="success" 
            size="small" 
            @click="batchPublish"
            :loading="batchPublishing"
            class="batch-publish-btn"
          >
            批量发布
          </el-button>
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="publish-content">
      <div class="tab-content-wrapper">
        <div 
          v-for="tab in tabs" 
          :key="tab.name"
          v-show="activeTab === tab.name"
          class="tab-content"
        >
          <!-- 发布状态提示 -->
          <div v-if="tab.publishStatus" class="publish-status">
            <el-alert
              :title="tab.publishStatus.message"
              :type="tab.publishStatus.type"
              :closable="false"
              show-icon
            />
          </div>

          <!-- 视频上传区域 -->
          <div class="upload-section">
            <h3>图文/视频</h3>
            <div class="upload-options">
              <el-button type="primary" @click="selectLocalUpload(tab)" class="upload-btn">
                <el-icon><Upload /></el-icon>
                本地上传
              </el-button>
              <el-button type="success" @click="selectMaterialLibrary(tab)" class="upload-btn">
                <el-icon><Folder /></el-icon>
                素材库
              </el-button>
            </div>
            
            <!-- 已上传文件列表 -->
            <div v-if="tab.fileList.length > 0" class="uploaded-files">
              <h4>已上传文件：</h4>
              <div class="file-list">
                <div v-for="(file, index) in tab.fileList" :key="index" class="file-item">
                  <el-link :href="file.url" target="_blank" type="primary">{{ file.name }}</el-link>
                  <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(2) }}MB</span>
                  <el-button type="danger" size="small" @click="removeFile(tab, index)">删除</el-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 上传选项弹窗已移除，直接显示本地上传和素材库按钮 -->

          <!-- 本地上传弹窗 -->
          <el-dialog
            v-model="localUploadVisible"
            title="本地上传"
            width="600px"
            class="local-upload-dialog"
          >
            <el-upload
              class="video-upload"
              drag
              :auto-upload="true"
              :action="`${apiBaseUrl}/upload`"
              :on-success="(response, file) => handleUploadSuccess(response, file, currentUploadTab)"
              :on-error="handleUploadError"
              multiple
              accept="video/*"
              :headers="authHeaders"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                将视频文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持MP4、AVI等视频格式，可上传多个文件
                </div>
              </template>
            </el-upload>
          </el-dialog>

          <!-- 批量发布进度对话框 -->
          <el-dialog
            v-model="batchPublishDialogVisible"
            title="批量发布进度"
            width="500px"
            :close-on-click-modal="false"
            :close-on-press-escape="false"
            :show-close="false"
          >
            <div class="publish-progress">
              <el-progress 
                :percentage="publishProgress"
                :status="publishProgress === 100 ? 'success' : ''"
              />
              <div v-if="currentPublishingTab" class="current-publishing">
                正在发布：{{ currentPublishingTab.label }}
              </div>
              
              <!-- 发布结果列表 -->
              <div class="publish-results" v-if="publishResults.length > 0">
                <div 
                  v-for="(result, index) in publishResults" 
                  :key="index"
                  :class="['result-item', result.status]"
                >
                  <el-icon v-if="result.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
                  <el-icon v-else><InfoFilled /></el-icon>
                  <span class="label">{{ result.label }}</span>
                  <span class="message">{{ result.message }}</span>
                </div>
              </div>
            </div>
            
            <template #footer>
              <div class="dialog-footer">
                <el-button 
                  @click="cancelBatchPublish" 
                  :disabled="publishProgress === 100"
                >
                  取消发布
                </el-button>
                <el-button 
                  type="primary" 
                  @click="batchPublishDialogVisible = false"
                  v-if="publishProgress === 100"
                >
                  关闭
                </el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 素材库选择弹窗 -->
          <el-dialog
            v-model="materialLibraryVisible"
            title="选择素材"
            width="800px"
            class="material-library-dialog"
          >
            <div class="material-library-content">
              <el-checkbox-group v-model="selectedMaterials">
                <div class="material-list">
                  <div
                    v-for="material in materials"
                    :key="material.id"
                    class="material-item"
                  >
                    <el-checkbox :label="material.id" class="material-checkbox">
                      <div class="material-info">
                        <div class="material-name">{{ material.filename }}</div>
                        <div class="material-details">
                          <span class="file-size">{{ material.filesize }}MB</span>
                          <span class="upload-time">{{ material.upload_time }}</span>
                        </div>
                      </div>
                    </el-checkbox>
                  </div>
                </div>
              </el-checkbox-group>
            </div>
            <template #footer>
              <div class="dialog-footer">
                <el-button @click="materialLibraryVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmMaterialSelection">确定</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 平台选择 -->
          <div class="platform-section">
            <h3>平台</h3>
            <el-checkbox-group v-model="tab.selectedPlatforms" class="platform-checkboxes">
              <el-checkbox 
                v-for="platform in platforms" 
                :key="platform.key"
                :label="platform.key"
                class="platform-checkbox"
              >
                {{ platform.name }}
              </el-checkbox>
            </el-checkbox-group>
          </div>

          <!-- 账号选择 -->
          <div class="account-section">
            <h3>账号</h3>
            <div class="account-display">
              <div class="selected-accounts">
                <el-tag
                  v-for="(account, index) in tab.selectedAccounts"
                  :key="index"
                  closable
                  @close="removeAccount(tab, index)"
                  class="account-tag"
                >
                  {{ getAccountDisplayName(account) }}
                </el-tag>
              </div>
              <el-button 
                type="primary" 
                plain 
                @click="openAccountDialog(tab)"
                class="select-account-btn"
                :disabled="tab.selectedPlatforms.length === 0"
              >
                选择账号
              </el-button>
            </div>
          </div>

          <!-- 账号选择弹窗 -->
          <el-dialog
            v-model="accountDialogVisible"
            title="选择账号"
            width="600px"
            class="account-dialog"
          >
            <div class="account-dialog-content">
              <!-- 只有在有多个账号时才显示全选按钮 -->
              <el-checkbox 
                v-if="availableAccounts.length > 1" 
                v-model="selectAllAccounts" 
                @change="handleSelectAllChange" 
                class="select-all-checkbox"
              >全选</el-checkbox>
              <el-checkbox-group v-model="tempSelectedAccounts">
                <div class="account-list">
                  <el-checkbox
                    v-for="account in availableAccounts"
                    :key="account.id"
                    :label="account.id"
                    class="account-item"
                  >
                    <div class="account-info">
                      <span class="account-name">{{ account.name }}</span>                       
                    </div>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="accountDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmAccountSelection">确定</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 单平台特有功能 -->
          <template v-if="tab.selectedPlatforms.length <= 1">
            <!-- 草稿选项 (仅在视频号可见) -->
            <div v-if="tab.selectedPlatforms.includes(2)" class="draft-section">
              <el-checkbox
                v-model="tab.isDraft"
                label="视频号仅保存草稿(用手机发布)"
                class="draft-checkbox"
              />
            </div>
          </template>

          <!-- 标题输入 -->
          <div class="title-section">
            <h3>标题</h3>
            <el-input
              v-model="tab.title"
              type="textarea"
              :rows="3"
              placeholder="请输入标题"
              maxlength="100"
              show-word-limit
              class="title-input"
            />
          </div>
          
          <!-- 正文输入 -->
          <div v-if="tab.selectedPlatforms.includes(1) || tab.selectedPlatforms.length <= 1" class="content-section">
            <h3>正文</h3>
            <el-input
              v-model="tab.content"
              type="textarea"
              :rows="6"
              placeholder="请输入正文内容"
              maxlength="500"
              show-word-limit
              class="content-input"
            />
          </div>

          <!-- 话题输入 -->
          <div class="topic-section">
            <h3>话题</h3>
            <div class="topic-display">
              <div class="selected-topics">
                <el-tag
                  v-for="(topic, index) in tab.selectedTopics"
                  :key="index"
                  closable
                  @close="removeTopic(tab, index)"
                  class="topic-tag"
                >
                  #{{ topic }}
                </el-tag>
              </div>
              <el-button 
                type="primary" 
                plain 
                @click="openTopicDialog(tab)"
                class="select-topic-btn"
              >
                添加话题
              </el-button>
            </div>
          </div>
          
          <!-- 添加话题弹窗 -->
          <el-dialog
            v-model="topicDialogVisible"
            title="添加话题"
            width="600px"
            class="topic-dialog"
          >
            <div class="topic-dialog-content">
              <!-- 自定义话题输入 -->
              <div class="custom-topic-input">
                <el-input
                  v-model="customTopic"
                  placeholder="输入自定义话题"
                  class="custom-input"
                >
                  <template #prepend>#</template>
                </el-input>
                <el-button type="primary" @click="addCustomTopic">添加</el-button>
              </div>

              <!-- 推荐话题 -->
              <div class="recommended-topics">
                <h4>推荐话题</h4>
                <div class="topic-grid">
                  <el-button
                    v-for="topic in recommendedTopics"
                    :key="topic"
                    :type="currentTab?.selectedTopics?.includes(topic) ? 'primary' : 'default'"
                    @click="toggleRecommendedTopic(topic)"
                    class="topic-btn"
                  >
                    {{ topic }}
                  </el-button>
                </div>
              </div>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="topicDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmTopicSelection">确定</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- 单平台特有功能 - 继续 -->
          <template v-if="tab.selectedPlatforms.length <= 1">
            <!-- 标签 (仅在抖音可见) -->
            <div v-if="tab.selectedPlatforms.includes(3)" class="product-section">
              <h3>商品链接</h3>
              <el-input
                v-model="tab.productTitle"
                type="text"
                :rows="1"
                placeholder="请输入商品名称"
                maxlength="200"
                class="product-name-input"
              />
              <el-input
                v-model="tab.productLink"
                type="text"
                :rows="1"
                placeholder="请输入商品链接"
                maxlength="200"
                class="product-link-input"
              />
            </div>

            <!-- 定时发布 -->
            <div class="schedule-section">
              <h3>定时发布</h3>
              <div class="schedule-controls">
                <el-switch
                  v-model="tab.scheduleEnabled"
                  active-text="定时发布"
                  inactive-text="立即发布"
                />
                <div v-if="tab.scheduleEnabled" class="schedule-settings">
                  <div class="schedule-item">
                    <span class="label">每天发布视频数：</span>
                    <el-select v-model="tab.videosPerDay" placeholder="选择发布数量">
                      <el-option
                        v-for="num in 55"
                        :key="num"
                        :label="num"
                        :value="num"
                      />
                    </el-select>
                  </div>
                  <div class="schedule-item">
                    <span class="label">每天发布时间：</span>
                    <el-time-select
                      v-for="(time, index) in tab.dailyTimes"
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
                    <span class="label">开始天数：</span>
                    <el-select v-model="tab.startDays" placeholder="选择开始天数">
                      <el-option :label="'明天'" :value="0" />
                      <el-option :label="'后天'" :value="1" />
                    </el-select>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button size="small" @click="cancelPublish(tab)">取消</el-button>
            <el-button
              size="small"
              type="primary"
              @click="confirmPublish(tab)"
              :loading="tab.publishing || false"
            >
              {{ tab.publishing ? '发布中...' : '发布' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { Upload, Plus, Close, Folder } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { materialApi } from '@/api/material'
import { publishApi } from '@/api/publish'
import { accountApi } from '@/api/account'

// API base URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

// Authorization headers
const authHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

// 当前激活的tab
const activeTab = ref('tab1')

// tab计数器
let tabCounter = 1

// 获取应用状态管理
const appStore = useAppStore()

// 上传相关状态
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const currentUploadTab = ref(null)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)

// 批量发布相关状态
const batchPublishing = ref(false)
const batchPublishMessage = ref('')
const batchPublishType = ref('info')

// 平台列表 - 对应后端type字段
const platforms = [
  { key: 3, name: '抖音' },
  { key: 4, name: '快手' },
  { key: 2, name: '视频号' },
  { key: 1, name: '小红书' },
  { key: 5, name: 'TikTok' },
  { key: 6, name: 'Instagram' },
  { key: 7, name: 'Facebook' },
  { key: 8, name: '哔哩哔哩' },
  { key: 9, name: '百家号' }
]

const defaultTabInit = {
  name: 'tab1',
  label: '发布1',
  fileList: [], // 后端返回的文件名列表
  displayFileList: [], // 用于显示的文件列表
  selectedAccounts: [], // 选中的账号ID列表
  selectedPlatforms: [], // 选中的平台列表（多选）
  title: '',
  content: '', // 正文内容
  productLink: '', // 商品链接
  productTitle: '', // 商品名称
  selectedTopics: [], // 话题列表（不带#号）
  scheduleEnabled: false, // 定时发布开关
  videosPerDay: 1, // 每天发布视频数量
  dailyTimes: ['10:00'], // 每天发布时间点列表
  startDays: 0, // 从今天开始计算的发布天数，0表示明天，1表示后天
  publishStatus: null, // 发布状态，包含message和type
  publishing: false, // 发布状态，用于控制按钮loading效果
  isDraft: false // 是否保存为草稿，仅视频号平台可见
}

// helper to create a fresh deep-copied tab from defaultTabInit
const makeNewTab = () => {
  // prefer structuredClone when available (newer browsers/node), fallback to JSON
  try {
    return typeof structuredClone === 'function' ? structuredClone(defaultTabInit) : JSON.parse(JSON.stringify(defaultTabInit))
  } catch (e) {
    return JSON.parse(JSON.stringify(defaultTabInit))
  }
}

// tab页数据 - 默认只有一个tab (use deep copy to avoid shared refs)
const tabs = reactive([
  makeNewTab()
])

// 账号相关状态
const accountDialogVisible = ref(false)
const tempSelectedAccounts = ref([])
const currentTab = ref(null)
const selectAllAccounts = ref(false)

// 监听平台选择变化，当平台改变时清空已选择的账号
watch(() => currentTab.value?.selectedPlatforms, (newPlatforms, oldPlatforms) => {
  if (currentTab.value && JSON.stringify(newPlatforms) !== JSON.stringify(oldPlatforms) && oldPlatforms !== undefined) {
    // 平台发生变化，清空已选择的账号
    currentTab.value.selectedAccounts = []
    ElMessage.info('平台已切换，请重新选择账号')
  }
}, { deep: true })

// 获取账号状态管理
const accountStore = useAccountStore()

// 加载账号数据
const loadAccounts = async () => {
  try {
    const response = await accountApi.getAccounts()
    if (response.code === 200) {
      accountStore.setAccounts(response.data)
    } else {
      ElMessage.error('加载账号数据失败：' + response.msg)
    }
  } catch (error) {
    console.error('加载账号数据失败：', error)
    ElMessage.error('加载账号数据失败')
  }
}

// 组件挂载时加载账号数据
onMounted(() => {
  loadAccounts()
})

// 根据选择的平台获取可用账号列表
const availableAccounts = computed(() => {
  const platformMap = {
    3: '抖音',
    2: '视频号',
    1: '小红书',
    4: '快手',
    5: 'TikTok',
    6: 'Instagram',
    7: 'Facebook',
    8: '哔哩哔哩',
    9: '百家号'
  }
  
  // 获取当前选中的所有平台对应的平台名称
  const selectedPlatforms = currentTab.value?.selectedPlatforms || []
  const platformNames = selectedPlatforms.map(platformKey => platformMap[platformKey]).filter(Boolean)
  
  // 如果没有选中平台，返回所有账号
  if (platformNames.length === 0) {
    return []
  }
  
  // 返回所有选中平台的可用账号
  return accountStore.accounts.filter(acc => platformNames.includes(acc.platform))
})

// 话题相关状态
const topicDialogVisible = ref(false)
const customTopic = ref('')

// 推荐话题列表
const recommendedTopics = [
  '游戏', '电影', '音乐', '美食', '旅行', '文化',
  '科技', '生活', '娱乐', '体育', '教育', '艺术',
  '健康', '时尚', '美妆', '摄影', '宠物', '汽车'
]

// 添加新tab
const addTab = () => {
  tabCounter++
  const newTab = makeNewTab()
  newTab.name = `tab${tabCounter}`
  newTab.label = `发布${tabCounter}`
  tabs.push(newTab)
  activeTab.value = newTab.name
}

// 删除tab
const removeTab = (tabName) => {
  const index = tabs.findIndex(tab => tab.name === tabName)
  if (index > -1) {
    tabs.splice(index, 1)
    // 如果删除的是当前激活的tab，切换到第一个tab
    if (activeTab.value === tabName && tabs.length > 0) {
      activeTab.value = tabs[0].name
    }
  }
}

// 处理文件上传成功
const handleUploadSuccess = (response, file, tab) => {
  if (response.code === 200) {
    // 获取文件路径
    const filePath = response.data.path || response.data
    // 从路径中提取文件名
    const filename = filePath.split('/').pop()
    
    // 保存文件信息到fileList，包含文件路径和其他信息
    const fileInfo = {
      name: file.name,
      url: materialApi.getMaterialPreviewUrl(filename), // 使用getMaterialPreviewUrl生成预览URL
      path: filePath,
      size: file.size,
      type: file.type
    }
    
    // 添加到文件列表
    tab.fileList.push(fileInfo)
    
    // 更新显示列表
    tab.displayFileList = [...tab.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
    
    ElMessage.success('文件上传成功')
    console.log('上传成功:', fileInfo)
  } else {
    ElMessage.error(response.msg || '上传失败')
  }
}

// 处理文件上传失败
const handleUploadError = (error) => {
  ElMessage.error('文件上传失败')
  console.error('上传错误:', error)
}

// 删除已上传文件
const removeFile = (tab, index) => {
  // 从文件列表中删除
  tab.fileList.splice(index, 1)
  
  // 更新显示列表
  tab.displayFileList = [...tab.fileList.map(item => ({
    name: item.name,
    url: item.url
  }))]
  
  ElMessage.success('文件删除成功')
}

// 话题相关方法
// 打开添加话题弹窗
const openTopicDialog = (tab) => {
  currentTab.value = tab
  topicDialogVisible.value = true
}

// 添加自定义话题
const addCustomTopic = () => {
  if (!customTopic.value.trim()) {
    ElMessage.warning('请输入话题内容')
    return
  }
  if (currentTab.value && !currentTab.value.selectedTopics.includes(customTopic.value.trim())) {
    currentTab.value.selectedTopics.push(customTopic.value.trim())
    customTopic.value = ''
    ElMessage.success('话题添加成功')
  } else {
    ElMessage.warning('话题已存在')
  }
}

// 切换推荐话题
const toggleRecommendedTopic = (topic) => {
  if (!currentTab.value) return
  
  const index = currentTab.value.selectedTopics.indexOf(topic)
  if (index > -1) {
    currentTab.value.selectedTopics.splice(index, 1)
  } else {
    currentTab.value.selectedTopics.push(topic)
  }
}

// 删除话题
const removeTopic = (tab, index) => {
  tab.selectedTopics.splice(index, 1)
}

// 确认添加话题
const confirmTopicSelection = () => {
  topicDialogVisible.value = false
  customTopic.value = ''
  currentTab.value = null
  ElMessage.success('添加话题完成')
}

// 账号选择相关方法
// 打开账号选择弹窗
const openAccountDialog = (tab) => {
  currentTab.value = tab
  tempSelectedAccounts.value = [...tab.selectedAccounts]
  // 检查是否已经全选
  selectAllAccounts.value = tempSelectedAccounts.value.length === availableAccounts.value.length && availableAccounts.value.length > 0
  accountDialogVisible.value = true
}

// 处理全选/取消全选
const handleSelectAllChange = (checked) => {
  if (checked) {
    // 全选：将所有可用账号的ID添加到tempSelectedAccounts
    tempSelectedAccounts.value = availableAccounts.value.map(account => account.id)
  } else {
    // 取消全选：清空tempSelectedAccounts
    tempSelectedAccounts.value = []
  }
}

// 确认账号选择
const confirmAccountSelection = () => {
  if (currentTab.value) {
    currentTab.value.selectedAccounts = [...tempSelectedAccounts.value]
  }
  accountDialogVisible.value = false
  currentTab.value = null
  ElMessage.success('账号选择完成')
}

// 删除选中的账号
const removeAccount = (tab, index) => {
  tab.selectedAccounts.splice(index, 1)
}

// 获取账号显示名称
const getAccountDisplayName = (accountId) => {
  const account = accountStore.accounts.find(acc => acc.id === accountId)
  return account ? account.name : accountId
}

// 取消发布
const cancelPublish = (tab) => {
  ElMessage.info('已取消发布')
}

// 平台类型到平台名称的映射
const platformTypeMap = {
  1: 'xiaohongshu',
  2: 'tencent',
  3: 'douyin',
  4: 'kuaishou',
  5: 'tiktok',
  6: 'instagram',
  7: 'facebook',
  8: 'bilibili',
  9: 'baijiahao'
}

// 确认发布
const confirmPublish = async (tab) => {
  // 防止重复点击
  if (tab.publishing) {
    return Promise.reject(new Error('正在发布中，请稍候...'))
  }

  tab.publishing = true // 设置发布状态为进行中

  return new Promise((resolve, reject) => {
    // 数据验证
    if (tab.fileList.length === 0) {
      ElMessage.error('请先上传视频文件')
      tab.publishing = false // 重置发布状态
      reject(new Error('请先上传视频文件'))
      return
    }
    if (!tab.title.trim()) {
      ElMessage.error('请输入标题')
      tab.publishing = false // 重置发布状态
      reject(new Error('请输入标题'))
      return
    }
    if (!tab.selectedPlatforms || tab.selectedPlatforms.length === 0) {
      ElMessage.error('请选择至少一个发布平台')
      tab.publishing = false // 重置发布状态
      reject(new Error('请选择至少一个发布平台'))
      return
    }
    if (tab.selectedAccounts.length === 0) {
      ElMessage.error('请选择发布账号')
      tab.publishing = false // 重置发布状态
      reject(new Error('请选择发布账号'))
      return
    }

    // 如果只选择了一个平台，使用原有的单平台发布API
    if (tab.selectedPlatforms.length === 1) {
      const platformType = tab.selectedPlatforms[0]
      // 构造发布数据，符合后端API格式
      const publishData = {
        type: platformType,
        title: tab.title,
        text: tab.content.trim() || '', // 正文内容，后端API使用text字段
        tags: tab.selectedTopics, // 不带#号的话题列表
        fileList: tab.fileList.map(file => file.path), // 只发送文件路径
        accountList: tab.selectedAccounts.map(accountId => {
          const account = accountStore.accounts.find(acc => acc.id === accountId)
          return account ? account.filePath : accountId
        }), // 发送账号的文件路径
        enableTimer: tab.scheduleEnabled ? 1 : 0, // 是否启用定时发布，开启传1，不开启传0
        videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1, // 每天发布视频数量，1-55
        dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'], // 每天发布时间点
        startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0, // 从今天开始计算的发布天数，0表示明天，1表示后天
        category: 0, //表示非原创
        productLink: tab.productLink.trim() || '', // 商品链接
        productTitle: tab.productTitle.trim() || '', // 商品名称
        isDraft: tab.isDraft // 是否保存为草稿，仅视频号平台使用
      }

      // 调用后端发布API
      publishApi.postVideo(publishData)
        .then(data => {
        if (data.code === 200) {
          tab.publishStatus = {
            message: '发布成功',
            type: 'success'
          }
          // 清空当前tab的数据
          tab.fileList = []
          tab.displayFileList = []
          tab.title = ''
          tab.content = ''
          tab.selectedTopics = []
          tab.selectedAccounts = []
          tab.selectedPlatforms = []
          tab.scheduleEnabled = false
          resolve()
        } else {
          tab.publishStatus = {
            message: `发布失败：${data.msg || '发布失败'}`,
            type: 'error'
          }
          reject(new Error(data.msg || '发布失败'))
        }
      })
      .catch(error => {
        console.error('发布错误:', error)
        tab.publishStatus = {
          message: '发布失败，请检查网络连接',
          type: 'error'
        }
        reject(error)
      })
      .finally(() => {
        tab.publishing = false // 重置发布状态
      })
    } else {
      // 多个平台发布，使用新的批量发布API
      const platformNames = tab.selectedPlatforms.map(type => platformTypeMap[type])
      
      // 构建账号文件字典：key为平台名称，value为该平台对应的账号文件列表
      const accountFiles = {}
      platformNames.forEach(platformName => {
        accountFiles[platformName] = tab.selectedAccounts.map(accountId => {
          const account = accountStore.accounts.find(acc => acc.id === accountId)
          return account ? account.filePath : accountId
        })
      })
      
      // 构造发布数据，符合后端批量发布API格式，只包含公共参数
      const publishData = {
        platforms: platformNames,
        accountFiles: accountFiles,
        fileType: 2, // 默认视频类型
        files: tab.fileList.map(file => file.path), // 只发送文件路径
        title: tab.title,
        text: tab.content.trim() || '', // 正文内容，后端API使用text字段
        tags: tab.selectedTopics.join(','), // 标签用逗号隔开
        thumbnail: '', // 缩略图路径
        location: 1, // 默认国内
        // 多平台发布不支持定时发布和其他单平台特有参数
        enableTimer: 0,
        videosPerDay: 1,
        dailyTimes: ['10:00'],
        startDays: 0
      }

      // 调用后端批量发布API
      publishApi.postVideosToMultiplePlatforms(publishData)
        .then(data => {
        if (data.code === 200) {
          tab.publishStatus = {
            message: '发布成功',
            type: 'success'
          }
          // 清空当前tab的数据
          tab.fileList = []
          tab.displayFileList = []
          tab.title = ''
          tab.content = ''
          tab.selectedTopics = []
          tab.selectedAccounts = []
          tab.selectedPlatforms = []
          tab.scheduleEnabled = false
          resolve()
        } else {
          tab.publishStatus = {
            message: `发布失败：${data.msg || '发布失败'}`,
            type: 'error'
          }
          reject(new Error(data.msg || '发布失败'))
        }
      })
      .catch(error => {
        console.error('发布错误:', error)
        tab.publishStatus = {
          message: '发布失败，请检查网络连接',
          type: 'error'
        }
        reject(error)
      })
      .finally(() => {
        tab.publishing = false // 重置发布状态
      })
    }
  })
}

// 选择本地上传
const selectLocalUpload = (tab) => {
  currentUploadTab.value = tab
  localUploadVisible.value = true
}

// 选择素材库
const selectMaterialLibrary = async (tab) => {
  currentUploadTab.value = tab
  
  // 如果素材库为空，先获取素材数据
  if (materials.value.length === 0) {
    try {
      const response = await materialApi.getAllMaterials()
      if (response.code === 200) {
        appStore.setMaterials(response.data)
      } else {
        ElMessage.error('获取素材列表失败')
        return
      }
    } catch (error) {
      console.error('获取素材列表出错:', error)
      ElMessage.error('获取素材列表失败')
      return
    }
  }
  
  selectedMaterials.value = []
  materialLibraryVisible.value = true
}

// 确认素材选择
const confirmMaterialSelection = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('请选择至少一个素材')
    return
  }
  
  if (currentUploadTab.value) {
    // 将选中的素材添加到当前tab的文件列表
    selectedMaterials.value.forEach(materialId => {
      const material = materials.value.find(m => m.id === materialId)
      if (material) {
        const fileInfo = {
          name: material.filename,
          url: materialApi.getMaterialPreviewUrl(material.file_path.split('/').pop()),
          path: material.file_path,
          size: material.filesize * 1024 * 1024, // 转换为字节
          type: 'video/mp4'
        }
        
        // 检查是否已存在相同文件
        const exists = currentUploadTab.value.fileList.some(file => file.path === fileInfo.path)
        if (!exists) {
          currentUploadTab.value.fileList.push(fileInfo)
        }
      }
    })
    
    // 更新显示列表
    currentUploadTab.value.displayFileList = [...currentUploadTab.value.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
  }
  
  const addedCount = selectedMaterials.value.length
  materialLibraryVisible.value = false
  selectedMaterials.value = []
  currentUploadTab.value = null
  ElMessage.success(`已添加 ${addedCount} 个素材`)
}

// 批量发布对话框状态
const batchPublishDialogVisible = ref(false)
const currentPublishingTab = ref(null)
const publishProgress = ref(0)
const publishResults = ref([])
const isCancelled = ref(false)

// 取消批量发布
const cancelBatchPublish = () => {
  isCancelled.value = true
  ElMessage.info('正在取消发布...')
}

// 批量发布方法
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
      if (isCancelled.value) {
        publishResults.value.push({
          label: tabs[i].label,
          status: 'cancelled',
          message: '已取消'
        })
        continue
      }

      const tab = tabs[i]
      currentPublishingTab.value = tab
      publishProgress.value = Math.floor((i / tabs.length) * 100)
      
      try {
        await confirmPublish(tab)
        publishResults.value.push({
          label: tab.label,
          status: 'success',
          message: '发布成功'
        })
      } catch (error) {
        publishResults.value.push({
          label: tab.label,
          status: 'error',
          message: error.message
        })
        // 不立即返回，继续显示发布结果
      }
    }
    
    publishProgress.value = 100
    
    // 统计发布结果
    const successCount = publishResults.value.filter(r => r.status === 'success').length
    const failCount = publishResults.value.filter(r => r.status === 'error').length
    const cancelCount = publishResults.value.filter(r => r.status === 'cancelled').length
    
    if (isCancelled.value) {
      ElMessage.warning(`发布已取消：${successCount}个成功，${failCount}个失败，${cancelCount}个未执行`)
    } else if (failCount > 0) {
      ElMessage.error(`发布完成：${successCount}个成功，${failCount}个失败`)
    } else {
      ElMessage.success('所有Tab发布成功')
      setTimeout(() => {
        batchPublishDialogVisible.value = false
      }, 1000)
    }
    
  } catch (error) {
    console.error('批量发布出错:', error)
    ElMessage.error('批量发布出错，请重试')
  } finally {
    batchPublishing.value = false
    isCancelled.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.publish-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  
  // Tab管理区域
  .tab-management {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
    padding: 15px 20px;
    
    .tab-header {
      display: flex;
      align-items: flex-start;
      gap: 15px;
      
      .tab-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        flex: 1;
        min-width: 0;
        
        .tab-item {
           display: flex;
           align-items: center;
           gap: 6px;
           padding: 6px 12px;
           background-color: #f5f7fa;
           border: 1px solid #dcdfe6;
           border-radius: 4px;
           cursor: pointer;
           transition: all 0.3s;
           font-size: 14px;
           height: 32px;
           
           &:hover {
             background-color: #ecf5ff;
             border-color: #b3d8ff;
           }
           
           &.active {
             background-color: #1C9399;
             border-color: #1C9399;
             color: #fff;
             
             .close-icon {
               color: #fff;
               
               &:hover {
                 background-color: rgba(255, 255, 255, 0.2);
               }
             }
           }
           
           .close-icon {
             padding: 2px;
             border-radius: 2px;
             cursor: pointer;
             transition: background-color 0.3s;
             font-size: 12px;
             
             &:hover {
               background-color: rgba(0, 0, 0, 0.1);
             }
           }
         }
       }
       
      .tab-actions {
        display: flex;
        gap: 10px;
        flex-shrink: 0;
        
        .add-tab-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
          width: 10rem;
          border-radius: 4px;
          
          // 正常状态样式
          background-color: #1C9399;
          border-color: #1C9399;
          color: #FFFFFF;
          
          &:hover {
            background-color: #48D1CC;
            border-color: #48D1CC;
            color: #FFFFFF;
          }
          
          &:active {
            background-color: #166B6F;
            border-color: #166B6F;
            color: #FFFFFF;
          }
        }

        .batch-publish-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
          width: 10rem;
          border-radius: 4px;
          
          // 正常状态样式
          background-color: transparent;
          border-color: #1C9399;
          color: #1C9399;
          
          &:hover {
            background-color: #1C9399;
            border-color: #1C9399;
            color: #FFFFFF;
          }
          
          &:active {
            background-color: #166B6F;
            border-color: #166B6F;
            color: #FFFFFF;
          }
        }
      }
    }
  }
  
  // 批量发布进度对话框样式
  .publish-progress {
    padding: 20px;
    
    .current-publishing {
      margin: 15px 0;
      text-align: center;
      color: #606266;
    }

    .publish-results {
      margin-top: 20px;
      border-top: 1px solid #EBEEF5;
      padding-top: 15px;
      max-height: 300px;
      overflow-y: auto;

      .result-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: #606266;

        .el-icon {
          margin-right: 8px;
        }

        .label {
          margin-right: 10px;
          font-weight: 500;
        }

        .message {
          color: #909399;
        }

        &.success {
          color: #67C23A;
        }

        &.error {
          color: #F56C6C;
        }

        &.cancelled {
          color: #909399;
        }
      }
    }
  }

  .dialog-footer {
    text-align: right;
  }
  
  // 内容区域
  .publish-content {
    flex: 1;
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;
    
    .tab-content-wrapper {
      display: flex;
      justify-content: center;
      
      .tab-content {
        width: 100%;
        max-width: 800px;
        
        h3 {
          font-size: 16px;
          font-weight: 500;
          color: $text-primary;
          margin: 0 0 10px 0;
        }
        
        .upload-section,
        .account-section,
        .platform-section,
        .title-section,
        .product-section,
        .topic-section,
        .schedule-section {
          margin-bottom: 30px;
        }

        // 平台单选按钮样式
        .platform-radios {
          // 使用deep选择器穿透Element Plus的样式
          :deep(.platform-radio) {
            // 未选中状态的基础边框色
            &:not(.is-checked) {
              .el-radio__input .el-radio__inner {
                border-color: #1C9399 !important;
              }
            }
            
            // 鼠标悬浮状态 - 只改变文字颜色，不改变背景色
            &:hover:not(.is-checked) {
              .el-radio__label {
                color: #1C9399 !important;
              }
            }
            
            &.is-checked {
              // 选中状态的背景色与上传视频按钮一致
              .el-radio__input.is-checked .el-radio__inner {
                background-color: #1C9399 !important;
                border-color: #1C9399 !important;
              }
              
              // 选中状态的文本颜色
              .el-radio__label {
                color: #1C9399 !important;
                font-weight: 500 !important;
              }
            }
          }
          
          // 覆盖所有平台单选按钮的选中状态
          :deep(.el-radio.is-checked) {
            .el-radio__input.is-checked .el-radio__inner {
              background-color: #1C9399 !important;
              border-color: #1C9399 !important;
            }
            
            .el-radio__label {
              color: #1C9399 !important;
              font-weight: 500 !important;
            }
          }
          
          // 覆盖所有平台单选按钮的未选中状态基础边框色
          :deep(.el-radio:not(.is-checked)) {
            .el-radio__input .el-radio__inner {
              border-color: #1C9399 !important;
            }
            
            // 悬浮状态 - 只改变文字颜色
            &:hover {
              .el-radio__label {
                color: #1C9399 !important;
              }
            }
          }
        }

        .product-section {
          .product-name-input,
          .product-link-input {
            margin-bottom: 5px;
          }
        }
        
        .video-upload {
          width: 100%;
          
          :deep(.el-upload-dragger) {
            width: 100%;
            height: 180px;
          }
        }
        
        .account-input {
          max-width: 400px;
        }
        
        // 选择账号按钮 - 与批量发布按钮样式一致
        .el-button.el-button--primary.is-plain.select-account-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
          width: 10rem;
          border-radius: 4px;
          
          // 正常状态样式 - 与批量发布按钮一致
           background-color: #E8F4F5 !important;
           border-color: #8EC9CC !important;
           color: #1C9399 !important;
          
          &:hover {
            background-color: #1C9399 !important;
            border-color: #1C9399 !important;
            color: #FFFFFF !important;
          }
          
          &:active {
            background-color: #166B6F !important;
            border-color: #166B6F !important;
            color: #FFFFFF !important;
          }
        }
        
        .platform-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          
          .platform-btn {
            min-width: 80px;
          }
        }
        
        .title-input {
          max-width: 600px;
        }
        
        .topic-display {
          display: flex;
          flex-direction: column;
          gap: 12px;
          
          .selected-topics {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            min-height: 32px;
            
            .topic-tag {
              font-size: 14px;
            }
          }
          
          .select-topic-btn {
            align-self: flex-start;
            height: 32px;
            width: 10rem;
            border-radius: 4px;
            font-size: 14px;
            background-color: #e8f4f5;
            border-color: #8ec9cc;
            color: #1C9399;
            
            &:hover {
              background-color: #1C9399;
              border-color: #1C9399;
              color: #FFFFFF;
            }
            
            &:active {
              background-color: #7bb5b8;
              border-color: #7bb5b8;
              color: #FFFFFF;
            }
          }
          
          // 添加话题按钮 - 覆盖Element Plus默认样式
          .el-button.select-topic-btn {
            background-color: #e8f4f5 !important;
            border-color: #8ec9cc !important;
            color: #1C9399 !important;
            
            &:hover {
              background-color: #1C9399 !important;
              border-color: #1C9399 !important;
              color: #FFFFFF !important;
            }
            
            &:active {
              background-color: #7bb5b8 !important;
              border-color: #7bb5b8 !important;
              color: #FFFFFF !important;
            }
          }
          

        }
        
        .schedule-controls {
          display: flex;
          flex-direction: column;
          gap: 15px;

          .schedule-settings {
            margin-top: 15px;
            padding: 15px;
            background-color: #f5f7fa;
            border-radius: 4px;

            .schedule-item {
              display: flex;
              align-items: center;
              margin-bottom: 15px;

              &:last-child {
                margin-bottom: 0;
              }

              .label {
                min-width: 120px;
                margin-right: 10px;
              }

              .el-time-select {
                margin-right: 10px;
              }

              .el-button {
                margin-left: 10px;
              }
            }
          }
        }
        
        .action-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #ebeef5;
          
          .el-button {
            width: 10rem;
            height: 32px;
            border-radius: 4px;
            
            // 发布按钮样式
            &.el-button--primary {
              background-color: #1C9399;
              border-color: #1C9399;
              color: #FFFFFF;
              
              &:hover {
                background-color: #48D1CC;
                border-color: #48D1CC;
                color: #FFFFFF;
              }
              
              &:active {
                background-color: #166B6F;
                border-color: #166B6F;
                color: #FFFFFF;
              }
            }
            
            // 取消/重置按钮样式
            &:not(.el-button--primary) {
              background-color: #e8f4f5;
              border-color: #8ec9cc;
              color: #1C9399;
              
              &:hover {
                background-color: #1C9399;
                border-color: #1C9399;
                color: #FFFFFF;
              }
              
              &:active {
                background-color: #7bb5b8;
                border-color: #7bb5b8;
                color: #FFFFFF;
              }
            }
          }
        }

        .draft-section {
          margin: 20px 0;

          .draft-checkbox {
            display: block;
            margin: 10px 0;
          }
        }
        
        .topic-section {
          margin: 20px 0;
          
          h3 {
            margin-bottom: 8px; /* 缩小标题与按钮之间的间距 */
          }
          
          .topic-display {
            margin-top: 8px; /* 缩小标题与按钮之间的间距 */
          }
        }
      }
    }
  }

  // 已上传文件列表样式
  .uploaded-files {
    margin-top: 20px;
    
    h4 {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #303133;
    }
    
    .file-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      
      .file-item {
        display: flex;
        align-items: center;
        padding: 10px 15px;
        background-color: #f5f7fa;
        border-radius: 4px;
        
        .el-link {
          margin-right: 10px;
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        
        .file-size {
          color: #909399;
          font-size: 13px;
          margin-right: auto;
        }
      }
    }
  }
  
  // 添加话题弹窗样式
  .topic-dialog {
    .topic-dialog-content {
      .custom-topic-input {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
        
        .custom-input {
          flex: 1;
        }
      }
      
      .recommended-topics {
        h4 {
          margin: 0 0 16px 0;
          font-size: 16px;
          font-weight: 500;
          color: #303133;
        }
        
        .topic-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
          gap: 12px;
          
          .topic-btn {
            height: 36px;
            font-size: 14px;
            border-radius: 6px;
            min-width: 100px;
            padding: 0 12px;
            white-space: nowrap;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            
            &.el-button--primary {
              background-color: #409eff;
              border-color: #409eff;
              color: white;
            }
          }
        }
      }
    }
    
    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }
}

// 上传视频按钮样式
.upload-options .upload-btn {
  width: 10rem;
  border-radius: 4px;
  background-color: #1C9399 !important;
  border-color: #1C9399 !important;
  color: #FFFFFF !important;
}
.upload-options .upload-btn:hover {
  background-color: #48D1CC !important;
  border-color: #48D1CC !important;
  color: #FFFFFF !important;
}
.upload-options .upload-btn:active {
  background-color: #166B6F !important;
  border-color: #166B6F !important;
  color: #FFFFFF !important;
}

// 顶部Tab按钮样式
.tab-actions .add-tab-btn {
  width: 10rem;
  border-radius: 4px;
  background-color: #1C9399 !important;
  border-color: #1C9399 !important;
  color: #FFFFFF !important;
}
.tab-actions .add-tab-btn:hover {
  background-color: #48D1CC !important;
  border-color: #48D1CC !important;
  color: #FFFFFF !important;
}
.tab-actions .add-tab-btn:active {
  background-color: #166B6F !important;
  border-color: #166B6F !important;
  color: #FFFFFF !important;
}

// 批量发布按钮样式 - 新配色方案
.tab-actions .batch-publish-btn {
  width: 10rem;
  border-radius: 4px;
  background-color: #e8f4f5 !important;
  border-color: #8ec9cc !important;
  color: #1C9399 !important;
}
.tab-actions .batch-publish-btn:hover {
  background-color: #1C9399 !important;
  border-color: #1C9399 !important;
  color: #FFFFFF !important;
}
.tab-actions .batch-publish-btn:active {
  background-color: #7bb5b8 !important;
  border-color: #7bb5b8 !important;
  color: #FFFFFF !important;
}
</style>
