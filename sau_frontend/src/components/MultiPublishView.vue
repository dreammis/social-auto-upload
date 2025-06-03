<template>
	<div class="multi-publish-container">
		<h1>多平台发布</h1>

		<!-- 添加发布按钮 -->
		<div class="action-bar">
			<button class="add-publish-btn" @click="showPlatformModal">
				<i class="add-icon">+</i> 添加发布
			</button>
		</div>

		<!-- 平台选择弹窗 -->
		<div class="platform-modal" v-if="isPlatformModalVisible" @click="closeModalOnOutsideClick">
			<div class="platform-modal-content">
				<div class="modal-header">
					<h3>选择平台</h3>
					<button class="close-btn" @click="hidePlatformModal">×</button>
				</div>
				<div class="modal-body">
					<div class="platform-options">
						<div class="platform-option" :class="{ 'selected': selectedPlatform === 3 }"
							@click="selectPlatform(3)">
							<div class="platform-icon douyin-icon"></div>
							<span>抖音</span>
						</div>
						<div class="platform-option" :class="{ 'selected': selectedPlatform === 4 }"
							@click="selectPlatform(4)">
							<div class="platform-icon kuaishou-icon"></div>
							<span>快手</span>
						</div>
						<div class="platform-option" :class="{ 'selected': selectedPlatform === 1 }"
							@click="selectPlatform(1)">
							<div class="platform-icon xiaohongshu-icon"></div>
							<span>小红书</span>
						</div>
						<div class="platform-option" :class="{ 'selected': selectedPlatform === 2 }"
							@click="selectPlatform(2)">
							<div class="platform-icon shipinhao-icon"></div>
							<span>视频号</span>
						</div>
					</div>
				</div>
				<div class="modal-footer">
					<button class="cancel-btn" @click="hidePlatformModal">取消</button>
					<button class="confirm-btn" @click="confirmPlatformSelection">确认</button>
				</div>
			</div>
		</div>

		<!-- 发布卡片容器 -->
		<div class="publish-cards-container">
			<!-- 滚动控制按钮 -->
			<button v-if="publishCards.length > 2" class="scroll-btn scroll-left" @click="scrollLeft">
				<span>&lt;</span>
			</button>

			<!-- 卡片滚动区域 -->
			<div class="cards-scroll-area" ref="cardsContainer">
				<div v-if="publishCards.length === 0" class="empty-state">
					<p>暂无发布卡片，点击"添加发布"创建新卡片</p>
				</div>

				<div v-for="(card, index) in publishCards" :key="card.id" class="publish-card">
					<!-- 卡片头部 -->
					<div class="card-header">
						<div class="platform-info">
							<div :class="['platform-icon', getPlatformIconClass(card.platform)]"></div>
							<span>{{ getPlatformName(card.platform) }}</span>
						</div>
						<div class="card-actions">
							<button class="delete-card-btn" @click="deleteCard(index)">删除</button>
						</div>
					</div>

					<!-- 卡片内容 -->
					<div class="card-content">
						<!-- 账号选择 -->
						<div class="card-section">
							<div class="section-title">账号</div>
							<div class="account-selector" @click="showAccountSelector(index)">
								<div v-if="!card.selectedAccount" class="account-placeholder">
									<span>+ 选择账号</span>
								</div>
								<div v-else class="selected-account">
									<img :src="card.selectedAccount.avatar" alt="账号头像" class="account-avatar" />
									<span class="account-name">{{ card.selectedAccount.name }}</span>
									<span class="account-status"
										:class="card.selectedAccount.statusType">{{ card.selectedAccount.status }}</span>
								</div>
							</div>
						</div>

						<!-- 发布类型选择 -->
						<div class="card-section">
							<div class="section-title">发布类型</div>
							<div class="publish-type-selector">
								<button class="type-btn" :class="{ 'active': card.publishType === 'video' }"
									@click="setPublishType(index, 'video')">
									视频
								</button>
								<button class="type-btn" :class="{ 'active': card.publishType === 'image' }"
									@click="setPublishType(index, 'image')">
									图文
								</button>
							</div>
						</div>

						<!-- 媒体上传区域 -->
						<div class="card-section media-section">
							<div class="section-title">{{ card.publishType === 'video' ? '视频' : '图片' }}</div>
							<div class="media-upload-container">
								<!-- 视频上传区域 -->
								<div v-if="card.publishType === 'video'" class="videos-container">
									<div class="video-upload-area" @click="triggerMediaUpload(index)"
										v-if="card.mediaList.length < 5">
										<div class="upload-icon">
											<span class="icon">↑</span>
											<span class="text">上传</span>
										</div>
									</div>
									<div v-for="(media, mediaIndex) in card.mediaList" :key="mediaIndex"
										class="video-preview media-item">
										<video controls :src="media.previewUrl"></video>
										<div class="media-actions">
											<button class="remove-btn"
												@click.stop="removeMedia(index, mediaIndex)">删除</button>
										</div>
									</div>
								</div>

								<!-- 图片上传区域 -->
								<div v-else class="images-container">
									<div class="image-upload-area" @click="triggerMediaUpload(index)"
										v-if="card.mediaList.length < 9">
										<div class="upload-icon">
											<span class="icon">↑</span>
											<span class="text">上传</span>
										</div>
									</div>
									<div v-for="(media, mediaIndex) in card.mediaList" :key="mediaIndex"
										class="image-preview">
										<img :src="media.previewUrl" alt="预览图片" />
										<div class="media-actions">
											<button class="remove-btn"
												@click.stop="removeMedia(index, mediaIndex)">删除</button>
										</div>
									</div>
								</div>
							</div>
							<div class="media-count" v-if="card.mediaList.length > 0">
								已上传 {{ card.mediaList.length }} 个{{ card.publishType === 'video' ? '视频' : '图片' }}
								(最多{{ card.publishType === 'video' ? '5' : '9' }}个)
							</div>
						</div>

						<!-- 标题输入区域 -->
						<div class="card-section">
							<div class="section-title">标题</div>
							<div class="title-input-container">
								<textarea v-model="card.title" @input="updateCharCount(index)" placeholder="请输入标题"
									maxlength="100" rows="2"></textarea>
								<div class="char-count">{{ card.charCount }}/100</div>
							</div>
						</div>

						<!-- 话题选择区域 -->
						<div class="card-section">
							<div class="section-title">话题</div>
							<div class="tags-container">
								<div v-for="(tag, tagIndex) in card.tags" :key="tagIndex" class="tag">
									{{ tag }}
									<span class="remove-tag" @click="removeTag(index, tagIndex)">×</span>
								</div>
								<div class="add-tag" @click="showTagSelector(index)">+ 添加话题</div>
							</div>
						</div>

						<!-- 定时发布设置 -->
						<div class="card-section">
							<div class="section-title">
								<div class="timer-toggle">
									<label class="switch">
										<input type="checkbox" v-model="card.enableTimer" @change="toggleTimer(index)">
										<span class="slider round"></span>
									</label>
									<span class="toggle-label">定时发布</span>
								</div>
							</div>
							<div v-if="card.enableTimer" class="timer-settings">
								<div class="setting-item">
									<label class="setting-label">每天发布视频数</label>
									<select v-model="card.videosPerDay" @change="updateDailyTimes(index)" class="setting-select">
										<option value="1">1个</option>
										<option value="2">2个</option>
										<option value="3">3个</option>
										<option value="4">4个</option>
										<option value="5">5个</option>
									</select>
								</div>
								<div class="setting-item">
									<label class="setting-label">每天发布时间</label>
									<div class="time-slots">
										<input v-for="(time, timeIndex) in card.dailyTimes" :key="timeIndex" type="time"
											v-model="card.dailyTimes[timeIndex]" class="time-input">
									</div>
								</div>
								<div class="setting-item">
									<label class="setting-label">开始天数</label>
									<div class="days-setting">
										<input type="number" v-model="card.startDays" min="1" max="30" class="days-input">
										<span class="days-unit">天后开始</span>
									</div>
								</div>
							</div>
						</div>

						<!-- 发布按钮 -->
						<div class="card-actions-bottom">
							<button class="publish-btn" @click="publishContent(index)"
								:disabled="!isCardValid(card) || card.isUploading">
								{{ card.isUploading ? '上传中...' : '发布' }}
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- 滚动控制按钮 -->
			<button v-if="publishCards.length > 2" class="scroll-btn scroll-right" @click="scrollRight">
				<span>&gt;</span>
			</button>
		</div>

		<!-- 账号选择弹窗 -->
		<div class="account-selector-modal" v-if="isAccountSelectorVisible" @click="closeAccountModalOnOutsideClick">
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
					<div v-else-if="filteredAccountList.length === 0" class="no-accounts">
						<span>暂无可用账号</span>
					</div>
					<div v-else class="account-list">
						<div v-for="account in filteredAccountList" :key="account.id" class="account-item"
							@click="selectAccount(account)">
							<img :src="account.avatar" alt="账号头像" class="account-avatar" />
							<div class="account-info">
								<div class="account-name">{{ account.name }}</div>
								<div class="account-status" :class="account.statusType">{{ account.status }}</div>
							</div>
						</div>
					</div>
				</div>
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

		<!-- 视频来源选择器 -->
		<div class="source-selector" v-if="isSourceSelectorVisible" @click="hideSourceSelector">
			<div class="source-selector-content" @click.stop>
				<div class="source-option" @click="selectLocalSource">
					<div class="source-icon local-icon">
						<i class="icon-upload">📁</i>
					</div>
					<span class="source-text">本地视频</span>
				</div>
				<div class="source-option" @click="showMaterialLibrary">
					<div class="source-icon library-icon">
						<i class="icon-library">🎬</i>
					</div>
					<span class="source-text">素材库</span>
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
								<button class="delete-btn" @click.stop="deleteMaterial(material)" title="删除素材">×</button>
							</div>
							<div class="material-info">
								<div class="material-name">{{ material.filename }}</div>
								<div class="material-meta">
									<span>{{ formatFileSize(material.filesize) }}</span>
									<span>{{ formatDate(material.upload_time) }}</span>
								</div>
							</div>
						</div>
					</div>
				</div>
				<div class="modal-footer">
					<button class="cancel-btn" @click="hideMaterialLibrary">取消</button>
					<button class="confirm-btn" @click="confirmMaterialSelection"
						:disabled="!selectedMaterial">确认</button>
				</div>
			</div>
		</div>

		<!-- 隐藏的文件输入 -->
		<input type="file" ref="mediaInput" style="display: none" @change="handleMediaUpload" />
	</div>
