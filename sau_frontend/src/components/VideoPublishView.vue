<template>
	<div class="video-publish-container">
		<!-- 视频上传区域 -->
		<div class="section">
			<div class="section-title">视频</div>
			<div class="videos-container">
				<div class="video-upload-area" @click="showSourceSelector" v-if="videoList.length < 5">
					<div class="upload-icon">
						<span class="icon">↑</span>
						<span class="text">上传</span>
					</div>
				</div>
				<div v-for="(video, index) in videoList" :key="index" class="video-preview">
					<video controls :src="video.previewUrl"></video>
					<div class="video-actions">
						<button class="remove-btn" @click.stop="removeVideo(index)">删除</button>
					</div>
				</div>
			</div>
			<div class="video-count" v-if="videoList.length > 0">
				已上传 {{ videoList.length }} 个视频 (最多5个)
			</div>
			<input type="file" ref="videoInput" accept="video/*" style="display: none" @change="handleVideoUpload" />

			<!-- 视频来源选择器 -->
			<div class="source-selector" v-if="isSourceSelectorVisible" @click="hideSourceSelector">
				<div class="source-selector-content" @click.stop>
					<div class="source-option" @click="selectLocalSource">
						<span>本地视频</span>
					</div>
					<div class="source-option" @click="showMaterialLibrary">
						<span>素材库</span>
					</div>
				</div>
			</div>

			<!-- 素材库选择弹窗 -->
			<div class="material-library-modal" v-if="isMaterialLibraryVisible" @click="closeMaterialLibraryOnOutsideClick">
				<div class="material-library-content">
					<div class="modal-header">
						<h3>选择素材</h3>
						<button class="close-btn" @click="hideMaterialLibrary">×</button>
					</div>
					<div class="modal-body">
						<div v-if="isLoadingMaterials" class="loading-materials">
							<span>加载素材中...</span>
						</div>
						<div v-else-if="materialList.length === 0" class="no-materials">
							<span>暂无可用素材</span>
						</div>
						<div v-else class="material-grid">
							<div v-for="material in materialList" :key="material.id" class="material-item"
								:class="{ 'selected': selectedMaterial === material.id }" @click="selectMaterial(material)">
								<div class="material-checkbox">
									<div class="checkbox" :class="{ 'checked': selectedMaterial === material.id }"></div>
								</div>
								<div class="material-preview">
									<img src="@/assets/bofang.png" alt="播放图标" class="play-icon">
								</div>
								<div class="material-info">
									<div class="material-name">{{ material.filename }}</div>
								</div>
							</div>
						</div>
					</div>
					<div class="modal-footer">
						<button class="cancel-btn" @click="hideMaterialLibrary">取消</button>
						<button class="confirm-btn" @click="confirmMaterialSelection" :disabled="!selectedMaterial">确认</button>
					</div>
				</div>
			</div>
		</div>

		<!-- 账号选择区域 -->
		<div class="section">
			<div class="section-title">账号</div>
			<div class="account-selector" @click="showAccountSelector">
				<div v-if="selectedAccounts.length === 0" class="account-placeholder">
					<span>+ 添加账号</span>
				</div>
				<div v-else class="selected-accounts-container">
					<div v-for="(account, index) in selectedAccounts" :key="account.id" class="selected-account">
						<img :src="account.avatar" alt="账号头像" class="account-avatar" />
						<span class="account-name">{{ account.name }}</span>
						<span class="account-status" :class="account.statusType">{{ account.status }}</span>
						<button class="remove-account-btn" @click.stop="removeAccount(index)">×</button>
					</div>
					<div class="add-more-account" @click.stop="showAccountSelector">
						<span>+ 添加更多</span>
					</div>
				</div>
			</div>
		</div>

		<!-- 账号选择弹窗 -->
		<div class="account-selector-modal" v-if="isAccountSelectorVisible" @click="closeModalOnOutsideClick">
			<div class="account-selector-content">
				<div class="modal-header">
					<h3>选择账号</h3>
					<button class="refresh-btn" @click.stop="refreshAccounts" title="刷新账号列表">
						<span class="refresh-icon">↻</span>
					</button>
					<button class="close-btn" @click="hideAccountSelector">×</button>
				</div>
				<div class="modal-body">
					<div v-if="isAccountsLoading" class="loading-accounts">
						<span>加载账号中...</span>
					</div>
					<div v-else-if="accountList.length === 0" class="no-accounts">
						<span>暂无可用账号</span>
					</div>
					<div v-else class="account-list">
						<div v-for="account in accountList" :key="account.id" class="account-item"
							:class="{ 'selected': isAccountSelected(account) }" @click="selectAccount(account)">
							<div class="account-checkbox">
								<div class="checkbox" :class="{ 'checked': isAccountSelected(account) }"></div>
							</div>
							<img :src="account.avatar" alt="账号头像" class="account-avatar" />
							<div class="account-info">
								<div class="account-name">{{ account.name }}</div>
								<div class="account-status" :class="account.statusType">{{ account.status }}</div>
							</div>
						</div>
					</div>
				</div>
				<div class="modal-footer">
					<button class="cancel-btn" @click="hideAccountSelector">取消</button>
					<button class="confirm-btn" @click="confirmAccountSelection">确认</button>
				</div>
			</div>
		</div>

		<!-- 平台选择区域 -->
		<div class="section">
			<div class="section-title">平台</div>
			<div class="platform-selector">
				<button class="platform-btn" :class="{ 'active': selectedPlatform === 3 }" @click="selectPlatform(3)">
					抖音
				</button>
				<button class="platform-btn" :class="{ 'active': selectedPlatform === 4 }" @click="selectPlatform(4)">
					快手
				</button>
				<button class="platform-btn" :class="{ 'active': selectedPlatform === 2 }" @click="selectPlatform(2)">
					视频号
				</button>
				<button class="platform-btn" :class="{ 'active': selectedPlatform === 1 }" @click="selectPlatform(1)">
					小红书
				</button>
			</div>
		</div>

		<!-- 标题输入区域 -->
		<div class="section">
			<div class="section-title">标题</div>
			<div class="title-input-container">
				<textarea v-model="title" @input="updateCharCount" placeholder="请输入标题" maxlength="100"
					rows="2"></textarea>
				<div class="char-count">{{ charCount }}/100</div>
			</div>
		</div>

		<!-- 话题选择区域 -->
		<div class="section">
			<div class="section-title">话题</div>
			<div class="tags-container">
				<div v-for="(tag, index) in tags" :key="index" class="tag">
					{{ tag }}
					<span class="remove-tag" @click="removeTag(index)">×</span>
				</div>
				<div class="add-tag" @click="showTagSelector">+ 添加话题</div>
			</div>
		</div>

		<!-- 话题选择弹窗 -->
		<div class="tag-selector-modal" v-if="isTagSelectorVisible" @click="closeTagSelectorOnOutsideClick">
			<div class="tag-selector-content">
				<div class="modal-header">
					<h3>选择话题</h3>
					<button class="close-btn" @click="hideTagSelector">×</button>
				</div>
				<div class="modal-body">
					<div class="custom-tag-input">
						<input v-model="customTag" placeholder="输入自定义话题" @keyup.enter="addCustomTag" />
						<button @click="addCustomTag">添加</button>
					</div>
					<div class="suggested-tags">
						<h4>推荐话题</h4>
						<div class="tag-grid">
							<div v-for="tag in suggestedTags" :key="tag" class="suggested-tag"
								@click="addSuggestedTag(tag)">
								{{ tag }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- 位置输入区域 -->
		<!-- <div class="section">
			<div class="section-title">位置</div>
			<div class="location-input-container">
				<input v-model="location" placeholder="请输入位置" maxlength="50" />
			</div>
		</div> -->

		<!-- 定时发布设置区域 -->
		<div class="section">
			<div class="section-title">定时发布</div>
			<div class="timer-toggle">
				<label class="switch">
					<input type="checkbox" v-model="enableTimer">
					<span class="slider round"></span>
				</label>
				<span>{{ enableTimer ? '已开启' : '已关闭' }}</span>
			</div>

			<div class="timer-settings" v-if="enableTimer">
				<div class="setting-item">
					<label>每天发布视频数</label>
					<select v-model="videosPerDay">
						<option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
					</select>
				</div>

				<div class="setting-item">
					<label>每天发布时间</label>
					<div class="time-slots">
						<div v-for="(time, index) in dailyTimes" :key="index" class="time-slot">
							<input type="time" v-model="dailyTimes[index]">
							<button v-if="dailyTimes.length > 1" @click="removeTimeSlot(index)"
								class="remove-time-btn">×</button>
						</div>
						<button v-if="dailyTimes.length < videosPerDay" @click="addTimeSlot" class="add-time-btn">+
							添加时间</button>
					</div>
				</div>

				<div class="setting-item">
					<label>开始天数</label>
					<select v-model="startDays">
						<option :value="0">明天</option>
						<option :value="1">后天</option>
					</select>
				</div>
			</div>
		</div>

		<!-- 操作按钮区域 -->
		<div class="action-buttons">
			<button class="preview-btn" @click="previewContent" :disabled="videoList.length === 0 || isUploading">
				预览
			</button>
			<button class="publish-btn" @click="publishContent"
				:disabled="videoList.length === 0 || !title || selectedAccounts.length === 0 || !selectedPlatform || isUploading">
				{{ isUploading ? '上传中...' : '发布' }}
			</button>
		</div>
	</div>
</template>

<script setup>
	import { ref, onMounted, onUnmounted, watch, defineProps } from 'vue';
import { useRoute } from 'vue-router';
import { API_BASE_URL, globalAccountsCache } from '../config';
import axios from 'axios';
import tx from '@assets/fengbaobao.png'

// 定义props接收路由参数
const props = defineProps({
  id: {
    type: String,
    required: true
  }
});

	// 使用路由参数作为组件实例的唯一标识
	const route = useRoute();
	const suggestedTags = ['游戏', '电影', '音乐', '美食', '旅行', '文化', '科技', '生活', '娱乐', '体育', '教育', '艺术', '健康', '时尚', '美食', '旅行', '文化', '科技', '生活', '娱乐', '体育', '教育', '艺术', '健康', '时尚'];
	const instanceId = route.params.id || Date.now().toString();

	// 组件状态
	// 组件状态
	const videoInput = ref(null);
	const videoList = ref([]); // 修改为视频列表
	const title = ref('');
	const charCount = ref(0);
	const tags = ref([]);
	const location = ref('');
	const file_list = ref([]); // 保存上传后的fileID
	const isUploading = ref(false); // 上传状态
	const customTag = ref(''); // 自定义话题输入
	const isTagSelectorVisible = ref(false); // 话题选择器是否可见

	// 视频来源选择器相关
	const isSourceSelectorVisible = ref(false); // 视频来源选择器是否可见

	// 素材库选择相关
	const isMaterialLibraryVisible = ref(false); // 素材库选择器是否可见
	const isLoadingMaterials = ref(false); // 素材加载状态
	const materialList = ref([]); // 素材列表
	const selectedMaterial = ref(null); // 选中的素材ID

	// 账号选择相关
	const selectedAccounts = ref([]); // 选中的账号列表
	const tempSelectedAccounts = ref([]); // 临时选中的账号列表，用于确认前的暂存
	const isAccountSelectorVisible = ref(false); // 账号选择器是否可见
	const isAccountsLoading = ref(false); // 账号加载状态
	const accountList = ref([]); // 账号列表
	const account_list = ref([]); // 保存选中账号的cookie

	// 平台选择相关
	const selectedPlatform = ref(null); // 选中的平台：3-抖音，2-视频号，1-小红书

	// 定时发布相关
	const enableTimer = ref(false); // 是否启用定时发布
	const videosPerDay = ref(1); // 每天发布视频数
	const dailyTimes = ref(['08:00']); // 每天发布时间
	const startDays = ref(0); // 开始天数：0-明天，1-后天

	// 触发视频上传
	const triggerVideoUpload = () => {
		videoInput.value?.click();
	};

	// 显示视频来源选择器
	const showSourceSelector = () => {
		isSourceSelectorVisible.value = true;
	};

	// 隐藏视频来源选择器
	const hideSourceSelector = () => {
		isSourceSelectorVisible.value = false;
	};

	// 选择本地视频源
	const selectLocalSource = () => {
		hideSourceSelector();
		triggerVideoUpload();
	};

	// 显示素材库
	const showMaterialLibrary = () => {
		hideSourceSelector();
		isMaterialLibraryVisible.value = true;
		fetchMaterials();
	};

	// 隐藏素材库
	const hideMaterialLibrary = () => {
		isMaterialLibraryVisible.value = false;
		selectedMaterial.value = null;
	};

	// 点击素材库外部关闭
	const closeMaterialLibraryOnOutsideClick = (event) => {
		if (event.target.classList.contains('material-library-modal')) {
			hideMaterialLibrary();
		}
	};

	// 获取素材列表
	const fetchMaterials = async () => {
		isLoadingMaterials.value = true;
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
				materialList.value = await Promise.all(materialPromises);
				
				console.log('处理后的素材列表:', materialList.value);
			} else {
				console.error('获取素材列表失败:', response.data.message);
			}
		} catch (error) {
			console.error('获取素材列表失败:', error);
		} finally {
			isLoadingMaterials.value = false;
		}
	};

	// 选择素材
	const selectMaterial = (material) => {
		// 如果点击的是已选中的素材，则取消选择
		if (selectedMaterial.value === material.id) {
			selectedMaterial.value = null;
		} else {
			selectedMaterial.value = material.id;
		}
	};

	// 确认素材选择
	const confirmMaterialSelection = () => {
		if (!selectedMaterial.value) return;
		
		const material = materialList.value.find(m => m.id === selectedMaterial.value);
		if (material) {
			// 从file_path中提取第一个下划线之前的内容作为fileID
			const filePath = material.file_path;
			const fileId = filePath.split('_')[0].split('/').pop();
			console.log('选择的素材ID:', fileId);
			
			// 添加到file_list
			if (fileId && !file_list.value.includes(fileId)) {
				file_list.value.push(fileId);
			}
			
			// 添加到视频列表用于预览
			videoList.value.push({
				previewUrl: material.file_path,
				isFromLibrary: true
			});
		}
		
		hideMaterialLibrary();
	};

	// 判断是否为视频文件
	const isVideo = (filename) => {
		if (!filename) return false;
		const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'];
		return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext));
	};

	// 处理视频上传
	const handleVideoUpload = (event) => {
		const input = event.target;
		console.log('触发视频上传:', input);
		if (input.files && input.files.length > 0) {
			const file = input.files[0];
			console.log('上传的文件:', file);
			const previewUrl = URL.createObjectURL(file);
			console.log('预览URL:', previewUrl);
			videoList.value.push({ file, previewUrl });
			console.log('添加到视频列表:', videoList.value);

			// 清空input，允许再次选择相同文件
			if (videoInput.value) {
				videoInput.value.value = '';
			}
		}
	};

	// 删除视频
	const removeVideo = (index) => {
		if (videoList.value[index].previewUrl) {
			URL.revokeObjectURL(videoList.value[index].previewUrl);
		}
		videoList.value.splice(index, 1);
	};

	// 更新字符计数
	const updateCharCount = () => {
		charCount.value = title.value.length;
	};

	// 显示话题选择器
	const showTagSelector = () => {
		isTagSelectorVisible.value = true;
	};

	// 隐藏话题选择器
	const hideTagSelector = () => {
		isTagSelectorVisible.value = false;
		customTag.value = ''; // 清空自定义话题输入
	};

	// 点击话题选择器外部关闭
	const closeTagSelectorOnOutsideClick = (event) => {
		if (event.target.classList.contains('tag-selector-modal')) {
			hideTagSelector();
		}
	};

	// 添加预设话题
	const addSuggestedTag = (tag) => {
		if (!tags.value.includes(tag)) {
			tags.value.push(tag);
		}
	};

	// 添加自定义话题
	const addCustomTag = () => {
		if (customTag.value && !tags.value.includes(customTag.value)) {
			tags.value.push(customTag.value);
			customTag.value = ''; // 清空输入
		}
	};

	// 删除话题
	const removeTag = (index) => {
		tags.value.splice(index, 1);
	};

	// 显示账号选择器
	const showAccountSelector = () => {
		// 检查是否已选择平台
		if (!selectedPlatform.value) {
			alert('请先选择平台');
			return;
		}
		
		isAccountSelectorVisible.value = true;
		// 复制当前选中的账号到临时选中列表
		tempSelectedAccounts.value = [...selectedAccounts.value];
		fetchAccounts();
	};

	// 隐藏账号选择器
	const hideAccountSelector = () => {
		isAccountSelectorVisible.value = false;
		// 清空临时选中列表
		tempSelectedAccounts.value = [];
	};

	// 点击模态框外部关闭
	const closeModalOnOutsideClick = (event) => {
		if (event.target.classList.contains('account-selector-modal')) {
			hideAccountSelector();
		}
	};

	// 获取账号列表
	const fetchAccounts = async (forceRefresh = false) => {
		isAccountsLoading.value = true;
		
		// 检查全局缓存是否有效且不是强制刷新
		if (!forceRefresh && globalAccountsCache.isValid()) {
			console.log("使用缓存的账号列表数据");
			accountList.value = formatAccountData(globalAccountsCache.accounts);
			isAccountsLoading.value = false;
			return;
		}
		
		try {
			console.log("getValidAccounts请求前", `api/getValidAccounts`);
			const response = await axios.get(`api/getValidAccounts`);
			console.log("getValidAccounts",response.data.code);

			if (response.data.code === 200) {
				console.log("getValidAccounts",response.data.data);
				
				// 更新全局缓存
				globalAccountsCache.updateCache(response.data.data);
				
				// 格式化账号数据
				accountList.value = formatAccountData(response.data.data);
			}
		} catch (error) {
			console.error('获取账号列表失败:', error);
			accountList.value = [];
		} finally {
			isAccountsLoading.value = false;
		}
	};

	// 格式化账号数据
	const formatAccountData = (data) => {
		return data.map(account => ({
			id: account[0] || Math.random().toString(36).substr(2, 9),
			name: account[3] || '未命名账号',
			avatar: tx,
			status: account[4] === 1 ? '正常' : '异常',
			statusType: account[4] === 1 ? 'normal' : 'warning',
			userData: account,
			cookie: account[2] // 保存cookie路径
		}));
	};

	// 刷新账号列表
	const refreshAccounts = () => {
		fetchAccounts(true); // 强制刷新
	};

	// 选择账号
	const selectAccount = (account) => {
		const index = tempSelectedAccounts.value.findIndex(item => item.id === account.id);
		if (index === -1) {
			// 如果账号不在临时选中列表中，添加它
			tempSelectedAccounts.value.push(account);
		} else {
			// 如果账号已在临时选中列表中，移除它
			tempSelectedAccounts.value.splice(index, 1);
		}
	};

	// 确认账号选择
	const confirmAccountSelection = () => {
		// 将临时选中的账号列表应用到实际选中的账号列表
		selectedAccounts.value = [...tempSelectedAccounts.value];
		// 更新 account_list 用于 API 请求
		account_list.value = selectedAccounts.value.map(account => account.cookie);
		hideAccountSelector();
	};

	// 检查账号是否被选中
	const isAccountSelected = (account) => {
		return tempSelectedAccounts.value.some(item => item.id === account.id);
	};

	// 移除已选择的账号
	const removeAccount = (index) => {
		selectedAccounts.value.splice(index, 1);
		// 更新 account_list
		account_list.value = selectedAccounts.value.map(account => account.cookie);
	};

	// 选择平台
	const selectPlatform = (platformId) => {
		selectedPlatform.value = platformId;
	};

	// 添加时间槽
	const addTimeSlot = () => {
		if (dailyTimes.value.length < videosPerDay.value) {
			dailyTimes.value.push('12:00');
		}
	};

	// 移除时间槽
	const removeTimeSlot = (index) => {
		dailyTimes.value.splice(index, 1);
	};

	// 监听视频数量变化，调整时间槽
	watch(videosPerDay, (newValue, oldValue) => {
		if (newValue > oldValue) {
			// 增加时间槽
			for (let i = dailyTimes.value.length; i < newValue; i++) {
				dailyTimes.value.push('12:00');
			}
		} else if (newValue < oldValue) {
			// 减少时间槽
			dailyTimes.value = dailyTimes.value.slice(0, newValue);
		}
	});

	// 预览内容
	const previewContent = () => {
		if (videoList.value.length === 0) {
			alert('请上传视频');
			return;
		}

		// 这里可以实现预览逻辑
		alert('预览功能开发中...');
	};

	// 发布内容
	const publishContent = async () => {
		// 验证必填项
		if (videoList.value.length === 0) {
			alert('请上传视频');
			return;
		}

		if (!title.value) {
			alert('请输入标题');
			return;
		}

		if (selectedAccounts.value.length === 0) {
			alert('请选择至少一个账号');
			return;
		}

		if (!selectedPlatform.value) {
			alert('请选择发布平台');
			return;
		}

		// 设置上传状态
		isUploading.value = true;

		try {
			// 上传所有视频
			console.log('上传视频...');
			for (const videoItem of videoList.value) {
				// 创建FormData对象
				console.log('上传文件:', videoItem.file.name);
				const formData = new FormData();
				formData.append('file', videoItem.file);
				formData.append('filename', videoItem.file.name);
				
				for (let [key, value] of formData) {
					console.log(key, value);
				}
				
				try {
					const response = await axios.post('/api/upload', formData);
					console.log('上传成功，请手动刷新列表', response.data);
					
					// 检查请求是否成功
					if (response.data.code === 200) {
						// 提取fileID并保存
						if (response.data.data) {
							file_list.value.push(response.data.data);
							console.log('文件上传成功，fileID:', response.data.data);
							console.log('file_list:', file_list.value);
						} else {
							throw new Error('未获取到fileID');
						}
					} else {
						throw new Error(response.data.message || '上传失败');
					}
				} catch (err) {
					console.error('上传失败:', err.response?.data || err.message);
					throw new Error(err.response?.data?.message || err.message || '上传失败');
				}
			}

			// 准备发布数据

			const postData = {
				fileList: file_list.value,
				accountList: account_list.value,
				type: selectedPlatform.value,
				tags: tags.value,
				title: title.value,
				category: 0
			};

			// 如果启用定时发布，添加相关参数
			if (enableTimer.value) {
				postData.enableTimer = true;
				postData.videos_per_day = videosPerDay.value;
				postData.daily_times = dailyTimes.value.map(time => {
					const [hours, minutes] = time.split(':');
					return parseInt(hours) * 60 + parseInt(minutes); // 转换为分钟数
				});
				postData.start_days = startDays.value;
			} else {
				postData.enableTimer = false;
			}

			// 发送发布请求
			const publishResponse = await axios.post('/api/postVideo', postData);
			console.log('发布结果:', publishResponse.data);

			if (publishResponse.data.code === 200) {
				alert('发布成功！');
				// 重置表单
				resetForm();
			} else {
				throw new Error(publishResponse.data.message || '发布失败');
			}
		} catch (error) {
			console.error('发布视频失败:', error);
			alert(`发布失败: ${error instanceof Error ? error.message : '未知错误'}`);
		} finally {
			isUploading.value = false;
		}
	};

	// 重置表单
	const resetForm = () => {
		// 清理所有视频预览URL
		videoList.value.forEach(video => {
			if (video.previewUrl) {
				URL.revokeObjectURL(video.previewUrl);
			}
		});
		videoList.value = [];
		title.value = '';
		tags.value = [];
		location.value = '';
		file_list.value = [];
		selectedAccounts.value = [];
		account_list.value = [];
		selectedPlatform.value = null;
		enableTimer.value = false;
		videosPerDay.value = 1;
		dailyTimes.value = ['08:00'];
		startDays.value = 0;
	};

	// 组件卸载时清理资源
	onUnmounted(() => {
		// 清理所有视频预览URL
		videoList.value.forEach(video => {
			if (video.previewUrl) {
				URL.revokeObjectURL(video.previewUrl);
			}
		});
	});
