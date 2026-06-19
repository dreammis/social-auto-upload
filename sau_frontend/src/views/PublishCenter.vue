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
              v-if="tabs.length > 1 && tab.type !== 'unified'"
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
          <!-- ==================== 统一发布Tab（一键发布） ==================== -->
          <div v-if="tab.type === 'unified'" class="unified-publish-container">
            <!-- 发布状态提示 -->
            <div v-if="tab.publishStatus" class="publish-status">
              <el-alert
                :title="tab.publishStatus.message"
                :type="tab.publishStatus.type"
                :closable="false"
                show-icon
              />
            </div>

            <!-- 📁 公共区域 - 所有平台共用 -->
            <el-card class="section-card">
              <template #header>
                <span class="card-title">📁 公共设置（所有平台共用）</span>
              </template>

              <!-- 视频上传 -->
              <div class="form-item">
                <label>视频文件</label>
                <el-button type="primary" @click="showUploadOptions(tab)" :disabled="tab.publishing">
                  <el-icon><Upload /></el-icon> 上传视频
                </el-button>
                <div v-if="tab.fileList.length > 0" class="uploaded-files-inline">
                  <el-tag v-for="(file, idx) in tab.fileList" :key="idx" closable @close="removeFile(tab, idx)">
                    {{ file.name }}
                  </el-tag>
                </div>
              </div>

              <!-- 封面配置（3种尺寸，参考抖音双封面UI） -->
              <div class="form-item" style="margin-top: 8px;">
                <label>封面</label>
                <div class="cover-section">
                  <div class="cover-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                    <!-- 3:4 -->
                    <div class="cover-card">
                      <div class="cover-card-header">
                        <span>3:4</span>
                        <el-button size="small" type="primary" plain @click="showUploadOptions(tab, UPLOAD_TARGETS.COVER_PORTRAIT)" :disabled="tab.publishing">
                          选择封面
                        </el-button>
                      </div>
                      <div v-if="tab.coverPortrait" class="cover-file-item">
                        <el-link :href="tab.coverPortrait.url" target="_blank" type="primary">{{ tab.coverPortrait.name }}</el-link>
                        <span class="file-size">{{ (tab.coverPortrait.size / 1024 / 1024).toFixed(2) }}MB</span>
                        <el-button type="danger" size="small" @click="removeCover(tab, UPLOAD_TARGETS.COVER_PORTRAIT)">删除</el-button>
                      </div>
                      <div v-else class="cover-empty">未选择竖封面</div>
                      <div class="cover-platform-hint">
                        <el-icon><InfoFilled /></el-icon>
                        <span>适用：小红书 / 视频号 / 抖音 / 快手</span>
                        <el-tag size="small" type="warning" style="margin-left: 8px;">快手≤5MB</el-tag>
                      </div>
                    </div>

                    <!-- 4:3 -->
                    <div class="cover-card">
                      <div class="cover-card-header">
                        <span>4:3</span>
                        <el-button size="small" type="primary" plain @click="showUploadOptions(tab, UPLOAD_TARGETS.COVER_SQUARE)" :disabled="tab.publishing">
                          选择封面
                        </el-button>
                      </div>
                      <div v-if="tab.coverSquare" class="cover-file-item">
                        <el-link :href="tab.coverSquare.url" target="_blank" type="primary">{{ tab.coverSquare.name }}</el-link>
                        <span class="file-size">{{ (tab.coverSquare.size / 1024 / 1024).toFixed(2) }}MB</span>
                        <el-button type="danger" size="small" @click="removeCover(tab, UPLOAD_TARGETS.COVER_SQUARE)">删除</el-button>
                      </div>
                      <div v-else class="cover-empty">未选择方封面</div>
                      <div class="cover-platform-hint">
                        <el-icon><InfoFilled /></el-icon>
                        <span>适用：抖音 / B站</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 标题 -->
              <div class="form-item">
                <label>标题</label>
                <el-input v-model="tab.title" placeholder="请输入标题" maxlength="80" show-word-limit />
              </div>

              <!-- 描述/简介 -->
              <div class="form-item">
                <label>描述 / 简介</label>
                <el-input v-model="tab.desc" type="textarea" :rows="3" placeholder="请输入视频描述或简介" maxlength="2000" show-word-limit />
              </div>
            </el-card>

            <!-- 👤 账号配置（自动识别平台） -->
            <el-card class="section-card">
              <template #header>
                <span class="card-title">👤 账号配置</span>
              </template>

              <!-- 用户名搜索框 -->
              <div class="form-item">
                <label>搜索账号（输入用户名查找）</label>
                <el-select
                  v-model="tab.selectedUserIds"
                  multiple
                  filterable
                  remote
                  reserve-keyword
                  placeholder="输入用户名搜索，如'表情包'"
                  :remote-method="(query) => searchAccounts(tab, query)"
                  :loading="tab.accountSearchLoading"
                  style="width: 100%;"
                  :disabled="tab.publishing"
                  @change="onAccountSelected(tab)"
                >
                  <el-option-group
                    v-for="group in tab.searchResults"
                    :key="group.label"
                    :label="`${group.label} (${group.accounts.length}个)`"
                  >
                    <el-option
                      v-for="acc in group.accounts"
                      :key="acc.id"
                      :label="`${acc.name}`"
                      :value="acc.id"
                    >
                      <span class="account-option">
                        <span>{{ acc.name }}</span>
                        <el-tag size="small" :type="getPlatformTagType(acc.platform)" style="margin-left: 8px;">
                          {{ acc.platform }}
                        </el-tag>
                        <span v-if="acc.status === '正常'" class="status-dot status-normal"></span>
                        <span v-else class="status-dot status-error"></span>
                      </span>
                    </el-option>
                  </el-option-group>
                </el-select>
              </div>

              <!-- 自动检测到的平台（只读显示） -->
              <div v-if="tab.selectedPlatforms.length > 0" class="auto-detected-platforms">
                <h4 style="margin-bottom: 10px; font-size: 14px; color: #606266;">
                  📱 将自动发布到以下 {{ tab.selectedPlatforms.length }} 个平台:
                </h4>

                <div class="platform-tags-display">
                  <el-tag
                    v-for="platformId in tab.selectedPlatforms"
                    :key="platformId"
                    :type="getPlatformTagType(getPlatformConfig(platformId).name)"
                    size="large"
                    effect="dark"
                    style="margin-right: 8px; margin-bottom: 8px;"
                  >
                    {{ getPlatformConfig(platformId).name }}
                    ({{ getSelectedAccountsByPlatform(tab, platformId).length }}个账号)
                  </el-tag>
                </div>
              </div>

              <!-- 未选择账号时的提示 -->
              <div v-else class="no-platform-hint">
                <el-alert
                  title="请先搜索并选择账号，系统将自动识别可发布的平台"
                  type="info"
                  :closable="false"
                  show-icon
                  size="small"
                />
              </div>

              <!-- 已选账号详情展示区 -->
              <div v-if="tab.selectedUserIds.length > 0" class="selected-accounts-display">
                <h4 style="margin-bottom: 10px; font-size: 14px; color: #606266;">
                  已选择 {{ tab.selectedUserIds.length }} 个账号:
                </h4>

                <!-- 按平台分组显示 -->
                <div v-for="platformId in tab.selectedPlatforms" :key="platformId" class="platform-account-group">
                  <div class="platform-label">
                    <el-tag :type="getPlatformTagType(getPlatformConfig(platformId).name)" size="small">
                      {{ getPlatformConfig(platformId).name }}
                    </el-tag>
                  </div>

                  <div class="account-list-in-platform">
                    <div
                      v-for="acc in getSelectedAccountsByPlatform(tab, platformId)"
                      :key="acc.id"
                      class="account-tag-item"
                    >
                      <el-tag closable @close="removeAccountFromSelection(tab, acc.id)">
                        {{ acc.name }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 提示信息 -->
              <div class="account-config-tips">
                <el-alert
                  title="提示：输入用户名后，系统会自动匹配该用户在所有平台的账号。选择后将同时发布到该用户的所有选中平台。"
                  type="info"
                  :closable="false"
                  show-icon
                  size="small"
                />
              </div>
            </el-card>

            <!-- ⚙️ 差异化设置 -->
            <el-card class="section-card" v-if="tab.selectedPlatforms.length > 0">
              <template #header>
                <span class="card-title">⚙️ 平台差异化设置</span>
              </template>

              <!-- 📦 公共设置（所有平台共用） -->
              <div class="platform-specific-settings common-settings">
                <h4 class="platform-title" style="color: #409EFF;">📦 公共设置</h4>

                <!-- 合集功能 -->
                <div class="form-item">
                  <label>合集名称</label>
                  <el-input v-model="tab.platformConfig.common.collection" placeholder="输入合集名称" clearable>
                    <template #prefix>
                      <el-icon><Folder /></el-icon>
                    </template>
                  </el-input>
                </div>
              </div>

              <!-- 各平台独有设置 -->
              <!-- B站独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(5)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #00A1D6;">B站</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.bilibili.tags" :key="idx" closable @close="tab.platformConfig.bilibili.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.bilibili"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'bilibili')"
                      clearable
                    />
                  </div>
                </div>

                <div class="form-item">
                  <label>分区选择</label>
                  <el-select v-model="tab.platformConfig.bilibili.tid" placeholder="请选择分区" style="width: 100%;">
                    <el-option v-for="zone in BILIBILI_ZONES" :key="zone.value" :label="zone.label" :value="zone.value" />
                  </el-select>
                </div>

                <div class="form-item">
                  <el-checkbox v-model="tab.platformConfig.bilibili.isOriginal">原创声明（禁止转载）</el-checkbox>
                </div>

                <div class="form-item">
                  <el-checkbox v-model="tab.platformConfig.bilibili.aiDeclaration">AI生成内容声明</el-checkbox>
                </div>
              </div>

              <!-- 视频号独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(2)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #07C160;">视频号</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.channels.tags" :key="idx" closable @close="tab.platformConfig.channels.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.channels"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'channels')"
                      clearable
                    />
                  </div>
                </div>

                <div class="form-item">
                  <el-checkbox v-model="tab.platformConfig.channels.isDraft">仅保存草稿（用手机发布）</el-checkbox>
                </div>

                <div class="form-item">
                  <el-checkbox v-model="tab.platformConfig.channels.isOriginal">声明原创</el-checkbox>
                </div>
              </div>

              <!-- 小红书独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(1)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #FE2C55;">小红书</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.xiaohongshu.tags" :key="idx" closable @close="tab.platformConfig.xiaohongshu.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.xiaohongshu"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'xiaohongshu')"
                      clearable
                    />
                  </div>
                </div>

                <div class="form-item">
                  <label>声明类型</label>
                  <el-select v-model="tab.platformConfig.xiaohongshu.declaration" placeholder="请选择声明类型" clearable style="width: 100%;">
                    <el-option label="笔记含AI合成内容" value="笔记含AI合成内容" />
                    <el-option label="内容自行拍摄" value="内容自行拍摄" />
                    <el-option label="内容取材网络" value="内容取材网络" />
                    <el-option label="可能引人不适" value="可能引人不适" />
                  </el-select>
                </div>

                <div class="form-item">
                  <el-checkbox v-model="tab.platformConfig.xiaohongshu.isOriginal">声明原创</el-checkbox>
                </div>
              </div>

              <!-- 快手独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(4)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #FF4906;">快手</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.kuaishou.tags" :key="idx" closable @close="tab.platformConfig.kuaishou.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.kuaishou"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'kuaishou')"
                      clearable
                    />
                  </div>
                </div>

                <div class="form-item">
                  <label>作者声明</label>
                  <el-select v-model="tab.platformConfig.kuaishou.declaration" placeholder="请选择作者声明类型" style="width: 100%;">
                    <el-option label="内容为AI生成" value="内容为AI生成" />
                    <el-option label="内容自行拍摄" value="内容自行拍摄" />
                    <el-option label="内容取材网络" value="内容取材网络" />
                    <el-option label="可能引人不适" value="可能引人不适" />
                  </el-select>
                </div>
              </div>

              <!-- 抖音独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(3)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #000;">抖音</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.douyin.tags" :key="idx" closable @close="tab.platformConfig.douyin.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.douyin"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'douyin')"
                      clearable
                    />
                  </div>
                </div>

                <div class="form-item">
                  <label>商品名称</label>
                  <el-input v-model="tab.platformConfig.douyin.productTitle" placeholder="请输入商品名称（可选）" clearable />
                </div>

                <div class="form-item">
                  <label>商品链接</label>
                  <el-input v-model="tab.platformConfig.douyin.productLink" placeholder="请输入商品链接（可选）" clearable />
                </div>

                <div class="form-item">
                  <label>声明类型</label>
                  <el-radio-group v-model="tab.platformConfig.douyin.declaration_type">
                    <el-radio label="">不声明</el-radio>
                    <el-radio label="内容取材网络">内容取材网络</el-radio>
                    <el-radio label="内容由AI生成">内容由AI生成</el-radio>
                    <el-radio label="可能引人不适">可能引人不适</el-radio>
                    <el-radio label="虚构演绎，仅供娱乐">虚构演绎，仅供娱乐</el-radio>
                  </el-radio-group>
                </div>
              </div>

              <!-- TikTok独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(6)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #000;">TikTok</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.tiktok.tags" :key="idx" closable @close="tab.platformConfig.tiktok.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.tiktok"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'tiktok')"
                      clearable
                    />
                  </div>
                </div>
              </div>

              <!-- 百家号独有设置 -->
              <div v-if="tab.selectedPlatforms.includes(7)" class="platform-specific-settings">
                <h4 class="platform-title" style="color: #E74C3C;">百家号</h4>
                
                <!-- 标签/话题 -->
                <div class="form-item">
                  <label>标签 / 话题</label>
                  <div class="tags-input">
                    <el-tag v-for="(tag, idx) in tab.platformConfig.baijiahao.tags" :key="idx" closable @close="tab.platformConfig.baijiahao.tags.splice(idx, 1)" style="margin-right: 5px;">
                      {{ tag }}
                    </el-tag>
                    <el-input
                      v-model="newTagInputs.baijiahao"
                      placeholder="输入标签后按回车添加"
                      size="small"
                      style="width: 200px;"
                      @keyup.enter="addTagToPlatform(tab, 'baijiahao')"
                      clearable
                    />
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 🚀 发布按钮 -->
            <div class="unified-publish-actions">
              <el-button
                type="primary"
                size="large"
                @click="executeUnifiedPublish(tab)"
                :loading="tab.publishing"
                :disabled="!canUnifiedPublish(tab)"
                style="width: 100%; height: 50px; font-size: 18px;"
              >
                🚀 一键发布到 {{ tab.selectedPlatforms.length }} 个平台
              </el-button>
            </div>

            <!-- 发布进度 -->
            <el-card v-if="tab.publishResults.length > 0 || tab.publishing" class="section-card">
              <template #header>
                <span class="card-title">发布进度</span>
              </template>
              <el-progress :percentage="tab.publishProgress" :status="tab.publishProgress === 100 ? 'success' : ''" />
              
              <div class="publish-results-list">
                <div
                  v-for="(result, index) in tab.publishResults"
                  :key="index"
                  :class="['result-item', result.status]"
                >
                  <el-icon v-if="result.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
                  <el-icon v-else v-show="tab.publishing"><Loading /></el-icon>
                  <span class="label">{{ result.platform }}</span>
                  <span class="message">{{ result.message }}</span>
                  <el-link
                    v-if="result.status === 'error' && result.screenshot"
                    type="primary"
                    :underline="true"
                    @click="showScreenshotPreview(result.screenshot)"
                    style="margin-left: 8px;"
                  >
                    查看截图
                  </el-link>
                </div>
              </div>
            </el-card>
          </div>

          <!-- ==================== 普通发布Tab（原有功能保持不变） ==================== -->
          <div v-else>
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
            <h3>视频</h3>
            <div class="upload-options">
              <el-button type="primary" @click="showUploadOptions(tab)" class="upload-btn">
                <el-icon><Upload /></el-icon>
                上传视频
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
          
          <!-- 封面部分：根据平台配置动态显示 -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.cover !== 'none'" class="cover-section">
            <h3>封面</h3>
            <!-- 快手平台特殊提示 -->
            <el-alert v-if="tab.selectedPlatform === 4" type="warning" :closable="false" style="margin-bottom: 12px;">
              <template #title>
                <span style="font-size: 13px;">快手平台限制：封面图片不能大于5MB，系统会自动压缩超过限制的图片</span>
              </template>
            </el-alert>
            <div class="cover-grid">
              <!-- 单封面模式：小红书、视频号、快手 -->
              <div v-if="getPlatformConfig(tab.selectedPlatform).features.cover === 'single'" class="cover-card">
                <div class="cover-card-header">
                  <span>{{ getPlatformConfig(tab.selectedPlatform).name }}封面{{ tab.selectedPlatform === 2 ? ' 4:3' : '' }}</span>
                  <el-button size="small" type="primary" plain @click="showUploadOptions(tab, UPLOAD_TARGETS.COVER_SINGLE)">
                    选择封面
                  </el-button>
                </div>
                <div v-if="tab.coverSingle" class="cover-file-item">
                  <el-link :href="tab.coverSingle.url" target="_blank" type="primary">{{ tab.coverSingle.name }}</el-link>
                  <span class="file-size">{{ (tab.coverSingle.size / 1024 / 1024).toFixed(2) }}MB</span>
                  <el-button type="danger" size="small" @click="removeCover(tab, UPLOAD_TARGETS.COVER_SINGLE)">删除</el-button>
                </div>
                <div v-else class="cover-empty">未选择封面</div>
              </div>

              <!-- 双封面模式：抖音（竖封面 + 方封面） -->
              <template v-if="getPlatformConfig(tab.selectedPlatform).features.cover === 'double'">
                <div class="cover-card">
                  <div class="cover-card-header">
                    <span>竖封面 3:4</span>
                    <el-button size="small" type="primary" plain @click="showUploadOptions(tab, UPLOAD_TARGETS.COVER_PORTRAIT)">
                      选择封面
                    </el-button>
                  </div>
                  <div v-if="tab.coverPortrait" class="cover-file-item">
                    <el-link :href="tab.coverPortrait.url" target="_blank" type="primary">{{ tab.coverPortrait.name }}</el-link>
                    <span class="file-size">{{ (tab.coverPortrait.size / 1024 / 1024).toFixed(2) }}MB</span>
                    <el-button type="danger" size="small" @click="removeCover(tab, UPLOAD_TARGETS.COVER_PORTRAIT)">删除</el-button>
                  </div>
                  <div v-else class="cover-empty">未选择竖封面</div>
                </div>

                <div class="cover-card">
                  <div class="cover-card-header">
                    <span>方封面 4:3</span>
                    <el-button size="small" type="primary" plain @click="showUploadOptions(tab, UPLOAD_TARGETS.COVER_SQUARE)">
                      选择封面
                    </el-button>
                  </div>
                  <div v-if="tab.coverSquare" class="cover-file-item">
                    <el-link :href="tab.coverSquare.url" target="_blank" type="primary">{{ tab.coverSquare.name }}</el-link>
                    <span class="file-size">{{ (tab.coverSquare.size / 1024 / 1024).toFixed(2) }}MB</span>
                    <el-button type="danger" size="small" @click="removeCover(tab, UPLOAD_TARGETS.COVER_SQUARE)">删除</el-button>
                  </div>
                  <div v-else class="cover-empty">未选择方封面</div>
                </div>
              </template>
            </div>
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

          <!-- 平台选择 -->
          <div class="platform-section">
            <h3>平台</h3>
            <el-radio-group v-model="tab.selectedPlatform" class="platform-radios">
              <el-radio 
                v-for="platform in platforms" 
                :key="platform.key"
                :label="platform.key"
                class="platform-radio"
              >
                {{ platform.name }}
              </el-radio>
            </el-radio-group>
          </div>

          <!-- 平台特殊功能：草稿选项（视频号） -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.channelsDraft" class="channelsDraft-section">
            <el-checkbox
              v-model="tab.isDraft"
              label="视频号仅保存草稿(用手机发布)"
              class="channelsDraft-checkbox"
            />
          </div>

          <!-- 平台特殊功能：原创声明（视频号、小红书） -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.declareOriginal" class="declareOriginal-section">
            <el-checkbox
              v-model="tab.isOriginal"
              label="声明原创"
              class="declareOriginal-checkbox"
            />
          </div>

          <!-- 平台特殊功能：商品链接和声明类型（抖音） -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.douyinProduct" class="douyinProduct-section">
            <h3>商品链接</h3>
            <el-input
              v-model="tab.douyinProductTitle"
              type="text"
              :rows="1"
              placeholder="请输入商品名称"
              maxlength="200"
              class="douyinProduct-name-input"
            />
            <el-input
              v-model="tab.douyinProductLink"
              type="text"
              :rows="1"
              placeholder="请输入商品链接"
              maxlength="200"
              class="douyinProduct-link-input"
            />
          </div>

          <!-- 平台特殊功能：声明类型（抖音） -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.douyinDeclaration" class="douyinDeclaration-section">
            <h3>请选择声明类型（单选）</h3>
            <el-radio-group v-model="tab.declaration_type" @change="onDeclarationTypeChange(tab)">
              <el-radio label="内容自行拍摄" disabled>内容自行拍摄</el-radio> <!-- TODO: 暂时选择不了地区，后续有时间再优化 -->
              <el-radio label="内容取材网络">内容取材网络</el-radio>
              <el-radio label="内容由AI生成">内容由AI生成</el-radio>
              <el-radio label="可能引人不适">可能引人不适</el-radio>
              <el-radio label="虚构演绎，仅供娱乐">虚构演绎，仅供娱乐</el-radio>
              <el-radio label="危险行为，请勿模仿">危险行为，请勿模仿</el-radio>
            </el-radio-group>
            <div v-if="tab.declaration_type === '内容取材网络'" style="margin-top: 10px;">
              <el-radio-group v-model="tab.declaration_network_subtype">
                <el-radio label="取材站外">取材站外</el-radio>
              </el-radio-group>
            </div>
            <div v-if="tab.declaration_type === '内容自行拍摄'" class="shot-extra" style="margin-top: 10px;">
              <el-cascader
                v-model="tab.declaration_location"
                :options="regionsCountryOptions"
                :props="regionsCascaderProps"
                placeholder="选择拍摄地点"
                style="width: 300px;"
                filterable
                clearable
              />
              <el-date-picker
                v-model="tab.declaration_date"
                type="date"
                placeholder="设置拍摄日期"
                value-format="YYYY-MM-DD"
                style="margin-left: 10px;"
              />
            </div>
          </div>

          <!-- 平台特殊功能：声明类型（小红书） -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.xiaohongshuDeclaration" class="xiaohongshu-declaration-section">
            <h3>声明类型</h3>
            <el-select
              v-model="tab.xiaohongshu_declaration"
              placeholder="请选择声明类型"
              style="width: 100%"
              clearable
            >
              <el-option label="笔记含AI合成内容" value="笔记含AI合成内容" />
              <el-option label="内容自行拍摄" value="内容自行拍摄" />
              <el-option label="内容取材网络" value="内容取材网络" />
              <el-option label="可能引人不适" value="可能引人不适" />
              <el-option label="虚构演绎，仅供娱乐" value="虚构演绎，仅供娱乐" />
              <el-option label="危险行为，请勿模仿" value="危险行为，请勿模仿" />
            </el-select>
          </div>

          <!-- 平台特殊功能：作者声明（快手） -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.kuaishouDeclaration" class="kuaishou-declaration-section">
            <h3>作者声明</h3>
            <el-select
              v-model="tab.kuaishou_declaration"
              placeholder="请选择作者声明类型"
              style="width: 100%"
            >
              <el-option label="内容为AI生成" value="内容为AI生成" />
              <el-option label="内容自行拍摄" value="内容自行拍摄" />
              <el-option label="内容取材网络" value="内容取材网络" />
              <el-option label="可能引人不适" value="可能引人不适" />
              <el-option label="虚构演绎，仅供娱乐" value="虚构演绎，仅供娱乐" />
              <el-option label="危险行为，请勿模仿" value="危险行为，请勿模仿" />
            </el-select>
          </div>

          <!-- 平台特殊功能：B站分区选择 -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.bilibiliZone" class="bilibili-zone-section">
            <h3>分区选择</h3>
            <el-select
              v-model="tab.bilibiliTid"
              placeholder="请选择分区"
              style="width: 100%"
            >
              <el-option
                v-for="zone in BILIBILI_ZONES"
                :key="zone.value"
                :label="zone.label"
                :value="zone.value"
              />
            </el-select>
          </div>

          <!-- 平台特殊功能：B站创作声明 -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.bilibiliDeclaration" class="bilibili-declaration-section">
            <h3>创作声明</h3>
            <el-checkbox
              v-model="tab.bilibiliAiDeclaration"
              label="含AI生成内容"
              class="bilibili-declaration-checkbox"
            />
          </div>

          <!-- 合集选择 -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.collection" class="collection-section">
            <h3>合集</h3>
            <el-select
              v-model="tab.collection"
              placeholder="请选择或搜索合集（支持模糊匹配）"
              style="width: 100%"
              filterable
              allow-create
              default-first-option
            >
              <el-option
                v-for="item in COLLECTION_OPTIONS"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <div style="margin-top: 5px; color: #909399; font-size: 12px;">
              可输入关键字搜索合集，如输入"大学"可匹配"大学篇"
            </div>
          </div>

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

          <!-- 描述输入：根据平台配置动态显示 -->
          <div v-if="getPlatformConfig(tab.selectedPlatform).features.description" class="description-section">
            <h3>描述</h3>
            <el-input
              v-model="tab.desc"
              type="textarea"
              :rows="4"
              placeholder="请输入描述"
              maxlength="2000"
              show-word-limit
              class="description-input"
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
          </div>  <!-- 关闭 v-else 普通发布Tab容器 -->
        </div>
      </div>

      <!-- ==================== 全局上传弹窗（所有Tab共用） ==================== -->
      <!-- 上传选项弹窗 -->
      <el-dialog
        v-model="uploadOptionsVisible"
        :title="uploadOptionsTitle"
        width="400px"
        class="upload-options-dialog"
      >
        <div class="upload-options-content">
          <el-button type="primary" @click="selectLocalUpload" class="option-btn">
            <el-icon><Upload /></el-icon>
            本地上传
          </el-button>
          <el-button type="success" @click="selectMaterialLibrary" class="option-btn">
            <el-icon><Folder /></el-icon>
            素材库
          </el-button>
        </div>
      </el-dialog>

      <!-- 本地上传弹窗 -->
      <el-dialog
        v-model="localUploadVisible"
        :title="localUploadTitle"
        width="600px"
        class="local-upload-dialog"
      >
        <el-upload
          class="video-upload"
          drag
          :auto-upload="true"
          :http-request="handleCustomUpload"
          :on-error="handleUploadError"
          :multiple="allowMultipleUpload"
          :accept="uploadAccept"
          :headers="authHeaders"
          :show-file-list="false"
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">
            将{{ uploadTargetNoun }}拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              {{ uploadTargetTip }}
            </div>
          </template>
        </el-upload>
      </el-dialog>

      <!-- 素材库选择弹窗 -->
      <el-dialog
        v-model="materialLibraryVisible"
        :title="currentUploadTarget === UPLOAD_TARGETS.VIDEO ? '选择视频素材' : '选择封面素材'"
        width="800px"
        class="material-library-dialog"
      >
        <div class="material-library-content">
          <el-checkbox-group v-model="selectedMaterials" :max="isCoverUploadTarget ? 1 : undefined">
            <div class="material-list">
              <div
                v-for="material in selectableMaterials"
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
          <el-empty v-if="selectableMaterials.length === 0" description="暂无可选素材" />
        </div>
        <template #footer>
          <div class="dialog-footer">
            <el-button @click="materialLibraryVisible = false">取消</el-button>
            <el-button type="primary" @click="confirmMaterialSelection">确定</el-button>
          </div>
        </template>
      </el-dialog>
      
      <!-- 截图预览弹窗 -->
      <el-dialog
        v-model="screenshotPreviewVisible"
        title="上传失败截图"
        width="80%"
        destroy-on-close
        @close="closeScreenshotPreview"
      >
        <div class="screenshot-preview-container">
          <el-image
            :src="currentScreenshotUrl"
            fit="contain"
            style="width: 100%; max-height: 70vh;"
            :preview-src-list="[currentScreenshotUrl]"
          >
            <template #error>
              <div class="image-error">
                <el-icon><Picture /></el-icon>
                <span>截图加载失败</span>
              </div>
            </template>
          </el-image>
        </div>
        <template #footer>
          <el-button @click="closeScreenshotPreview">关闭</el-button>
          <el-button type="primary" @click="window.open(currentScreenshotUrl)">在新窗口打开</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { Upload, Plus, Close, Folder, Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { materialApi } from '@/api/material'
import { http } from '@/utils/request'
import { countryOptions as regionsCountryOptions, declarationCascaderProps as regionsCascaderProps } from '@/utils/regions.zh'

const UPLOAD_TARGETS = {
  VIDEO: 'video',
  COVER_SINGLE: 'coverSingle',
  COVER_PORTRAIT: 'coverPortrait',
  COVER_SQUARE: 'coverSquare'
}

// Authorization headers
const authHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

// 当前激活的tab
const activeTab = ref('unified')  // 默认显示"一键发布"Tab

// tab计数器
let tabCounter = 1

// 获取应用状态管理
const appStore = useAppStore()

// 上传相关状态
const uploadOptionsVisible = ref(false)
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const currentUploadTab = ref(null)
const currentUploadTarget = ref(UPLOAD_TARGETS.VIDEO)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)
const isCoverUploadTarget = computed(() => currentUploadTarget.value !== UPLOAD_TARGETS.VIDEO)
const allowMultipleUpload = computed(() => currentUploadTarget.value === UPLOAD_TARGETS.VIDEO)
const uploadAccept = computed(() => currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? 'video/*' : 'image/*')
const uploadTargetNoun = computed(() => currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? '视频文件' : '封面图片')
const uploadTargetTip = computed(() => currentUploadTarget.value === UPLOAD_TARGETS.VIDEO
  ? '支持MP4、AVI等视频格式，可上传多个文件'
  : '支持 JPG、PNG、WEBP 等图片格式，上传后会写入素材库')
const uploadOptionsTitle = computed(() => currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? '选择视频上传方式' : '选择封面上传方式')
const localUploadTitle = computed(() => currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? '本地上传视频' : '本地上传封面')

// 批量发布相关状态
const batchPublishing = ref(false)
const batchPublishMessage = ref('')
const batchPublishType = ref('info')

// ==================== 平台配置 ====================
// 定义每个平台的特性，统一管理平台差异
const PLATFORM_CONFIG = {
  1: { // 小红书
    name: '小红书',
    features: {
      cover: 'single',        // 单封面
      description: true,      // 支持描述
      channelsDraft: false,           // 不支持草稿
      douyinProduct: false,         // 不支持商品
      douyinDeclaration: false,     // 不支持抖音声明类型
      xiaohongshuDeclaration: true, // 支持小红书声明类型（下拉列表）
      declareOriginal: true,          // 支持原创声明
      bilibiliZone: false,    // 不支持B站分区
      collection: true         // 支持合集
    }
  },
  2: { // 视频号
    name: '视频号',
    features: {
      cover: 'single',
      description: true,
      channelsDraft: true,            // 支持草稿
      douyinProduct: false,
      douyinDeclaration: false,
      declareOriginal: true,          // 支持原创声明
      bilibiliZone: false,
      collection: true               // 支持合集
    }
  },
  3: { // 抖音
    name: '抖音',
    features: {
      cover: 'double',        // 双封面（竖+横）
      description: true,
      channelsDraft: false,
      douyinProduct: true,          // 支持商品
      douyinDeclaration: true,      // 支持声明类型
      declareOriginal: false,        // 不支持原创声明
      bilibiliZone: false,
      collection: true              // 支持合集
    }
  },
  4: { // 快手
    name: '快手',
    features: {
      cover: 'single',
      description: true,
      channelsDraft: false,
      douyinProduct: false,
      douyinDeclaration: false,      // 不支持抖音声明类型（单选框）
      kuaishouDeclaration: true, // 快手作者声明（下拉列表）
      declareOriginal: false,        // 不支持原创声明
      bilibiliZone: false,
      collection: true              // 支持合集
    }
  },
  5: { // B站
    name: 'B站',
    features: {
      cover: 'single',              // 支持单封面
      description: true,
      channelsDraft: false,
      douyinProduct: false,
      douyinDeclaration: false,
      declareOriginal: true,         // 支持原创声明（声明原创 = 自制 + 禁止转载）
      bilibiliZone: true,            // 支持B站分区
      bilibiliDeclaration: true,     // 支持B站创作声明（含AI生成内容）
      collection: true               // 支持合集
    }
  },
  6: { // TikTok
    name: 'TikTok',
    features: {
      cover: 'none',
      description: false,
      channelsDraft: false,
      douyinProduct: false,
      douyinDeclaration: false,
      declareOriginal: false,        // 不支持原创声明
      bilibiliZone: false,
      collection: true              // 支持合集
    }
  },
  7: { // 百家号
    name: '百家号',
    features: {
      cover: 'none',
      description: false,
      channelsDraft: false,
      douyinProduct: false,
      douyinDeclaration: false,
      declareOriginal: false,        // 不支持原创声明
      bilibiliZone: false,
      collection: true              // 支持合集
    }
  }
}

// B站分区
const BILIBILI_ZONES = [
  { value: 218, label: '动物' }
]

// 合集选项
const COLLECTION_OPTIONS = [
  { value: '大学篇', label: '大学篇' }
]

// 获取平台配置的辅助函数
const getPlatformConfig = (platformId) => {
  return PLATFORM_CONFIG[platformId] || PLATFORM_CONFIG[1]
}

// 平台列表 - 对应后端type字段
const platforms = [
  { key: 3, name: '抖音' },
  { key: 4, name: '快手' },
  { key: 2, name: '视频号' },
  { key: 1, name: '小红书' },
  { key: 5, name: 'B站' },
  { key: 7, name: '百家号' },
  { key: 6, name: 'TikTok' },
]

const defaultTabInit = {
  name: 'tab1',
  label: '发布1',
  fileList: [], // 后端返回的文件名列表
  displayFileList: [], // 用于显示的文件列表
  coverSingle: null,
  coverPortrait: null,
  coverSquare: null,
  selectedAccounts: [], // 选中的账号ID列表
  selectedPlatform: 1, // 选中的平台（单选）
  title: '',
  desc: '',
  douyinProductLink: '', // 商品链接
  douyinProductTitle: '', // 商品名称
  declaration_type: '', // 自主声明类型（与抖音页面选项文字一致）
  declaration_location: [], // 拍摄地点
  declaration_date: '', // 拍摄日期
  declaration_network_subtype: '', // 内容取材网络的下级默认选项
  selectedTopics: [], // 话题列表（不带#号）
  scheduleEnabled: false, // 定时发布开关
  videosPerDay: 1, // 每天发布视频数量
  dailyTimes: ['10:00'], // 每天发布时间点列表
  startDays: 0, // 从今天开始计算的发布天数，0表示明天，1表示后天
  publishStatus: null, // 发布状态，包含message和type
  publishing: false, // 发布状态，用于控制按钮loading效果
  isDraft: false, // 是否保存为草稿，仅视频号平台可见
  isOriginal: false, // 是否标记为原创，仅视频号、小红书平台可见
  bilibiliTid: 218, // B站分区ID，默认218（动物圈）
  bilibiliAiDeclaration: false, // B站创作声明：含AI生成内容
  kuaishou_declaration: '内容为AI生成', // 快手作者声明类型，默认"内容为AI生成"
  xiaohongshu_declaration: '', // 小红书声明类型
  collection: '大学篇', // 合集名称，默认"大学篇"
  coverSingle: null, // B站封面文件
}

// ==================== 统一发布Tab数据结构 ====================
const unifiedPublishInit = {
  name: 'unified',
  label: '🚀 一键发布',
  type: 'unified', // 特殊类型标识
  // 公共区域 - 所有平台共用
  fileList: [], // 视频文件列表
  displayFileList: [],
  coverSingle: null, // 统一封面（各平台可能不同）
  title: '', // 标题
  desc: '', // 描述/简介

  // 平台选择
  selectedPlatforms: [], // 选中的平台ID列表 [1,3,5]

  // 账号搜索与选择（新设计）
  selectedUserIds: [], // 已选择的账号ID列表 [2, 5, 8]
  accountSearchLoading: false, // 搜索加载状态
  searchResults: [], // 搜索结果 [{label: '表情包', accounts: [...]}]

  // 各平台账号配置（自动从selectedUserIds计算）
  platformAccounts: {
    1: [], // 小红书账号
    2: [], // 视频号账号
    3: [], // 抖音账号
    4: [], // 快手账号
    5: [], // B站账号
    6: [], // TikTok账号
    7: [], // 百家号账号
  },

  // 平台差异化设置（每个平台独立的标签）
  platformConfig: {
    // 公共设置
    common: {
      collection: '', // 合集名称（所有平台共用）
    },

    // 小红书独有
    xiaohongshu: {
      tags: [], // 标签/话题（独立）
      declaration: '笔记含AI合成内容', // 声明类型
      isOriginal: true, // 原创声明
    },
    // 视频号独有
    channels: {
      tags: [], // 标签/话题（独立）
      isDraft: false, // 草稿模式
      isOriginal: true, // 原创声明
    },
    // 抖音独有
    douyin: {
      tags: [], // 标签/话题（独立）
      productTitle: '', // 商品名称
      productLink: '', // 商品链接
      declaration_type: '内容由AI生成', // 声明类型
    },
    // 快手独有
    kuaishou: {
      tags: [], // 标签/话题（独立）
      declaration: '内容为AI生成', // 作者声明
    },
    // B站独有
    bilibili: {
      tags: [], // 标签/话题（独立）
      tid: 218, // 分区ID
      isOriginal: true, // 原创声明(禁止转载) - 默认勾选
      aiDeclaration: true, // AI声明
    },
    // TikTok独有
    tiktok: {
      tags: [], // 标签/话题（独立）
    },
    // 百家号独有
    baijiahao: {
      tags: [], // 标签/话题（独立）
    }
  },

  // 各平台封面配置（2种尺寸）
  coverPortrait: null, // 竖版 (3:4)
  coverSquare: null,    // 方形 (4:3)

  // 发布状态
  publishStatus: null,
  publishing: false,
  publishProgress: 0,
  publishResults: [],
}

// 创建统一发布Tab
const makeUnifiedTab = () => {
  try {
    return typeof structuredClone === 'function'
      ? structuredClone(unifiedPublishInit)
      : JSON.parse(JSON.stringify(unifiedPublishInit))
  } catch (e) {
    return JSON.parse(JSON.stringify(unifiedPublishInit))
  }
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

// tab页数据 - 默认包含"一键发布"Tab和普通发布Tab
const tabs = reactive([
  makeUnifiedTab(),  // 🚀 一键发布（特殊Tab）
  makeNewTab()       // 普通发布1
])

// 账号相关状态
const accountDialogVisible = ref(false)
const tempSelectedAccounts = ref([])
const currentTab = ref(null)

// 获取账号状态管理
const accountStore = useAccountStore()

// 根据选择的平台获取可用账号列表
const availableAccounts = computed(() => {
  const platformMap = {
    1: '小红书',
    2: '视频号',
    3: '抖音',
    4: '快手',
    5: 'B站',
    6: 'TikTok',
    7: '百家号'
  }
  const currentPlatform = currentTab.value ? platformMap[currentTab.value.selectedPlatform] : null
  return currentPlatform ? accountStore.accounts.filter(acc => acc.platform === currentPlatform) : []
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

const getMaterialFileName = (materialOrFile) => {
  if (!materialOrFile) {
    return ''
  }

  if (typeof materialOrFile === 'string') {
    return materialOrFile
  }

  const displayName = materialOrFile.filename || materialOrFile.name || ''
  if (displayName && displayName !== '未命名') {
    return displayName
  }

  return materialOrFile.file_path || materialOrFile.path || displayName
}

const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']

const isImageMaterial = (materialOrFile) => {
  const filename = getMaterialFileName(materialOrFile).toLowerCase()
  return imageExtensions.some(ext => filename.endsWith(ext))
}

const isVideoMaterial = (materialOrFile) => {
  const filename = getMaterialFileName(materialOrFile).toLowerCase()
  return videoExtensions.some(ext => filename.endsWith(ext))
}

const selectableMaterials = computed(() => materials.value.filter(material => (
  currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? isVideoMaterial(material) : isImageMaterial(material)
)))

const buildPreviewUrl = (filePath) => {
  const normalizedPath = String(filePath || '').replace(/\\/g, '/')
  const filename = normalizedPath.split('/').pop()
  return materialApi.getMaterialPreviewUrl(filename)
}

const buildFileInfo = ({ name, path, size, type }) => ({
  name,
  path,
  size,
  type,
  url: buildPreviewUrl(path)
})

const syncMaterials = async () => {
  const response = await materialApi.getAllMaterials()
  if (response.code === 200) {
    appStore.setMaterials(response.data)
  }
  return response
}

const setCoverFile = (tab, target, fileInfo) => {
  if (target === UPLOAD_TARGETS.COVER_SINGLE) {
    tab.coverSingle = fileInfo
    return
  }

  if (target === UPLOAD_TARGETS.COVER_PORTRAIT) {
    tab.coverPortrait = fileInfo
    return
  }

  if (target === UPLOAD_TARGETS.COVER_LANDSCAPE) {
    tab.coverLandscape = fileInfo
    return
  }

  if (target === UPLOAD_TARGETS.COVER_SQUARE) {
    tab.coverSquare = fileInfo
  }
}

const addVideoFile = (tab, fileInfo) => {
  tab.fileList.push(fileInfo)
  tab.displayFileList = [...tab.fileList.map(item => ({
    name: item.name,
    url: item.url
  }))]
}

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
  // 保护"一键发布"Tab，不允许删除
  const tab = tabs.find(t => t.name === tabName)
  if (tab && tab.type === 'unified') {
    ElMessage.warning('🚀 一键发布Tab不可删除')
    return
  }
  
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
const handleUploadSuccess = (response, file, tab, target = UPLOAD_TARGETS.VIDEO) => {
  if (response.code !== 200) {
    ElMessage.error(response.msg || '上传失败')
    return
  }

  const responseData = response.data || {}
  const filePath = responseData.filepath || responseData.path || responseData
  const displayName = responseData.filename || file.name
  const fileInfo = buildFileInfo({
    name: displayName,
    path: filePath,
    size: file.size,
    type: file.type
  })

  if (target === UPLOAD_TARGETS.VIDEO) {
    addVideoFile(tab, fileInfo)
    ElMessage.success('视频上传成功')
    return
  }

  setCoverFile(tab, target, fileInfo)
  ElMessage.success('封面上传成功，已同步到素材库')
}

const handleCustomUpload = async (options) => {
  const { file, onSuccess, onError } = options
  const formData = new FormData()
  formData.append('file', file)

  try {
    let response
    if (currentUploadTarget.value === UPLOAD_TARGETS.VIDEO) {
      response = await http.upload('/upload', formData)
    } else {
      response = await materialApi.uploadMaterial(formData)
    }

    handleUploadSuccess(response, file, currentUploadTab.value, currentUploadTarget.value)
    onSuccess?.(response)

    if (currentUploadTarget.value !== UPLOAD_TARGETS.VIDEO) {
      try {
        await syncMaterials()
      } catch (syncError) {
        console.error('同步素材列表出错:', syncError)
      }
      localUploadVisible.value = false
    }
  } catch (error) {
    onError?.(error)
  }
}

// 处理文件上传失败
const handleUploadError = (error) => {
  ElMessage.error('文件上传失败')
}

// ==================== 统一发布（一键发布）相关函数 ====================
// 各平台标签输入状态
const newTagInputs = reactive({
  xiaohongshu: '',
  channels: '',
  douyin: '',
  kuaishou: '',
  bilibili: '',
  tiktok: '',
  baijiahao: ''
})

// 添加标签到指定平台
const addTagToPlatform = (tab, platformKey) => {
  const inputValue = newTagInputs[platformKey].trim()
  if (inputValue && !tab.platformConfig[platformKey].tags.includes(inputValue)) {
    tab.platformConfig[platformKey].tags.push(inputValue)
    newTagInputs[platformKey] = ''
  }
}

// ==================== 账号搜索与选择（统一发布） ====================

// 搜索账号 - 按用户名模糊匹配
const searchAccounts = (tab, query) => {
  if (!query || query.trim().length === 0) {
    tab.searchResults = []
    return
  }

  tab.accountSearchLoading = true

  // 模拟异步搜索（实际可改为API调用）
  setTimeout(() => {
    const keyword = query.toLowerCase().trim()

    // 在所有账号中按用户名搜索
    const matchedAccounts = accountStore.accounts.filter(acc =>
      acc.name && acc.name.toLowerCase().includes(keyword)
    )

    // 按用户名分组
    const groupedByUser = {}
    matchedAccounts.forEach(acc => {
      if (!groupedByUser[acc.name]) {
        groupedByUser[acc.name] = {
          label: acc.name,
          accounts: []
        }
      }
      groupedByUser[acc.name].accounts.push(acc)
    })

    // 转换为数组并排序
    tab.searchResults = Object.values(groupedByUser).sort((a, b) =>
      a.label.localeCompare(b.label, 'zh-CN')
    )

    tab.accountSearchLoading = false
  }, 300)
}

// 账号选择变化时触发
const onAccountSelected = (tab) => {
  // 1. 自动从选择的账号中提取平台列表
  autoDetectPlatforms(tab)

  // 2. 根据选择的账号ID，重新计算各平台的账号列表
  recalculatePlatformAccounts(tab)
}

// 自动检测平台（从已选账号中提取）
const autoDetectPlatforms = (tab) => {
  // 收集所有已选账号对应的平台ID
  const platformIds = new Set()

  tab.selectedUserIds.forEach(userId => {
    const account = accountStore.accounts.find(acc => acc.id === userId)
    if (account) {
      const platformId = getPlatformIdByName(account.platform)
      if (platformId && [1, 2, 3, 4, 5].includes(platformId)) { // 只支持5大平台
        platformIds.add(platformId)
      }
    }
  })

  // 转换为数组并排序（按平台顺序：小红书、视频号、抖音、快手、B站）
  tab.selectedPlatforms = Array.from(platformIds).sort((a, b) => a - b)

  console.log(`[统一发布] 自动检测到 ${tab.selectedPlatforms.length} 个平台:`, tab.selectedPlatforms.map(id => getPlatformConfig(id).name))
}

// 重新计算各平台的账号配置
const recalculatePlatformAccounts = (tab) => {
  // 清空所有平台账号
  for (const platformId in tab.platformAccounts) {
    tab.platformAccounts[platformId] = []
  }

  // 根据selectedUserIds填充platformAccounts
  tab.selectedUserIds.forEach(userId => {
    const account = accountStore.accounts.find(acc => acc.id === userId)
    if (account) {
      // 找到该账号对应的平台ID
      const platformId = getPlatformIdByName(account.platform)
      if (platformId && tab.platformAccounts[platformId]) {
        tab.platformAccounts[platformId].push(userId)
      }
    }
  })
}

// 根据平台名称获取平台ID
const getPlatformIdByName = (platformName) => {
  const nameToIdMap = {
    '小红书': 1,
    '视频号': 2,
    '抖音': 3,
    '快手': 4,
    'B站': 5,
    'TikTok': 6,
    '百家号': 7
  }
  return nameToIdMap[platformName]
}

// 获取指定平台已选的账号列表
const getSelectedAccountsByPlatform = (tab, platformId) => {
  return tab.selectedUserIds.map(userId => {
    return accountStore.accounts.find(acc => acc.id === userId)
  }).filter(acc => acc && acc.platform === getPlatformConfig(platformId).name)
}

// 从选择中移除某个账号
const removeAccountFromSelection = (tab, userId) => {
  const index = tab.selectedUserIds.indexOf(userId)
  if (index > -1) {
    tab.selectedUserIds.splice(index, 1)
    // 重新计算平台账号
    recalculatePlatformAccounts(tab)
  }
}

// 获取平台标签类型（用于颜色）
const getPlatformTagType = (platformName) => {
  const typeMap = {
    '小红书': 'danger',
    '视频号': 'success',
    '抖音': '',
    '快手': 'warning',
    'B站': '',
    'TikTok': 'info',
    '百家号': 'info'
  }
  return typeMap[platformName] || ''
}

// ==================== 封面和差异化设置辅助函数 ====================

// 获取除抖音外的其他平台（用于单封面上传）
const getOtherPlatforms = (tab) => {
  return tab.selectedPlatforms.filter(id => id !== 3) // 3是抖音
}

// 获取封面比例
const getCoverRatio = (platformId) => {
  const ratioMap = {
    1: '3:4',   // 小红书 - 竖版
    2: '3:4',   // 视频号 - 竖版
    3: '3:4',   // 抖音 - 竖版
    4: '3:4',   // 快手 - 竖版
    5: '4:3',   // B站 - 方形
  }
  return ratioMap[platformId] || '3:4'
}

// 获取平台封面上传按钮文字
const getPlatformCoverName = (tab, platformId) => {
  const coverFile = tab.platformCovers[platformId]
  return coverFile ? '已选择' : '选择'
}

// 获取平台封面文件
const getPlatformCoverFile = (tab, platformId) => {
  return tab.platformCovers[platformId]
}

// ==================== 平台-尺寸映射函数 ====================

// 获取平台对应的封面名称
const getCoverNameForPlatform = (platformId) => {
  const mapping = {
    1: '竖版 (3:4)',   // 小红书
    2: '竖版 (3:4)',   // 视频号
    3: '双尺寸',       // 抖音 (3:4 + 4:3)
    4: '竖版 (3:4)',   // 快手
    5: '方版 (4:3)',   // B站 (目前只需要4:3)
  }
  return mapping[platformId] || '未配置'
}

// 获取封面类型（用于标签颜色）
const getCoverTypeForPlatform = (platformId) => {
  const typeMap = {
    1: '',      // 小红书 - 竖版
    2: '',      // 视频号 - 竖版
    3: 'warning', // 抖音 - 双尺寸
    4: '',      // 快手 - 竖版
    5: '',      // B站 - 方版（目前只需要一张）
  }
  return typeMap[platformId] || ''
}

// 检查平台是否有必需的封面
const hasRequiredCover = (tab, platformId) => {
  switch (platformId) {
    case 1: // 小红书 → 竖版
    case 2: // 视频号 → 竖版
    case 4: // 快手 → 竖版
      return !!tab.coverPortrait

    case 3: // 抖音 → 竖版 + 方形
      return !!(tab.coverPortrait && tab.coverSquare)

    case 5: // B站 → 方形 (4:3)
      return !!tab.coverSquare

    default:
      return true
  }
}

// 根据平台获取实际使用的封面路径
const getCoverPathForPlatform = (tab, platformId) => {
  switch (platformId) {
    case 1: // 小红书
    case 2: // 视频号
    case 4: // 快手
      return tab.coverPortrait?.path

    case 3: // 抖音（返回双封面对象）
      return {
        portrait: tab.coverPortrait?.path,
        square: tab.coverSquare?.path
      }

    case 5: // B站（目前只需要方形4:3）
      return tab.coverSquare?.path

    default:
      return tab.coverSingle?.path
  }
}

// 根据平台ID获取账号列表
const getAccountsByPlatform = (platformId) => {
  const platformMap = {
    1: '小红书',
    2: '视频号',
    3: '抖音',
    4: '快手',
    5: 'B站'
  }
  const platformName = platformMap[platformId]
  return platformName ? accountStore.accounts.filter(acc => acc.platform === platformName) : []
}

// 检查是否可以执行统一发布
const canUnifiedPublish = (tab) => {
  // 检查是否至少选择了一个账号
  const hasSelectedAccounts = tab.selectedUserIds.length > 0

  return (
    tab.fileList.length > 0 &&
    tab.title.trim() !== '' &&
    tab.selectedPlatforms.length > 0 &&
    hasSelectedAccounts &&  // 新增：必须选择账号
    !tab.publishing
  )
}

// 执行统一批量发布
const executeUnifiedPublish = async (tab) => {
  if (!canUnifiedPublish(tab)) {
    ElMessage.warning('请填写完整信息并选择至少一个平台')
    return
  }

  tab.publishing = true
  tab.publishProgress = 0
  tab.publishResults = []

  try {
    // 构建请求数据
    const requestData = {
      // 公共参数
      files: tab.fileList.map(f => f.path),
      title: tab.title,
      desc: tab.desc,

      // 平台列表和配置（每个平台的标签在config中）
      platforms: tab.selectedPlatforms,
      accounts: tab.platformAccounts,
      config: tab.platformConfig,

      // 2种尺寸封面
      covers: {
        portrait: tab.coverPortrait?.path,  // 竖版 (3:4)
        square: tab.coverSquare?.path,       // 方形 (4:3)
      }
    }

    // 调用后端批量发布API
    const response = await http.post('/batchUnifiedPublish', requestData)

    if (response.code === 200 && response.data) {
      // 后端返回实时进度（SSE或轮询）
      // 这里简化处理，假设后端直接返回结果
      
      // 模拟进度更新（实际应该用SSE）
      for (let i = 0; i < response.data.results.length; i++) {
        const result = response.data.results[i]
        tab.publishProgress = Math.floor(((i + 1) / response.data.results.length) * 100)
        tab.publishResults.push(result)
        
        // 短暂延迟让用户看到进度变化
        await new Promise(resolve => setTimeout(resolve, 500))
      }

      // 统计结果
      const successCount = tab.publishResults.filter(r => r.status === 'success').length
      const failCount = tab.publishResults.filter(r => r.status === 'error').length

      if (failCount === 0) {
        ElMessage.success(`🎉 全部发布成功！共 ${successCount} 个平台`)
        tab.publishStatus = { message: `全部发布成功！共 ${successCount} 个平台`, type: 'success' }
      } else {
        ElMessage.warning(`发布完成：${successCount} 成功，${failCount} 失败`)
        tab.publishStatus = { message: `发布完成：${successCount} 成功，${failCount} 失败`, type: 'warning' }
      }
    } else {
      throw new Error(response.msg || '批量发布请求失败')
    }

  } catch (error) {
    console.error('统一发布出错:', error)
    ElMessage.error(`批量发布出错: ${error.message}`)
    tab.publishStatus = { message: `批量发布出错: ${error.message}`, type: 'error' }
    
    // 如果后端不可用，尝试前端逐个调用（备用方案）
    await fallbackUnifiedPublish(tab)
  } finally {
    tab.publishing = false
  }
}

// 备用方案：前端逐个平台发布（当后端API不可用时）
const fallbackUnifiedPublish = async (tab) => {
  try {
    for (let i = 0; i < tab.selectedPlatforms.length; i++) {
      const platformId = tab.selectedPlatforms[i]
      const platformName = getPlatformConfig(platformId).name
      
      tab.publishProgress = Math.floor((i / tab.selectedPlatforms.length) * 100)
      tab.publishResults.push({
        platform: platformName,
        status: 'publishing',
        message: '正在发布...'
      })

      try {
        // 构建单个平台的发布参数
        const singleTabData = {
          fileList: [...tab.fileList],
          displayFileList: [],
          coverSingle: tab.coverSingle,
          selectedAccounts: tab.platformAccounts[platformId] || [],
          selectedPlatform: platformId,
          title: tab.title,
          desc: tab.desc,
          selectedTopics: [...tab.selectedTopics],
          ...getPlatformSpecificConfig(tab, platformId)
        }

        // 调用现有的confirmPublish逻辑（需要适配）
        // 这里简化处理，实际需要根据各平台参数转换
        await new Promise(resolve => setTimeout(resolve, 2000)) // 模拟发布时间
        
        // 更新结果
        const resultIdx = tab.publishResults.findIndex(r => r.platform === platformName)
        if (resultIdx >= 0) {
          tab.publishResults[resultIdx] = {
            platform: platformName,
            status: 'success',
            message: '发布成功'
          }
        }
      } catch (platformError) {
        const resultIdx = tab.publishResults.findIndex(r => r.platform === platformName)
        if (resultIdx >= 0) {
          tab.publishResults[resultIdx] = {
            platform: platformName,
            status: 'error',
            message: platformError.message || '发布失败'
          }
        }
      }
    }
    
    tab.publishProgress = 100
    
  } catch (fallbackError) {
    console.error('备用发布方案也失败:', fallbackError)
  }
}

// 根据平台ID获取该平台的差异化配置
const getPlatformSpecificConfig = (tab, platformId) => {
  const config = tab.platformConfig
  const common = config.common

  switch (platformId) {
    case 3: // 抖音
      return {
        douyinProductTitle: config.douyin.productTitle,
        douyinProductLink: config.douyin.productLink,
        declaration_type: config.douyin.declaration_type,
        collection: common.collection,  // 使用公共合集
        aiDeclaration: common.aiDeclaration  // 使用公共AI声明
      }
    case 5: // B站
      return {
        bilibiliTid: config.bilibili.tid,
        bilibiliAiDeclaration: common.aiDeclaration,  // 使用公共AI声明
        isOriginal: config.bilibili.isOriginal ? 1 : 0,
        collection: common.collection  // 使用公共合集
      }
    case 2: // 视频号（无AI声明）
      return {
        isDraft: config.channels.isDraft,
        isOriginal: config.channels.isOriginal,
        declareOriginal: config.channels.isOriginal,
        tencentDeclareOriginal: config.channels.isOriginal,
        collection: common.collection  // 使用公共合集
      }
    case 1: // 小红书
      return {
        xiaohongshu_declaration: config.xiaohongshu.declaration || (common.aiDeclaration ? '笔记含AI合成内容' : ''),
        isOriginal: config.xiaohongshu.isOriginal,
        collection: common.collection  // 使用公共合集
      }
    case 4: // 快手
      return {
        kuaishou_declaration: config.kuaishou.declaration || (common.aiDeclaration ? '内容为AI生成' : ''),
        collection: common.collection  // 使用公共合集
      }
    default:
      return {}
  }
}

// 声明类型变更时设置子级默认值
const onDeclarationTypeChange = (tab) => {
  if (tab.declaration_type === '内容取材网络') {
    tab.declaration_network_subtype = '取材站外'
  } else {
    tab.declaration_network_subtype = ''
  }
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

const removeCover = (tab, target) => {
  setCoverFile(tab, target, null)
  ElMessage.success('封面已移除')
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
  accountDialogVisible.value = true
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

// 确认发布
const confirmPublish = async (tab) => {
  // 防止重复点击
  if (tab.publishing) {
    throw new Error('正在发布中，请稍候...')
  }

  tab.publishing = true // 设置发布状态为进行中

  // 数据验证
  if (tab.fileList.length === 0) {
    ElMessage.error('请先上传视频文件')
    tab.publishing = false
    throw new Error('请先上传视频文件')
  }
  if (!tab.title.trim()) {
    ElMessage.error('请输入标题')
    tab.publishing = false
    throw new Error('请输入标题')
  }
  if (!tab.selectedPlatform) {
    ElMessage.error('请选择发布平台')
    tab.publishing = false
    throw new Error('请选择发布平台')
  }
  if (tab.selectedAccounts.length === 0) {
    ElMessage.error('请选择发布账号')
    tab.publishing = false
    throw new Error('请选择发布账号')
  }

  // 构造发布数据，符合后端API格式
  const publishData = {
    type: tab.selectedPlatform,
    title: tab.title,
    desc: tab.desc?.trim() || '',
    tags: tab.selectedTopics, // 不带#号的话题列表
    fileList: tab.fileList.map(file => file.path), // 只发送文件路径
    accountList: tab.selectedAccounts.map(accountId => {
      const account = accountStore.accounts.find(acc => acc.id === accountId)
      return account ? account.filePath : accountId
    }), // 发送账号的文件路径
    enableTimer: tab.scheduleEnabled ? 1 : 0,
    videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1,
    dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'],
    startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0,
    declareOriginal: tab.isOriginal, // 原创声明
    tencentDeclareOriginal: tab.selectedPlatform === 2 ? tab.isOriginal : false, // 视频号原创声明
    productLink: tab.douyinProductLink.trim() || '',
    productTitle: tab.douyinProductTitle.trim() || '',
    thumbnail: tab.coverSingle?.path || '',
    thumbnailLandscape: tab.coverSingle?.path || tab.coverLandscape?.path || '',
    thumbnailPortrait: tab.coverPortrait?.path || '',
    declaration_info: tab.declaration_type ? {
      declaration_type: tab.declaration_type.trim(),
      declaration_location: Array.isArray(tab.declaration_location) ? tab.declaration_location : [],
      declaration_date: tab.declaration_date || '',
      isDraft: tab.isDraft
    } : null,
    isDraft: tab.isDraft,
    // 快手作者声明参数
    kuaishouDeclaration: tab.kuaishou_declaration || '内容为AI生成',
    // 小红书声明参数
    xiaohongshuDeclaration: tab.xiaohongshu_declaration || '',
    bilibiliTid: tab.bilibiliTid || 218, // B站分区ID（动物圈）
    bilibiliAiDeclaration: tab.bilibiliAiDeclaration || false, // B站创作声明：含AI生成内容
    noReprint: tab.isOriginal ? 1 : 0, // 声明原创时禁止转载
    collection: tab.collection || '大学篇' // 合集名称
  }

  // 校验“内容自行拍摄”时必须选择地点与日期
  if (tab.declaration_type === '内容自行拍摄') {
    const hasLocation = Array.isArray(tab.declaration_location) && tab.declaration_location.length > 0
    const hasDate = !!tab.declaration_date
    if (!(hasLocation && hasDate)) {
      ElMessage.error('请选择拍摄位置和拍摄时间')
      tab.publishing = false
      reject(new Error('请选择拍摄位置和拍摄时间'))
      return
    }
  }

  // 调用后端发布API（使用统一的http封装）
  try {
    const data = await http.post('/postVideo', publishData)
    tab.publishStatus = {
      message: '发布成功',
      type: 'success'
    }
    // 清空当前tab的数据
    tab.fileList = []
    tab.displayFileList = []
    tab.title = ''
    tab.selectedTopics = []
    tab.selectedAccounts = []
    tab.scheduleEnabled = false
    tab.coverSingle = null
    tab.coverPortrait = null
    tab.coverLandscape = null
  } catch (error) {
    console.error('发布错误:', error)
    tab.publishStatus = {
      message: `发布失败：${error.message || '请检查网络连接'}`,
      type: 'error'
    }
    throw error
  } finally {
    tab.publishing = false
  }
}

// 显示上传选项
const showUploadOptions = (tab, target = UPLOAD_TARGETS.VIDEO) => {
  currentUploadTab.value = tab
  currentUploadTarget.value = target
  uploadOptionsVisible.value = true
}

// 选择本地上传
const selectLocalUpload = () => {
  uploadOptionsVisible.value = false
  localUploadVisible.value = true
}

// 选择素材库
const selectMaterialLibrary = async () => {
  uploadOptionsVisible.value = false
  
  // 如果素材库为空，先获取素材数据
  if (materials.value.length === 0) {
    try {
      const response = await syncMaterials()
      if (response.code === 200) {
        if (selectableMaterials.value.length === 0) {
          ElMessage.warning(currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? '素材库中暂无视频素材' : '素材库中暂无图片素材')
          return
        }
      }
    } catch (error) {
      console.error('获取素材列表出错:', error)
      ElMessage.error('获取素材列表失败')
      return
    }
  }

  if (selectableMaterials.value.length === 0) {
    ElMessage.warning(currentUploadTarget.value === UPLOAD_TARGETS.VIDEO ? '素材库中暂无视频素材' : '素材库中暂无图片素材')
    return
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

  if (isCoverUploadTarget.value && selectedMaterials.value.length > 1) {
    ElMessage.warning('封面一次只能选择一个素材')
    return
  }
  
  if (currentUploadTab.value) {
    selectedMaterials.value.forEach(materialId => {
      const material = selectableMaterials.value.find(m => m.id === materialId)
      if (!material) {
        return
      }

      const fileInfo = buildFileInfo({
        name: material.filename,
        path: material.file_path,
        size: material.filesize * 1024 * 1024,
        type: isImageMaterial(material) ? 'image/*' : 'video/*'
      })

      if (currentUploadTarget.value === UPLOAD_TARGETS.VIDEO) {
        const exists = currentUploadTab.value.fileList.some(file => file.path === fileInfo.path)
        if (!exists) {
          currentUploadTab.value.fileList.push(fileInfo)
        }
        return
      }

      setCoverFile(currentUploadTab.value, currentUploadTarget.value, fileInfo)
    })
    
    if (currentUploadTarget.value === UPLOAD_TARGETS.VIDEO) {
      currentUploadTab.value.displayFileList = [...currentUploadTab.value.fileList.map(item => ({
        name: item.name,
        url: item.url
      }))]
    }
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

// ==================== 截图预览功能 ====================
const screenshotPreviewVisible = ref(false)
const currentScreenshotUrl = ref('')

const showScreenshotPreview = (screenshotUrl) => {
  // 构建完整的URL（如果后端API不是同源，需要添加baseURL）
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  currentScreenshotUrl.value = baseURL + screenshotUrl
  screenshotPreviewVisible.value = true
}

const closeScreenshotPreview = () => {
  screenshotPreviewVisible.value = false
  currentScreenshotUrl.value = ''
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
             background-color: #409eff;
             border-color: #409eff;
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
        
        .add-tab-btn,
        .batch-publish-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
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
        .cover-section,
        .account-section,
        .platform-section,
        .title-section,
        .douyinProduct-section,
        .topic-section,
        .schedule-section {
          margin-bottom: 30px;
        }

        .douyinProduct-section {
          .douyinProduct-name-input,
          .douyinProduct-link-input {
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

        .cover-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 16px;
        }

        .cover-card {
          border: 1px solid #ebeef5;
          border-radius: 8px;
          padding: 14px;
          background-color: #fafafa;

          .cover-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
            font-weight: 500;
            color: #303133;
          }

          .cover-empty {
            color: #909399;
            font-size: 13px;
            min-height: 32px;
            display: flex;
            align-items: center;
          }

          .cover-file-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            background-color: #fff;
            border-radius: 6px;

            .el-link {
              max-width: 180px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .file-size {
              color: #909399;
              font-size: 13px;
              margin-left: auto;
            }
          }

          .cover-platform-hint {
            margin-top: 12px;
            padding: 8px 10px;
            background-color: #ecf5ff;
            border-left: 3px solid #409EFF;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
            color: #409EFF;
            font-size: 12px;

            .el-icon {
              flex-shrink: 0;
            }
          }
        }
        
        .account-input {
          max-width: 400px;
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
        }

        .channelsDraft-section {
          margin: 20px 0;

          .channelsDraft-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .declareOriginal-section {
          margin: 10px 0 20px;

          .declareOriginal-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .collection-section {
          margin: 20px 0;
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

// ==================== 统一发布（一键发布）样式 ====================
.unified-publish-container {
  max-width: 900px;
  margin: 0 auto;
  
  .section-card {
    margin-bottom: 20px;
    
    .card-title {
      font-size: 16px;
      font-weight: bold;
      color: #303133;
    }
    
    .form-item {
      margin-bottom: 15px;
      
      > label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: #606266;
      }
      
      .uploaded-files-inline {
        margin-top: 10px;
        
        .el-tag {
          margin-right: 8px;
          margin-bottom: 5px;
        }
      }
      
      .cover-preview {
        margin-top: 10px;
      }
      
      .tags-input {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 5px;
      }
    }
    
    .account-config-item {
      margin-bottom: 15px;
      padding: 12px;
      background-color: #f5f7fa;
      border-radius: 4px;

      > label {
        font-weight: 500;
        color: #606266;
        margin-bottom: 5px;
        display: block;
      }
    }

    // 账号搜索选项样式
    .account-option {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;

        &.status-normal {
          background-color: #67c23a;
        }

        &.status-error {
          background-color: #f56c6c;
        }
      }
    }

    // 已选账号展示区
    .selected-accounts-display {
      margin-top: 20px;
      padding: 15px;
      background-color: #f0f9eb;
      border: 1px solid #e1f3d8;
      border-radius: 4px;

      .platform-account-group {
        display: flex;
        align-items: flex-start;
        margin-bottom: 12px;
        padding: 10px;
        background-color: #fff;
        border-radius: 4px;
        border: 1px solid #ebeef5;

        &:last-child {
          margin-bottom: 0;
        }

        .platform-label {
          min-width: 80px;
          font-weight: 500;
          padding-top: 4px;
        }

        .account-list-in-platform {
          flex: 1;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;

          .account-tag-item {
            .el-tag {
              max-width: 200px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
          }

          .no-account-hint {
            color: #909399;
            font-size: 12px;
            line-height: 32px;
          }
        }
      }
    }

    // 账号配置提示
    .account-config-tips {
      margin-top: 15px;
    }

    // 自动检测到的平台
    .auto-detected-platforms {
      margin-top: 20px;
      padding: 15px;
      background-color: #ecf5ff;
      border: 1px solid #d9ecff;
      border-radius: 4px;

      .platform-tags-display {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;

        .el-tag {
          font-size: 14px;
          padding: 6px 12px;
        }
      }
    }

    // 未选择账号时的提示
    .no-platform-hint {
      margin-top: 15px;
    }

    // 公共设置样式
    .common-settings {
      background-color: #f0f9ff;
      border: 1px solid #b3d8ff;
    }

    // 封面配置样式
    .cover-settings {
      background-color: #fdf6ec;
      border: 1px solid #faecd8;

      // 3种尺寸封面上传容器
      .cover-upload-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
        margin-bottom: 20px;

        @media (max-width: 768px) {
          grid-template-columns: 1fr;
        }

        .cover-size-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 15px;
          background-color: #fff;
          border-radius: 8px;
          border: 2px dashed #dcdfe6;
          transition: all 0.3s;

          &:hover {
            border-color: #409EFF;
            box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
          }

          // 封面预览区域
          .cover-preview {
            width: 120px;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #f5f7fa;
            border-radius: 4px;
            margin-bottom: 10px;
            overflow: hidden;

            &.portrait {
              aspect-ratio: 3/4;  // 竖版
              height: 140px;
              width: auto;
            }

            &.square {
              aspect-ratio: 4/3;  // 方形
              width: 130px;
              height: auto;
            }

            img {
              width: 100%;
              height: 100%;
              object-fit: cover;
            }
          }

          // 封面信息
          .cover-info {
            text-align: center;

            .cover-label {
              display: block;
              font-weight: 600;
              color: #303133;
              margin-bottom: 5px;
              font-size: 14px;
            }

            .cover-platforms {
              display: block;
              font-size: 11px;
              color: #909399;
              margin-bottom: 8px;
              line-height: 1.4;
            }

            .file-name {
              display: block;
              margin-top: 5px;
              color: #67c23a;
              font-size: 11px;
              max-width: 150px;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
          }
        }
      }

      // 平台-尺寸映射展示区
      .platform-cover-mapping {
        margin-top: 20px;
        padding: 15px;
        background-color: #fff;
        border-radius: 4px;
        border: 1px solid #e4e7ed;

        .mapping-list {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;

          .mapping-item {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 5px 10px;
            background-color: #f5f7fa;
            border-radius: 4px;

            .mapping-arrow {
              color: #909399;
              font-weight: bold;
            }
          }
        }
      }
    }
    
    .platform-specific-settings {
      margin-bottom: 20px;
      padding: 15px;
      border: 1px solid #ebeef5;
      border-radius: 4px;
      background-color: #fafafa;
      
      .platform-title {
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid currentColor;
      }
    }
  }
  
  .unified-publish-actions {
    margin: 30px 0;
    text-align: center;
  }
  
  .publish-results-list {
    margin-top: 20px;
    
    .result-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      margin-bottom: 8px;
      border-radius: 4px;
      background-color: #f5f7fa;
      
      &.success {
        background-color: #f0f9eb;
        color: #67c23a;
      }
      
      &.error {
        background-color: #fef0f0;
        color: #f56c6c;
      }
      
      &.publishing {
        background-color: #ecf5ff;
        color: #409eff;
      }
      
      .label {
        font-weight: bold;
        min-width: 60px;
      }
      
      .message {
        flex: 1;
      }
    }
  }
}

// 截图预览弹窗样式
.screenshot-preview-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  
  .image-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    color: #909399;
    
    .el-icon {
      font-size: 48px;
      margin-bottom: 10px;
    }
  }
}
</style>
