<template>
  <div class="material-library-container">
    <h1>素材库</h1>
    
    <!-- 操作栏 -->
    <div class="action-bar">
      <button class="upload-btn" @click="showUploadModal">
        <i class="upload-icon">↑</i> 上传素材
      </button>
      <button class="batch-btn">
        批量操作
      </button>
      <!-- 添加搜索框 -->
      <div class="search-container">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="搜索素材名称" 
          class="search-input"
          @input="searchMaterials"
        />
        <i class="search-icon">🔍</i>
      </div>
    </div>
    
    <!-- 素材列表 -->
    <div v-if="filteredMaterials.length > 0" class="materials-grid">
      <div v-for="material in filteredMaterials" :key="material.file_name" class="material-card">
        <!-- 视频预览 -->
        <div class="material-preview">
          <img src="@/assets/bofang.png" alt="播放图标" class="play-icon">
          <button class="delete-btn" @click="deleteMaterial(material)" title="删除素材">×</button>
        </div>
        
        <!-- 素材信息 -->
        <div class="material-info">
          <div class="material-name">{{ material.filename }}</div>
          <div class="material-meta">
            <!-- <span>{{ material.filename }}</span> -->
            <span>{{ formatFileSize(material.filesize) }}</span>
            <span>{{ formatDate(material.upload_time) }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <div class="empty-image"></div>
      <p class="empty-text">暂无素材，点击上传素材按钮添加</p>
    </div>
    
    <!-- 上传素材弹窗 -->
    <div class="upload-modal" v-if="isUploadModalVisible">
      <div class="upload-modal-content">
        <div class="modal-header">
          <h3>上传素材</h3>
          <button class="close-btn" @click="hideUploadModal">×</button>
        </div>
        <div class="modal-body">
          <div class="filename-input">
            <input 
              type="text" 
              v-model="customFilename" 
              placeholder="输入文件名称（可选）" 
              class="filename-field"
            />
          </div>
          
          <div class="upload-area" @click="triggerFileInput">
            <div v-if="!selectedFile" class="upload-placeholder">
              <span>点击上传素材</span>
              <div class="upload-hint">图片最大支持20M</div>
            </div>
            <div v-else class="preview-container">
              <video v-if="isVideo(selectedFile.name)" controls class="file-preview">
                <source :src="previewUrl" type="video/mp4">
              </video>
              <img v-else :src="previewUrl" alt="预览" class="file-preview">
              <button class="remove-file-btn" @click.stop="removeSelectedFile">×</button>
            </div>
          </div>
          
          <div class="modal-footer">
            <button class="cancel-btn" @click="hideUploadModal">取消</button>
            <button 
              class="upload-submit-btn" 
              :disabled="!selectedFile || isUploading" 
              @click="uploadMaterial"
            >
              {{ isUploading ? '上传中...' : '上传' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 隐藏的文件输入 -->
    <input 
      type="file" 
      ref="fileInput" 
      style="display: none" 
      @change="handleFileSelected" 
      accept="image/*,video/*"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';

// 素材列表
const materials = ref([]);
const filteredMaterials = ref([]);
const searchQuery = ref('');

// 上传弹窗状态
const isUploadModalVisible = ref(false);
const isUploading = ref(false);
const selectedFile = ref(null);
const previewUrl = ref('');
const customFilename = ref('');
const fileInput = ref(null);

// 显示上传弹窗
const showUploadModal = () => {
  isUploadModalVisible.value = true;
  selectedFile.value = null;
  previewUrl.value = '';
  customFilename.value = '';
  // 重置文件输入框，确保每次打开弹窗都能正常选择文件
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

// 隐藏上传弹窗
const hideUploadModal = () => {
  isUploadModalVisible.value = false;
  // 清理预览URL
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
    previewUrl.value = '';
  }
};

// 移除点击弹窗外部关闭的函数，不再需要
// const closeModalOnOutsideClick = (event) => {
//   if (event.target.classList.contains('upload-modal')) {
//     hideUploadModal();
//   }
// };

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value?.click();
};

// 处理文件选择
const handleFileSelected = (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
    previewUrl.value = URL.createObjectURL(file);
    
    // 如果没有自定义文件名，使用原始文件名
    if (!customFilename.value) {
      customFilename.value = file.name;
    }
  }
};

// 移除已选择的文件
const removeSelectedFile = () => {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value);
  }
  selectedFile.value = null;
  previewUrl.value = '';
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

// 上传素材
const uploadMaterial = async () => {
  if (!selectedFile.value) return;
  
  isUploading.value = true;
  
  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    console.log('上传文件:', selectedFile.value);
    console.log('上传文件类型：', selectedFile.value.type);
    
    // 使用自定义文件名或原始文件名
    const filename = customFilename.value || selectedFile.value.name;
    formData.append('filename', filename);
    console.log('上传文件名:', filename);
    
    const response = await axios.post('/api/uploadSave', formData);
    console.log('上传响应:', response.data);
    if (response.data.code === 200) {
      // 上传成功，刷新素材列表
      fetchMaterials();
      hideUploadModal();
    } else {
      alert('上传失败: ' + (response.data.message || '未知错误'));
    }
  } catch (error) {
    console.error('上传素材失败:', error);
    alert('上传失败: ' + (error.response?.data?.message || error.message || '未知错误'));
  } finally {
    isUploading.value = false;
  }
};