</template>

<script setup>
	import {
		ref,
		computed,
		onMounted,
		onUnmounted,
		watch
	} from 'vue';
	import {
		globalAccountsCache
	} from '../config';
	import axios from 'axios';
	import tx from '@assets/fengbaobao.png'

	// 推荐话题列表
	const suggestedTags = ['游戏', '电影', '音乐', '美食', '旅行', '文化', '科技', '生活', '娱乐', '体育', '教育', '艺术', '健康', '时尚'];

	// 平台弹窗状态
	const isPlatformModalVisible = ref(false);
	const selectedPlatform = ref(null);

	// 账号选择状态
	const isAccountSelectorVisible = ref(false);
	const isAccountsLoading = ref(false);
	const accountList = ref([]);
	const currentCardIndex = ref(-1);

	// 话题选择状态
	const isTagSelectorVisible = ref(false);
	const customTag = ref('');

	// 媒体上传
	const mediaInput = ref(null);
	const currentUploadCardIndex = ref(-1);

	// 卡片容器引用
	const cardsContainer = ref(null);

	// 发布卡片列表
	const publishCards = ref([]);

	// 显示平台选择弹窗
	const showPlatformModal = () => {
		isPlatformModalVisible.value = true;
		selectedPlatform.value = null;
	};

	// 隐藏平台选择弹窗
	const hidePlatformModal = () => {
		isPlatformModalVisible.value = false;
	};

	// 点击弹窗外部关闭
	const closeModalOnOutsideClick = (event) => {
		if (event.target.classList.contains('platform-modal')) {
			hidePlatformModal();
		}
	};

	// 选择平台
	const selectPlatform = (platformId) => {
		selectedPlatform.value = platformId;
	};

	// 确认平台选择并创建卡片
	const confirmPlatformSelection = () => {
		if (selectedPlatform.value) {
			// 创建新的发布卡片
			const newCard = {
				id: Date.now().toString(),
				platform: selectedPlatform.value,
				selectedAccount: null,
				publishType: 'video', // 默认为视频类型
				mediaList: [],
				title: '',
				charCount: 0,
				tags: [],
				isUploading: false,
				file_list: [], // 保存上传后的fileID
				// 定时发布相关属性
				enableTimer: false,
				videosPerDay: 1,
				dailyTimes: ['09:00'],
				startDays: 1
			};

			publishCards.value.push(newCard);
			hidePlatformModal();
		} else {
			alert('请选择一个平台');
		}
	};

	// 删除卡片
	const deleteCard = (index) => {
		// 清理媒体资源
		publishCards.value[index].mediaList.forEach(media => {
			if (media.previewUrl) {
				URL.revokeObjectURL(media.previewUrl);
			}
		});

		// 移除卡片
		publishCards.value.splice(index, 1);
	};

	// 获取平台名称
	const getPlatformName = (platformId) => {
		switch (platformId) {
			case 3:
				return '抖音';
			case 4:
				return '快手';
			case 1:
				return '小红书';
			case 2:
				return '视频号';
			default:
				return '未知平台';
		}
	};

	// 获取平台图标类名
	const getPlatformIconClass = (platformId) => {
		switch (platformId) {
			case 3:
				return 'douyin-icon';
			case 4:
				return 'kuaishou-icon';
			case 1:
				return 'xiaohongshu-icon';
			case 2:
				return 'shipinhao-icon';
			default:
				return '';
		}
	};

	// 设置发布类型
	const setPublishType = (cardIndex, type) => {
		const card = publishCards.value[cardIndex];

		// 如果类型不同，清空已上传的媒体
		if (card.publishType !== type) {
			// 清理媒体资源
			card.mediaList.forEach(media => {
				if (media.previewUrl) {
					URL.revokeObjectURL(media.previewUrl);
				}
			});

			card.mediaList = [];
			card.file_list = [];
		}

		card.publishType = type;
	};

	// 视频来源选择器相关
	const isSourceSelectorVisible = ref(false); // 视频来源选择器是否可见
	const currentSourceCardIndex = ref(-1); // 当前操作的卡片索引

	// 素材库选择相关
	const isMaterialLibraryVisible = ref(false); // 素材库选择器是否可见
	const isLoadingMaterials = ref(false); // 素材加载状态
	const materialList = ref([]); // 素材列表
	const selectedMaterial = ref(null); // 选中的素材ID

	// 触发媒体上传
	const triggerMediaUpload = (cardIndex) => {
		currentUploadCardIndex.value = cardIndex;

		// 设置接受的文件类型
		const card = publishCards.value[cardIndex];
		if (card.publishType === 'video') {
			// 显示视频来源选择器
			currentSourceCardIndex.value = cardIndex;
			isSourceSelectorVisible.value = true;
		} else {
			// 图片直接触发上传
			mediaInput.value.accept = 'image/*';
			mediaInput.value?.click();
		}
	};

	// 隐藏视频来源选择器
	const hideSourceSelector = () => {
		isSourceSelectorVisible.value = false;
	};

	// 选择本地视频源
	const selectLocalSource = () => {
		hideSourceSelector();
		mediaInput.value.accept = 'video/*';
		mediaInput.value?.click();
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
							params: {
								filename: filename
							},
							responseType: 'blob'
						});

						console.log(`获取素材 ${filename} 数据:`, fileResponse.data);

						// 创建URL
						const blob = new Blob([fileResponse.data]);
						const url = URL.createObjectURL(blob);

						// 将获取的视频数据合并到素材对象中
						return {
							...item,
							videoData: {
								...fileResponse.data,
								url: url
							}
						};
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
			const cardIndex = currentSourceCardIndex.value;
			const card = publishCards.value[cardIndex];

			// 从file_path中提取第一个下划线之前的内容作为fileID
			const filePath = material.file_path;
			const fileId = filePath.split('_')[0].split('/').pop();
			console.log('选择的素材ID:', fileId);

			// 添加到file_list
			if (fileId && !card.file_list.includes(fileId)) {
				card.file_list.push(fileId);
			}

			// 构建预览URL
			const previewUrl = material.videoData && material.videoData.url ? material.videoData.url : material
				.file_path;

			// 添加到媒体列表用于预览
			card.mediaList.push({
				previewUrl: previewUrl,
				isFromLibrary: true,
				videoData: material.videoData
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

	// 处理媒体上传
	const handleMediaUpload = (event) => {
		const input = event.target;
		const cardIndex = currentUploadCardIndex.value;

		if (cardIndex === -1 || !input.files || input.files.length === 0) return;

		const card = publishCards.value[cardIndex];
		const file = input.files[0];
		const previewUrl = URL.createObjectURL(file);

		// 添加到媒体列表
		card.mediaList.push({
			file,
			previewUrl
		});

		// 清空input，允许再次选择相同文件
		if (mediaInput.value) {
			mediaInput.value.value = '';
		}
	};

	// 移除媒体
	const removeMedia = (cardIndex, mediaIndex) => {
		const card = publishCards.value[cardIndex];

		// 释放预览URL
		if (card.mediaList[mediaIndex].previewUrl) {
			URL.revokeObjectURL(card.mediaList[mediaIndex].previewUrl);
		}

		// 移除媒体
		card.mediaList.splice(mediaIndex, 1);
	};

	// 更新字符计数
	const updateCharCount = (cardIndex) => {
		const card = publishCards.value[cardIndex];
		card.charCount = card.title.length;
	};

	// 切换定时发布
	const toggleTimer = (cardIndex) => {
		const card = publishCards.value[cardIndex];
		if (!card.enableTimer) {
			// 重置定时设置
			card.videosPerDay = 1;
			card.dailyTimes = ['09:00'];
			card.startDays = 1;
		}
	};

	// 更新每日发布时间数组
	const updateDailyTimes = (cardIndex) => {
		const card = publishCards.value[cardIndex];
		const count = parseInt(card.videosPerDay);

		// 调整时间数组长度
		if (card.dailyTimes.length < count) {
			// 添加新的时间槽
			while (card.dailyTimes.length < count) {
				card.dailyTimes.push('09:00');
			}
		} else if (card.dailyTimes.length > count) {
			// 移除多余的时间槽
			card.dailyTimes.splice(count);
		}
	};

	// 显示账号选择器
	const showAccountSelector = (cardIndex) => {
		currentCardIndex.value = cardIndex;
		isAccountSelectorVisible.value = true;
		fetchAccounts();
	};

	// 隐藏账号选择器
	const hideAccountSelector = () => {
		isAccountSelectorVisible.value = false;
		currentCardIndex.value = -1;
	};

	// 点击账号选择器外部关闭
	const closeAccountModalOnOutsideClick = (event) => {
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
			const response = await axios.get(`/api/getValidAccounts`);

			if (response.data.code === 200) {
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
			type: account[1],
			cookie: account[2] // 保存cookie路径
		}));
	};

	// 根据当前选中的卡片平台过滤账号列表
	const filteredAccountList = computed(() => {
		if (currentCardIndex.value === -1) return [];

		const platformId = publishCards.value[currentCardIndex.value].platform;
		return accountList.value.filter(account => account.type === platformId);
	});

	// 刷新账号列表
	const refreshAccounts = () => {
		fetchAccounts(true); // 强制刷新
	};

	// 选择账号
	const selectAccount = (account) => {
		if (currentCardIndex.value !== -1) {
			publishCards.value[currentCardIndex.value].selectedAccount = account;
		}
		hideAccountSelector();
	};

	// 显示话题选择器
	const showTagSelector = (cardIndex) => {
		currentCardIndex.value = cardIndex;
		isTagSelectorVisible.value = true;
	};

	// 隐藏话题选择器
	const hideTagSelector = () => {
		isTagSelectorVisible.value = false;
		customTag.value = ''; // 清空自定义话题输入
		currentCardIndex.value = -1;
	};

	// 点击话题选择器外部关闭
	const closeTagSelectorOnOutsideClick = (event) => {
		if (event.target.classList.contains('tag-selector-modal')) {
			hideTagSelector();
		}
	};

	// 添加预设话题
	const addSuggestedTag = (tag) => {
		if (currentCardIndex.value !== -1) {
			const card = publishCards.value[currentCardIndex.value];
			if (!card.tags.includes(tag)) {
				card.tags.push(tag);
			}
		}
	};

	// 添加自定义话题
	const addCustomTag = () => {
		if (currentCardIndex.value !== -1 && customTag.value) {
			const card = publishCards.value[currentCardIndex.value];
			if (!card.tags.includes(customTag.value)) {
				card.tags.push(customTag.value);
				customTag.value = ''; // 清空输入
			}
		}
	};

	// 删除话题
	const removeTag = (cardIndex, tagIndex) => {
		publishCards.value[cardIndex].tags.splice(tagIndex, 1);
	};

	// 检查卡片是否有效（可发布）
	const isCardValid = (card) => {
		return card.mediaList.length > 0 &&
			card.title &&
			card.selectedAccount !== null;
	};

	// 发布内容
	const publishContent = async (cardIndex) => {
		const card = publishCards.value[cardIndex];
    console.log('开始发布内容:', card);
    // console.log('账号信息:', publishCards.value);

		// 验证必填项
		if (card.mediaList.length === 0) {
			alert(`请上传${card.publishType === 'video' ? '视频' : '图片'}`);
			return;
		}

		if (!card.title) {
			alert('请输入标题');
			return;
		}

		if (!card.selectedAccount) {
			alert('请选择账号');
			return;
		}

		// 设置上传状态
		card.isUploading = true;

		try {
			// 上传所有媒体文件
			for (const mediaItem of card.mediaList) {
				// 创建FormData对象
				const formData = new FormData();
				formData.append('file', mediaItem.file);
				formData.append('filename', mediaItem.file.name);

				try {
					const response = await axios.post('/api/upload', formData);
					console.log('上传响应:', response.data);

					// 检查请求是否成功
					if (response.data.code === 200) {
						// 提取fileID并保存
						if (response.data.data) {
							card.file_list.push(response.data.data);
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
				fileList: card.file_list,
				accountList: [card.selectedAccount.cookie],
				type: card.platform,
				tags: card.tags,
				title: card.title,
				category: 0
			};
			
			// 如果启用定时发布，添加相关参数
			if (card.enableTimer.value) {
				postData.enableTimer = true;
				postData.videos_per_day = card.videosPerDay.value;
				postData.daily_times = card.dailyTimes.value.map(time => {
					const [hours, minutes] = time.split(':');
					return parseInt(hours) * 60 + parseInt(minutes); // 转换为分钟数
				});
				postData.start_days = card.startDays.value;
			} else {
				postData.enableTimer = false;
			}

			// 发送发布请求
			// 发送发布请求
			const publishResponse = await axios.post('/api/postVideo', postData);
			console.log('发布结果:', publishResponse.data);
			// const apiEndpoint = card.publishType === 'video' ? '/api/postVideo' : '/api/postImage';
			// const publishResponse = await axios.post(apiEndpoint, postData);

			if (publishResponse.data.code === 200) {
				alert('发布成功！');
				// 删除已发布的卡片
				deleteCard(cardIndex);
			} else {
				throw new Error(publishResponse.data.message || '发布失败');
			}
		} catch (error) {
			console.error(`发布${card.publishType === 'video' ? '视频' : '图文'}失败:`, error);
			alert(`发布失败: ${error instanceof Error ? error.message : '未知错误'}`);
			card.isUploading = false;
		}
	};

	// 滚动卡片容器
	const scrollLeft = () => {
		if (cardsContainer.value) {
			cardsContainer.value.scrollBy({
				left: -300,
				behavior: 'smooth'
			});
		}
	};

	const scrollRight = () => {
		if (cardsContainer.value) {
			cardsContainer.value.scrollBy({
				left: 300,
				behavior: 'smooth'
			});
		}
	};

	// 状态持久化键名
	const STORAGE_KEY = 'multi-publish-state';

	// 保存状态到localStorage
	const saveState = () => {
		try {
			const stateToSave = {
				publishCards: publishCards.value.map(card => ({
					...card,
					// 排除不能序列化的属性
					mediaList: card.mediaList.map(media => ({
						...media,
						previewUrl: null, // 预览URL不保存，重新生成
						file: null // File对象不保存
					}))
				}))
			};
			localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
		} catch (error) {
			console.warn('保存状态失败:', error);
		}
	};

	// 从localStorage恢复状态
	const restoreState = () => {
		try {
			const savedState = localStorage.getItem(STORAGE_KEY);
			if (savedState) {
				const parsedState = JSON.parse(savedState);
				if (parsedState.publishCards && Array.isArray(parsedState.publishCards)) {
					publishCards.value = parsedState.publishCards;
					// 重新生成预览URL（如果需要的话）
					publishCards.value.forEach(card => {
						card.mediaList.forEach(media => {
							if (media.isFromLibrary && media.videoData && media.videoData.url) {
								media.previewUrl = media.videoData.url;
							}
						});
					});
				}
			}
		} catch (error) {
			console.warn('恢复状态失败:', error);
		}
	};

	// 监听状态变化并自动保存
	watch(publishCards, saveState, {
		deep: true
	});

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

	// 组件挂载时恢复状态
	onMounted(() => {
		restoreState();
	});

	// 组件卸载时清理资源
	onUnmounted(() => {
		// 清理所有媒体预览URL
		publishCards.value.forEach(card => {
			card.mediaList.forEach(media => {
				if (media.previewUrl) {
					URL.revokeObjectURL(media.previewUrl);
				}
			});
		});
		// 保存最终状态
		saveState();
		// 移除事件监听器
		window.removeEventListener('beforeunload', saveState);
	});

	// 页面刷新前保存状态
	window.addEventListener('beforeunload', saveState);
</script>

<style scoped>
	.multi-publish-container {
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
		justify-content: flex-end;
		margin-bottom: 20px;
	}

	.add-publish-btn {
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

	.add-icon {
		margin-right: 5px;
		font-size: 16px;
	}

	/* 平台选择弹窗样式 */
	.platform-modal {
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

	.platform-modal-content {
		background-color: white;
		border-radius: 8px;
		width: 400px;
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

	.platform-options {
		display: flex;
		justify-content: space-around;
	}

	.platform-option {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 15px;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s;
	}

	.platform-option:hover {
		background-color: #f5f5f5;
	}

	.platform-option.selected {
		background-color: #e6f7ff;
		border: 1px solid #91d5ff;
	}

	.platform-icon {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		margin-bottom: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.douyin-icon {
		background-color: #e0e7ff;
		position: relative;
	}

	.douyin-icon::before {
		content: '';
		width: 20px;
		height: 20px;
		background-color: #6366f1;
		border-radius: 50%;
	}

	.xiaohongshu-icon {
		background-color: #fef2f2;
		position: relative;
	}

	.xiaohongshu-icon::before {
		content: '';
		width: 20px;
		height: 20px;
		background-color: #ef4444;
		border-radius: 50%;
	}

	.shipinhao-icon {
		background-color: #ecfdf5;
		position: relative;
	}

	.shipinhao-icon::before {
		content: '';
		width: 20px;
		height: 20px;
		background-color: #10b981;
		border-radius: 50%;
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
		border: 1px solid #ddd;
		background-color: white;
		border-radius: 4px;
		cursor: pointer;
	}

	.confirm-btn {
		padding: 8px 15px;
		background-color: #6366f1;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}

	/* 发布卡片容器样式 */
	.publish-cards-container {
		position: relative;
		margin-top: 20px;
		display: flex;
		align-items: center;
	}

	.cards-scroll-area {
		display: flex;
		overflow-x: auto;
		scroll-behavior: smooth;
		padding: 10px 0;
		gap: 20px;
		width: 100%;
		scrollbar-width: none;
		/* Firefox */
		-ms-overflow-style: none;
		/* IE and Edge */
	}

	.cards-scroll-area::-webkit-scrollbar {
		display: none;
		/* Chrome, Safari, Opera */
	}

	.scroll-btn {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		width: 30px;
		height: 30px;
		border-radius: 50%;
		background-color: white;
		border: 1px solid #ddd;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		z-index: 10;
		box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
	}

	.scroll-left {
		left: -15px;
	}

	.scroll-right {
		right: -15px;
	}

	/* 空状态样式 */
	.empty-state {
		width: 100%;
		padding: 50px 0;
		text-align: center;
		color: #999;
		background-color: #f9f9f9;
		border-radius: 8px;
	}

	/* 发布卡片样式 */
	.publish-card {
		min-width: 300px;
		width: 300px;
		border: 1px solid #eee;
		border-radius: 8px;
		background-color: white;
		box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
		overflow: hidden;
		flex-shrink: 0;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 15px;
		background-color: #f8f9fc;
		border-bottom: 1px solid #eee;
	}

	.platform-info {
		display: flex;
		align-items: center;
	}

	.platform-info .platform-icon {
		width: 24px;
		height: 24px;
		margin-right: 8px;
		margin-bottom: 0;
	}

	.platform-info .platform-icon::before {
		width: 12px;
		height: 12px;
	}

	.card-actions {
		display: flex;
		gap: 10px;
	}

	.delete-card-btn {
		padding: 4px 8px;
		background-color: #fff;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 12px;
		cursor: pointer;
	}

	.delete-card-btn:hover {
		background-color: #f5f5f5;
	}

	.card-content {
		padding: 15px;
	}

	.card-section {
		margin-bottom: 15px;
	}

	.section-title {
		font-size: 14px;
		font-weight: bold;
		margin-bottom: 8px;
		color: #333;
	}

	/* 账号选择器样式 */
	.account-selector {
		border: 1px dashed #ddd;
		border-radius: 4px;
		padding: 8px;
		cursor: pointer;
		min-height: 40px;
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
		height: 24px;
		color: #909399;
	}

	.selected-account {
		display: flex;
		align-items: center;
		background-color: #f0f7ff;
		border: 1px solid #d9ecff;
		border-radius: 4px;
		padding: 5px 10px;
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

	/* 发布类型选择器样式 */
	.publish-type-selector {
		display: flex;
		gap: 10px;
	}

	.type-btn {
		flex: 1;
		padding: 8px 0;
		border: 1px solid #ddd;
		border-radius: 4px;
		background-color: white;
		cursor: pointer;
		transition: all 0.3s;
	}

	.type-btn.active {
		background-color: #6366f1;
		color: white;
		border-color: #6366f1;
	}

	/* 媒体上传区域样式 */
	.media-container {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.video-upload-area,
	.image-upload-area {
		border: 2px dashed #ddd;
		border-radius: 4px;
		width: 80px;
		height: 80px;
		display: flex;
		justify-content: center;
		align-items: center;
		cursor: pointer;
		background-color: #f9f9f9;
		transition: all 0.3s;
	}

	.video-upload-area:hover,
	.image-upload-area:hover {
		border-color: #409eff;
		background-color: #f0f7ff;
	}

	.upload-icon {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.upload-icon .icon {
		font-size: 20px;
		color: #909399;
	}

	.upload-icon .text {
		margin-top: 5px;
		color: #606266;
		font-size: 12px;
	}

	.video-preview,
	.image-preview {
		position: relative;
		width: 80px;
		height: 80px;
		border-radius: 4px;
		overflow: hidden;
	}

	.video-preview video,
	.image-preview img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.media-actions {
		position: absolute;
		top: 5px;
		right: 5px;
		z-index: 10;
	}

	.remove-btn {
		background-color: rgba(0, 0, 0, 0.5);
		color: white;
		border: none;
		border-radius: 4px;
		padding: 2px 5px;
		cursor: pointer;
		font-size: 10px;
	}

	.remove-btn:hover {
		background-color: rgba(0, 0, 0, 0.7);
	}

	.media-count {
		margin-top: 8px;
		font-size: 12px;
		color: #909399;
	}

	/* 标题输入区域样式 */
	.title-input-container {
		position: relative;
	}

	.title-input-container textarea {
		width: 100%;
		padding: 8px;
		border: 1px solid #ddd;
		border-radius: 4px;
		resize: none;
		font-size: 14px;
	}

	.char-count {
		position: absolute;
		bottom: 5px;
		right: 10px;
		font-size: 12px;
		color: #999;
	}

	/* 话题选择区域样式 */
	.tags-container {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.tag {
		background-color: #f0f7ff;
		border: 1px solid #d9ecff;
		border-radius: 4px;
		padding: 4px 8px;
		font-size: 12px;
		color: #409eff;
		display: flex;
		align-items: center;
	}

	.remove-tag {
		margin-left: 5px;
		cursor: pointer;
		font-size: 14px;
	}

	.add-tag {
		border: 1px dashed #ddd;
		border-radius: 4px;
		padding: 4px 8px;
		font-size: 12px;
		color: #909399;
		cursor: pointer;
	}

	.add-tag:hover {
		border-color: #409eff;
		color: #409eff;
	}

	/* 底部操作按钮样式 */
	.card-actions-bottom {
		display: flex;
		justify-content: center;
		margin-top: 15px;
	}

	.publish-btn {
		padding: 8px 20px;
		background-color: #6366f1;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
	}

	.publish-btn:disabled {
		background-color: #a5a6f6;
		cursor: not-allowed;
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
		background-color: white;
		border-radius: 8px;
		width: 400px;
		max-width: 90%;
		max-height: 80vh;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.refresh-btn {
		background: none;
		border: none;
		cursor: pointer;
		color: #999;
		font-size: 16px;
		margin-right: 10px;
	}

	.refresh-icon {
		display: inline-block;
	}

	.loading-accounts,
	.no-accounts {
		padding: 20px;
		text-align: center;
		color: #999;
	}

	.account-list {
		max-height: 300px;
		overflow-y: auto;
		padding: 0 10px;
	}

	.account-item {
		display: flex;
		align-items: center;
		padding: 10px;
		border-bottom: 1px solid #eee;
		cursor: pointer;
	}

	.account-item:hover {
		background-color: #f5f5f5;
	}

	.account-item:last-child {
		border-bottom: none;
	}

	.account-info {
		display: flex;
		flex-direction: column;
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
		background-color: white;
		border-radius: 8px;
		width: 400px;
		max-width: 90%;
		max-height: 80vh;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.custom-tag-input {
		display: flex;
		margin-bottom: 15px;
	}

	.custom-tag-input input {
		flex: 1;
		padding: 8px;
		border: 1px solid #ddd;
		border-radius: 4px 0 0 4px;
		font-size: 14px;
	}

	.custom-tag-input button {
		padding: 8px 15px;
		background-color: #6366f1;
		color: white;
		border: none;
		border-radius: 0 4px 4px 0;
		cursor: pointer;
	}

	.suggested-tags h4 {
		margin-bottom: 10px;
		font-size: 14px;
		font-weight: 500;
	}

	.tag-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 10px;
	}

	.suggested-tag {
		background-color: #f5f5f5;
		border-radius: 4px;
		padding: 8px;
		text-align: center;
		font-size: 12px;
		cursor: pointer;
	}

	.suggested-tag:hover {
		background-color: #e0e0e0;
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
		border-radius: 12px;
		padding: 20px;
		width: 280px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
		display: flex;
		flex-direction: column;
		gap: 15px;
	}

	.source-option {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 20px 15px;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.3s ease;
		border: 2px solid #f0f0f0;
	}

	.source-option:hover {
		background-color: #f8f9ff;
		border-color: #6366f1;
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
	}

	.source-icon {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 8px;
		font-size: 24px;
	}

	.local-icon {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.library-icon {
		background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
		color: white;
	}

	.source-text {
		font-size: 14px;
		font-weight: 500;
		color: #333;
	}

	/* 媒体上传区域间距 */
	.media-section {
		margin-bottom: 25px;
	}

	.media-item {
		margin-bottom: 15px;
	}

	.media-item:last-child {
		margin-bottom: 0;
	}

	/* 定时发布设置美化样式 */
	.timer-toggle {
		display: flex;
		align-items: center;
		margin-bottom: 15px;
	}

	.switch {
		position: relative;
		display: inline-block;
		width: 44px;
		height: 24px;
		margin-right: 12px;
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
		height: 18px;
		width: 18px;
		left: 3px;
		bottom: 3px;
		background-color: white;
		transition: .4s;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	input:checked + .slider {
		background-color: #6366f1;
	}

	input:checked + .slider:before {
		transform: translateX(20px);
	}

	.slider.round {
		border-radius: 24px;
	}

	.slider.round:before {
		border-radius: 50%;
	}

	.toggle-label {
		font-size: 16px;
		font-weight: 500;
		color: #333;
	}

	.timer-settings {
		background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
		border-radius: 12px;
		padding: 20px;
		border: 1px solid #e1e8ed;
	}

	.setting-item {
		margin-bottom: 18px;
	}

	.setting-item:last-child {
		margin-bottom: 0;
	}

	.setting-label {
		display: block;
		margin-bottom: 8px;
		font-size: 14px;
		font-weight: 500;
		color: #4a5568;
	}

	.setting-select {
		width: 100%;
		padding: 10px 12px;
		border: 2px solid #e2e8f0;
		border-radius: 8px;
		font-size: 14px;
		background-color: white;
		transition: border-color 0.3s ease;
	}

	.setting-select:focus {
		outline: none;
		border-color: #6366f1;
		box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
	}

	.time-slots {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.time-input {
		padding: 8px 10px;
		border: 2px solid #e2e8f0;
		border-radius: 6px;
		font-size: 14px;
		background-color: white;
		transition: border-color 0.3s ease;
		min-width: 120px;
	}

	.time-input:focus {
		outline: none;
		border-color: #6366f1;
		box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
	}

	.days-setting {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.days-input {
		width: 80px;
		padding: 8px 10px;
		border: 2px solid #e2e8f0;
		border-radius: 6px;
		font-size: 14px;
		background-color: white;
		transition: border-color 0.3s ease;
	}

	.days-input:focus {
		outline: none;
		border-color: #6366f1;
		box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
	}

	.days-unit {
		font-size: 14px;
		color: #6b7280;
		font-weight: 500;
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
		background-color: white;
	}

	.material-item:hover {
		transform: translateY(-3px);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
	}

	.material-item.selected {
		border-color: #6366f1;
		box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
	}

	.material-checkbox {
		position: absolute;
		top: 10px;
		left: 10px;
		z-index: 2;
	}

	.checkbox {
		width: 20px;
		height: 20px;
		border: 2px solid #ddd;
		border-radius: 4px;
		background-color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.checkbox.checked {
		background-color: #6366f1;
		border-color: #6366f1;
	}

	.checkbox.checked::after {
		content: '✓';
		color: white;
		font-size: 12px;
		font-weight: bold;
	}

	.material-preview {
		position: relative;
		height: 120px;
		background-color: #f5f5f5;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}

	.material-preview .delete-btn {
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

	.material-item:hover .delete-btn {
		opacity: 1;
	}

	.play-icon {
		width: 40px;
		height: 40px;
		opacity: 0.7;
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

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 10px;
		padding: 15px 20px;
		border-top: 1px solid #eee;
	}

	.cancel-btn {
		padding: 8px 16px;
		background-color: #f5f5f5;
		border: 1px solid #ddd;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
	}

	.confirm-btn {
		padding: 8px 16px;
		background-color: #6366f1;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
	}

	.confirm-btn:disabled {
		background-color: #a5a6f6;
		cursor: not-allowed;
	}
</style>