</script>

<style scoped>
	.video-publish-container {
		max-width: 800px;
		margin: 0 auto;
		padding: 20px;
	}

	/* 通用部分样式 */
	.section {
		margin-bottom: 20px;
		border: 1px solid #eee;
		border-radius: 8px;
		padding: 15px;
		background-color: #fff;
	}

	.section-title {
		font-size: 16px;
		font-weight: bold;
		margin-bottom: 10px;
		color: #333;
	}

	/* 视频上传区域样式 - 更新 */
	.videos-container {
		display: flex;
		flex-wrap: wrap;
		gap: 15px;
	}

	.video-upload-area {
		border: 2px dashed #ddd;
		border-radius: 8px;
		width: 200px;
		height: 150px;
		display: flex;
		justify-content: center;
		align-items: center;
		cursor: pointer;
		background-color: #f9f9f9;
		transition: all 0.3s;
	}

	.video-upload-area:hover {
		border-color: #409eff;
		background-color: #f0f7ff;
	}

	.upload-icon {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.upload-icon .icon {
		font-size: 30px;
		color: #909399;
	}

	.upload-icon .text {
		margin-top: 10px;
		color: #606266;
	}

	.video-preview {
		position: relative;
		width: 200px;
		height: 150px;
		border-radius: 8px;
		overflow: hidden;
	}

	.video-preview video {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.video-actions {
		position: absolute;
		top: 10px;
		right: 10px;
		z-index: 10;
	}

	.remove-btn {
		background-color: rgba(0, 0, 0, 0.5);
		color: white;
		border: none;
		border-radius: 4px;
		padding: 5px 10px;
		cursor: pointer;
		font-size: 12px;
	}

	.remove-btn:hover {
		background-color: rgba(0, 0, 0, 0.7);
	}

	.video-count {
		margin-top: 10px;
		font-size: 14px;
		color: #909399;
	}

	/* 账号选择区域样式 */
	.account-selector {
		border: 1px dashed #ddd;
		border-radius: 8px;
		padding: 10px;
		cursor: pointer;
		min-height: 50px;
		background-color: #f9f9f9;
		transition: all 0.3s;
	}

	.account-selector:hover {
		border-color: #409eff;
		background-color: #f0f7ff;
	}

	.account-placeholder {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 30px;
		color: #909399;
	}

	.selected-accounts-container {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.selected-account {
		display: flex;
		align-items: center;
		background-color: #f0f7ff;
		border: 1px solid #d9ecff;
		border-radius: 4px;
		padding: 5px 10px;
		position: relative;
	}

	.account-avatar {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		margin-right: 8px;
		object-fit: cover;
	}

	.account-name {
		font-size: 14px;
		color: #333;
		margin-right: 8px;
	}

	.account-status {
		font-size: 12px;
		padding: 2px 6px;
		border-radius: 10px;
	}

	.account-status.normal {
		background-color: #f0f9eb;
		color: #67c23a;
	}

	.account-status.warning {
		background-color: #fdf6ec;
		color: #e6a23c;
	}

	.remove-account-btn {
		background: none;
		border: none;
		color: #909399;
		cursor: pointer;
		font-size: 16px;
		margin-left: 5px;
		padding: 0 5px;
	}

	.remove-account-btn:hover {
		color: #f56c6c;
	}

	.add-more-account {
		display: flex;
		align-items: center;
		color: #409eff;
		font-size: 14px;
		cursor: pointer;
		padding: 5px 10px;
	}

	/* 账号选择弹窗样式 */
	.account-selector-modal {
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

	.account-selector-content {
		width: 90%;
		max-width: 500px;
		background-color: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 15px;
		border-bottom: 1px solid #eee;
	}

	.modal-header h3 {
		margin: 0;
		font-size: 18px;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 24px;
		cursor: pointer;
		color: #666;
	}

	.refresh-btn {
		background: none;
		border: none;
		font-size: 18px;
		cursor: pointer;
		color: #666;
		margin-left: auto;
		margin-right: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.refresh-icon {
		display: inline-block;
		transition: transform 0.3s ease;
	}

	.refresh-btn:hover .refresh-icon {
		transform: rotate(180deg);
		color: #409eff;
	}

	.close-btn:hover {
		color: #f56c6c;
	}

	.modal-body {
		padding: 20px;
		max-height: 400px;
		overflow-y: auto;
	}

	.loading-accounts,
	.no-accounts {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100px;
		color: #909399;
	}

	.account-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.account-item {
		display: flex;
		align-items: center;
		padding: 10px;
		border-radius: 4px;
		cursor: pointer;
		transition: background-color 0.3s;
	}

	.account-item:hover {
		background-color: #f5f7fa;
	}

	.account-item.selected {
		background-color: #f0f7ff;
	}

	.account-checkbox {
		margin-right: 10px;
	}

	.checkbox {
		width: 18px;
		height: 18px;
		border: 2px solid #dcdfe6;
		border-radius: 2px;
		position: relative;
	}

	.checkbox.checked {
		background-color: #409eff;
		border-color: #409eff;
	}

	.checkbox.checked::after {
		content: '';
		position: absolute;
		top: 3px;
		left: 6px;
		width: 3px;
		height: 7px;
		border: solid white;
		border-width: 0 2px 2px 0;
		transform: rotate(45deg);
	}

	.account-info {
		flex: 1;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		padding: 15px 20px;
		border-top: 1px solid #eee;
		gap: 10px;
	}

	.cancel-btn,
	.confirm-btn {
		padding: 8px 20px;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
	}

	.cancel-btn {
		background-color: #f5f7fa;
		border: 1px solid #dcdfe6;
		color: #606266;
	}

	.confirm-btn {
		background-color: #409eff;
		border: 1px solid #409eff;
		color: white;
	}

	.cancel-btn:hover {
		background-color: #e9ebef;
	}

	.confirm-btn:hover {
		background-color: #66b1ff;
	}

	/* 平台选择区域样式 */
	.platform-selector {
		display: flex;
		gap: 10px;
	}

	.platform-btn {
		flex: 1;
		padding: 10px 15px;
		border: 1px solid #dcdfe6;
		border-radius: 4px;
		background-color: white;
		color: #606266;
		cursor: pointer;
		font-size: 14px;
		transition: all 0.3s;
	}

	.platform-btn:hover {
		border-color: #c6e2ff;
		color: #409eff;
	}

	.platform-btn.active {
		background-color: #409eff;
		border-color: #409eff;
		color: white;
	}

	/* 标题输入区域样式 */
	.title-input-container {
		position: relative;
	}

	textarea {
		width: 100%;
		padding: 10px;
		border: 1px solid #dcdfe6;
		border-radius: 4px;
		font-size: 14px;
		resize: none;
	}

	.char-count {
		position: absolute;
		bottom: 5px;
		right: 10px;
		font-size: 12px;
		color: #909399;
	}

	/* 话题选择区域样式 */
	.tags-container {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.tag {
		display: flex;
		align-items: center;
		background-color: #f0f7ff;
		border: 1px solid #d9ecff;
		border-radius: 4px;
		padding: 5px 10px;
		font-size: 14px;
		color: #409eff;
	}

	.remove-tag {
		margin-left: 5px;
		cursor: pointer;
		color: #909399;
	}

	.remove-tag:hover {
		color: #f56c6c;
	}

	.add-tag {
		display: flex;
		align-items: center;
		color: #409eff;
		border: 1px dashed #d9ecff;
		border-radius: 4px;
		padding: 5px 10px;
		cursor: pointer;
		font-size: 14px;
	}

	.add-tag:hover {
		background-color: #f0f7ff;
	}

	/* 话题选择弹窗样式 */
	.tag-selector-modal {
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

	.tag-selector-content {
		width: 90%;
		max-width: 500px;
		background-color: white;
		border-radius: 8px;
		overflow: hidden;
		box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
	}

	.custom-tag-input {
		display: flex;
		margin-bottom: 15px;
	}

	.custom-tag-input input {
		flex: 1;
		padding: 8px 10px;
		border: 1px solid #dcdfe6;
		border-radius: 4px 0 0 4px;
		font-size: 14px;
	}

	.custom-tag-input button {
		padding: 8px 15px;
		background-color: #409eff;
		border: 1px solid #409eff;
		border-radius: 0 4px 4px 0;
		color: white;
		cursor: pointer;
		font-size: 14px;
	}

	.suggested-tags h4 {
		margin-top: 0;
		margin-bottom: 10px;
		font-size: 16px;
		color: #333;
	}

	.tag-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
		gap: 10px;
	}

	.suggested-tag {
		background-color: #f5f7fa;
		border: 1px solid #e4e7ed;
		border-radius: 4px;
		padding: 8px 12px;
		font-size: 14px;
		color: #606266;
		cursor: pointer;
		text-align: center;
		transition: all 0.3s;
	}

	.suggested-tag:hover {
		background-color: #f0f7ff;
		border-color: #d9ecff;
		color: #409eff;
	}

	/* 位置输入区域样式 */
	.location-input-container input {
		width: 100%;
		padding: 10px;
		border: 1px solid #dcdfe6;
		border-radius: 4px;
		font-size: 14px;
	}

	/* 定时发布设置区域样式 */
	.timer-toggle {
		display: flex;
		align-items: center;
		margin-bottom: 15px;
	}

	.switch {
		position: relative;
		display: inline-block;
		width: 40px;
		height: 20px;
		margin-right: 10px;
	}

	.switch input {
		opacity: 0;
		width: 0;
		height: 0;
	}

	.slider {
		position: absolute;
		cursor: pointer;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: #dcdfe6;
		transition: .4s;
	}

	.slider:before {
		position: absolute;
		content: "";
		height: 16px;
		width: 16px;
		left: 2px;
		bottom: 2px;
		background-color: white;
		transition: .4s;
	}

	input:checked+.slider {
		background-color: #409eff;
	}

	input:checked+.slider:before {
		transform: translateX(20px);
	}

	.slider.round {
		border-radius: 20px;
	}

	.slider.round:before {
		border-radius: 50%;
	}

	.timer-settings {
		background-color: #f5f7fa;
		border-radius: 4px;
		padding: 15px;
	}

	.setting-item {
		margin-bottom: 15px;
	}

	.setting-item:last-child {
		margin-bottom: 0;
	}

	.setting-item label {
		display: block;
		margin-bottom: 5px;
		font-size: 14px;
		color: #606266;
	}

	.setting-item select {
		width: 100%;
		padding: 8px 10px;
		border: 1px solid #dcdfe6;
		border-radius: 4px;
		font-size: 14px;
		background-color: white;
	}

	.time-slots {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.time-slot {
		display: flex;
		align-items: center;
	}

	.time-slot input {
		flex: 1;
		padding: 8px 10px;
		border: 1px solid #dcdfe6;
		border-radius: 4px;
		font-size: 14px;
	}

	.remove-time-btn {
		background: none;
		border: none;
		color: #909399;
		cursor: pointer;
		font-size: 16px;
		margin-left: 10px;
	}

	.remove-time-btn:hover {
		color: #f56c6c;
	}

	.add-time-btn {
		background-color: #f5f7fa;
		border: 1px dashed #dcdfe6;
		border-radius: 4px;
		padding: 8px 0;
		color: #409eff;
		cursor: pointer;
		font-size: 14px;
		text-align: center;
		width: 100%;
	}

	.add-time-btn:hover {
		background-color: #f0f7ff;
		border-color: #c6e2ff;
	}

	/* 操作按钮区域样式 */
	.action-buttons {
		display: flex;
		justify-content: flex-end;
		gap: 15px;
		margin-top: 20px;
	}

	.preview-btn,
	.publish-btn {
		padding: 10px 20px;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
		border: none;
	}

	.preview-btn {
		background-color: #f5f7fa;
		color: #606266;
	}

	.publish-btn {
		background-color: #409eff;
		color: white;
	}

	.preview-btn:hover {
		background-color: #e9ebef;
	}

	.publish-btn:hover {
		background-color: #66b1ff;
	}

	.preview-btn:disabled,
	.publish-btn:disabled {
		background-color: #f5f7fa;
		color: #c0c4cc;
		cursor: not-allowed;
	}

	/* 视频来源选择器样式 */
	.source-selector {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.5);
	z-index: 1000;
	display: flex;
	justify-content: center;
	align-items: center;
	}
	
	.source-selector-content {
	background-color: white;
	border-radius: 8px;
	padding: 15px;
	width: 200px;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
	}
	
	.source-option {
	padding: 12px 15px;
	cursor: pointer;
	border-radius: 4px;
	transition: background-color 0.2s;
	}
	
	.source-option:hover {
	background-color: #f5f5f5;
	}
	
	/* 素材库弹窗样式 */
	.material-library-modal {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background-color: rgba(0, 0, 0, 0.5);
	z-index: 1000;
	display: flex;
	justify-content: center;
	align-items: center;
	}
	
	.material-library-content {
	background-color: white;
	border-radius: 8px;
	width: 80%;
	max-width: 900px;
	max-height: 80vh;
	overflow: hidden;
	display: flex;
	flex-direction: column;
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
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
	color: #666;
	}
	
	.modal-body {
	padding: 20px;
	overflow-y: auto;
	flex: 1;
	}
	
	.loading-materials,
	.no-materials {
	display: flex;
	justify-content: center;
	align-items: center;
	height: 200px;
	color: #666;
	}
	
	.material-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
	gap: 15px;
	}
	
	.material-item {
	border: 1px solid #eee;
	border-radius: 8px;
	overflow: hidden;
	cursor: pointer;
	transition: transform 0.2s, box-shadow 0.2s;
	position: relative;
	}
	
	.material-item:hover {
	transform: translateY(-3px);
	box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	}
	
	.material-item.selected {
	border-color: #1890ff;
	box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
	}
	
	.material-checkbox {
	position: absolute;
	top: 10px;
	right: 10px;
	z-index: 1;
	}
	
	.checkbox {
	width: 18px;
	height: 18px;
	border: 2px solid #fff;
	border-radius: 50%;
	background-color: rgba(0, 0, 0, 0.3);
	}
	
	.checkbox.checked {
	background-color: #1890ff;
	border-color: #fff;
	}
	
	.material-preview {
	height: 120px;
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
	
	.material-info {
	padding: 10px;
	}
	
	.material-name {
	font-size: 14px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	}
	
	.modal-footer {
	display: flex;
	justify-content: flex-end;
	padding: 15px 20px;
	border-top: 1px solid #eee;
	gap: 10px;
	}
	
	.cancel-btn {
	padding: 8px 15px;
	background-color: white;
	border: 1px solid #ddd;
	border-radius: 4px;
	cursor: pointer;
	}
	
	.confirm-btn {
	padding: 8px 15px;
	background-color: #1890ff;
	color: white;
	border: none;
	border-radius: 4px;
	cursor: pointer;
	}
	
	.confirm-btn:disabled {
	background-color: #ccc;
	cursor: not-allowed;
	}
</style>