// 搜索素材
const searchMaterials = () => {
  if (!searchQuery.value) {
    filteredMaterials.value = materials.value;
    return;
  }
  
  const query = searchQuery.value.toLowerCase();
  filteredMaterials.value = materials.value.filter(material => {
    return material.filename && material.filename.toLowerCase().includes(query);
  });
};

// 获取素材列表
const fetchMaterials = async () => {
  try {
    const response = await axios.get(`/api/getFiles`);
    console.log('获取素材列表响应:', response.data);
    
    if (response.data.code === 200) {
      // 处理文件路径，添加完整的请求地址
      const materialItems = (response.data.data || []).map(item => {
        return {
          ...item,
          file_path: `/api${item.file_path}` // 添加API前缀到文件路径
        };
      });
      
      // 对每个素材调用getFile接口获取视频数据
      const materialPromises = materialItems.map(async (item) => {
        try {
          // 从file_path中提取文件名
          const filename = item.file_path.split('/').pop();
          if (!filename) return item;
          
          // 调用getFile接口获取视频数据
          const fileResponse = await axios.get(`/api/getFile`, {
            params: { filename: filename }
          });
          
          console.log(`获取素材 ${filename} 数据:`, fileResponse.data);
          
          if (fileResponse.data.code === 200) {
            // 将获取的视频数据合并到素材对象中
            return {
              ...item,
              videoData: fileResponse.data.data
            };
          }
          return item;
        } catch (error) {
          console.error(`获取素材 ${item.filename || item.file_name} 数据失败:`, error);
          return item;
        }
      });
      
      // 等待所有getFile请求完成
      materials.value = await Promise.all(materialPromises);
      
      // 初始化过滤后的素材列表
      filteredMaterials.value = materials.value;
      console.log('处理后的素材列表:', materials.value);
    } else {
      console.error('获取素材列表失败:', response.data.message);
    }
  } catch (error) {
    console.error('获取素材列表失败:', error);
  }
};

// 删除素材
const deleteMaterial = async (material) => {
  console.log('要删除的素材:', material);
  if (confirm(`确定要删除素材 ${material.filename || material.file_name} 吗？`)) {
    try {
      // 调用删除API
      const response = await axios.get(`/api/deleteFile?id=${material.id}`);
      console.log('删除素材响应:', response.data);
      
      if (response.data.code === 200) {
        // 删除成功，刷新素材列表
        fetchMaterials();
        alert('删除成功');
      } else {
        alert('删除失败: ' + (response.data.message || '未知错误'));
      }
    } catch (error) {
      console.error('删除素材失败:', error);
      alert('删除失败: ' + (error.response?.data?.message || error.message || '未知错误'));
    }
  }
};

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

// 格式化日期
const formatDate = (timestamp) => {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 判断是否为视频文件
const isVideo = (filename) => {
  if (!filename) return false;
  const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'];
  return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext));
};

// 组件挂载时获取素材列表
onMounted(() => {
  fetchMaterials();
});
</script>

<style scoped>
.material-library-container {
  padding: 20px;
}

h1 {
  margin-bottom: 20px;
  font-size: 24px;
  font-weight: 500;
}

/* 操作栏样式 */
.action-bar {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 20px;
  gap: 15px;
  align-items: center;
}

.upload-btn {
  background-color: #6366f1;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 15px;
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 14px;
}

.upload-icon {
  margin-right: 5px;
  font-size: 16px;
}

.batch-btn {
  background-color: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 8px 15px;
  cursor: pointer;
  font-size: 14px;
}

/* 素材网格样式 */
.materials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.material-card {
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}

.material-card:hover {
  transform: translateY(-5px);
}

.material-preview {
  position: relative;
  height: 150px;
  background-color: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.material-preview video,
.material-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.delete-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
  opacity: 0;
  transition: opacity 0.2s;
}

.material-card:hover .delete-btn {
  opacity: 1;
}

.material-info {
  padding: 10px;
}

.material-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.material-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  background-color: #fff;
  border-radius: 8px;
  margin-top: 20px;
}

.empty-image {
  width: 120px;
  height: 120px;
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23d1d5db" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>');
  background-repeat: no-repeat;
  background-position: center;
  background-size: contain;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-text {
  color: #9ca3af;
  font-size: 14px;
}

/* 上传弹窗样式 */
.upload-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.upload-modal-content {
  background-color: white;
  border-radius: 8px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}

.modal-body {
  padding: 20px;
}

.filename-input {
  margin-bottom: 15px;
}

.filename-field {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 20px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area:hover {
  border-color: #6366f1;
}

.upload-placeholder {
  color: #666;
}

.upload-hint {
  margin-top: 10px;
  font-size: 12px;
  color: #999;
}

.preview-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-preview {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
}

.remove-file-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.cancel-btn {
  padding: 8px 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background-color: white;
  cursor: pointer;
}

.upload-submit-btn {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  background-color: #6366f1;
  color: white;
  cursor: pointer;
}

.upload-submit-btn:disabled {
  background-color: #a5a6f6;
  cursor: not-allowed;
}

/* 搜索框样式 */
.search-container {
  position: relative;
  flex-grow: 1;
  max-width: 300px;
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 30px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: #6366f1;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  color: #999;
}
</style>