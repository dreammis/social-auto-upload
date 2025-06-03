<template>
	<div class="account-view">
		<h1>账号管理</h1>
		<div class="account-container">
			<!-- 平台选项卡 -->
			<div class="platform-tabs">
				<div v-for="platform in platforms" :key="platform.id" class="platform-tab"
					:class="{ active: activePlatform === platform.id }" @click="activePlatform = platform.id">
					{{ platform.name }}
				</div>
			</div>

			<div class="filter-bar">
				<div class="filter-item">
					<select v-model="statusFilter">
						<option value="">账号状态</option>
						<option value="正常">正常</option>
						<option value="异常">异常</option>
						<!-- <option value="已封禁">已封禁</option> -->
					</select>
				</div>
				<!-- <div class="filter-item">
          <select>
            <option>分组</option>
            <option>默认分组</option>
            <option>自媒体</option>
            <option>电商</option>
          </select>
        </div> -->
				<div class="search-box">
					<input type="text" placeholder="输入账号名称搜索" v-model="searchQuery" />
					<button><i class="search-icon"></i></button>
				</div>
				<button class="refresh-btn" @click="refreshAccounts" title="刷新账号列表">
					<i class="refresh-icon"></i>
				</button>
				<button class="btn-add" @click="showAddAccountModal">添加账号</button>
			</div>

			<div class="account-list">
				<!-- 加载状态 -->
				<div v-if="isLoading" class="loading-state">
					<div class="loading-spinner"></div>
					<p>正在加载账号列表...</p>
				</div>

				<!-- 无数据提示 -->
				<div v-else-if="filteredAccounts.length === 0" class="empty-state">
					<p>暂无账号数据</p>
					<button class="btn-add-small" @click="showAddAccountModal">添加账号</button>
				</div>

				<!-- 账号列表 -->
				<div v-else v-for="account in filteredAccounts" :key="account.id" class="account-card">
					<div class="account-avatar">
						<img :src="account.avatar" alt="账号头像" />
					</div>
					<div class="account-info">
						<div class="account-name">{{ account.name }}</div>
						<div class="account-stats">
							<div class="stat-item">
								<span class="stat-label">粉丝</span>
								<span class="stat-value">{{ account.followers }}</span>
							</div>
							<div class="stat-item">
								<span class="stat-label">获赞</span>
								<span class="stat-value">{{ account.likes }}</span>
							</div>
							<div class="stat-item">
								<span class="stat-label">播放量</span>
								<span class="stat-value">{{ account.views }}</span>
							</div>
						</div>
						<div class="account-status" :class="'status-' + account.statusType">{{ account.status }}</div>
					</div>
				</div>
			</div>
		</div>

		<!-- 添加账号模态窗口 -->
		<AddAccountModal :visible="isAddAccountModalVisible" :platformId="activePlatform" @close="closeAddAccountModal"
			@login="handleAccountLogin" @account-added="handleAccountAdded" />
	</div>
</template>

<script setup>
	import { ref, computed, onMounted, watch } from 'vue';
	import AddAccountModal from './AddAccountModal.vue';
	import { API_BASE_URL, globalAccountsCache } from '../config';
	import axios from 'axios'
	import tx from '@assets/fengbaobao.png'

	// 平台数据
	const platforms = [
		{ id: 'douyin', name: '抖音' },
		{ id: 'kuaishou', name: '快手' },
		{ id: 'xiaohongshu', name: '小红书' },
		{ id: 'shipinhao', name: '视频号' },
	];

	// 当前选中的平台
	const activePlatform = ref('douyin');

	// 搜索关键词
	const searchQuery = ref('');

	// 状态筛选
	const statusFilter = ref('');

	// 账号数据
	const accountsData = ref({
		douyin: [],
		kuaishou: [],
		xiaohongshu: [],
		shipinhao: []
	});

	// 加载状态
	const isLoading = ref(false);

	// 获取账号列表
	const fetchAccounts = async (forceRefresh = false) => {
		// 如果全局缓存有效且不强制刷新，则使用缓存数据
		if (!forceRefresh && globalAccountsCache.isValid()) {
			console.log("使用缓存的账号数据");
			processAccountsData(globalAccountsCache.accounts);
			return;
		}

		isLoading.value = true;
		try {
			console.log("getValidAccounts请求前",`/api/getValidAccounts`);
			const response = await axios.get(`/api/getValidAccounts`);
			console.log("getValidAccounts", response);

			if (response.data.code === 200 && response.data.data) {
				// 更新全局缓存
				globalAccountsCache.updateCache(response.data.data);
				
				// 处理账号数据
				processAccountsData(response.data.data);
			}
		} catch (error) {
			console.error('获取账号列表失败:', error);
			// 如果获取失败，使用空数组
			accountsData.value = {
				douyin: [],
				xiaohongshu: [],
				shipinhao: []
			};
		} finally {
			isLoading.value = false;
		}
	};

	// 处理账号数据
	const processAccountsData = (data) => {
		// 清空所有平台的账号数据
		accountsData.value = {
			douyin: [],
			xiaohongshu: [],
			shipinhao: []
		};

		// 根据type值将账号分配到对应平台
		data.forEach(account => {
			const formattedAccount = {
				id: account[0]|| Math.random().toString(36).substr(2, 9),
				name: account[3] || '未命名账号',
				avatar: tx,
				followers: formatNumber(account.followers || 0),
				likes: formatNumber(account.likes || 0),
				views: formatNumber(account.views || 0),
				status: account[4] === 1 ? '正常' : '异常',
				statusType: account[4] === 1 ? 'normal' : 'warning',
				cookiejson:account[2],
				userData: account
			};

			// 根据type值分配到对应平台
			switch (account[1]) {
				case 3: // 抖音
					accountsData.value.douyin.push(formattedAccount);
					break;
				case 4: // 新增抖音平台
					accountsData.value.kuaishou.push(formattedAccount);
					break;
				case 1: // 小红书
					accountsData.value.xiaohongshu.push(formattedAccount);
					break;
				case 2: // 视频号
					accountsData.value.shipinhao.push(formattedAccount);
					break;
				default:
					// 如果type不匹配，默认放入当前选中的平台
					accountsData.value[activePlatform.value].push(formattedAccount);
					break;
			}
		});
	};

	// 强制刷新账号列表
	const refreshAccounts = () => {
		fetchAccounts(true);
	};

	// 格式化数字
	const formatNumber = (num) => {
		if (num >= 100000000) {
			return (num / 100000000).toFixed(1) + '亿';
		} else if (num >= 10000) {
			return (num / 10000).toFixed(1) + '万';
		}
		return num.toString();
	};

	// 获取平台ID数字
	const getPlatformIdNumber = (platform) => {
		switch (platform) {
			case 'douyin': return 3;
			case 'douyin2': return 4; // 新增抖音平台，编号为4
			case 'xiaohongshu': return 1;
			case 'shipinhao': return 2;
			default: return 0;
		}
	};

	// 根据当前选中平台和搜索关键词过滤账号列表
	const filteredAccounts = computed(() => {
		const accounts = accountsData.value[activePlatform.value] || [];
		let filtered = accounts;

		// 按名称搜索过滤
		if (searchQuery.value) {
			filtered = filtered.filter(account =>
				account.name.toLowerCase().includes(searchQuery.value.toLowerCase())
			);
		}

		// 按状态过滤
		if (statusFilter.value) {
			filtered = filtered.filter(account => account.status === statusFilter.value);
		}

		return filtered;
	});

	// 在组件挂载时获取账号列表
	onMounted(() => {
		fetchAccounts();
	});

	// 监听平台切换，重新获取账号列表
	watch(activePlatform, () => {
		// 平台切换时不需要强制刷新，可以使用缓存
		fetchAccounts(false);
	});

	// 添加账号模态窗口控制
	const isAddAccountModalVisible = ref(false);

	const showAddAccountModal = () => {
		console.log("showAddAccountModal");
		// 确保每次打开都是全新的弹窗状态
		isAddAccountModalVisible.value = true;
	};

	const closeAddAccountModal = () => {
		isAddAccountModalVisible.value = false;
		// 弹窗关闭后，确保下次打开是全新状态
		console.log('弹窗已关闭，状态已重置');
	};

	const handleAccountAdded = () => {
		// 账号添加成功后，不再自动刷新列表
		// 用户可以点击刷新按钮手动刷新
		console.log('账号添加成功，可点击刷新按钮更新列表');
	};

	const handleAccountLogin = (data) => {
		console.log('账号登录状态:', data);
		
		// 登录成功后不再自动刷新账号列表
		// 用户可以点击刷新按钮手动刷新
	};
</script>

<style scoped>
	.account-view {
		padding: 20px;
	}

	h1 {
		margin-bottom: 20px;
		font-size: 24px;
	}

	.account-container {
		background-color: #fff;
	}

	/* 加载状态 */
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 40px 0;
		width: 100%;
	}

	.loading-spinner {
		width: 40px;
		height: 40px;
		border: 4px solid #f3f3f3;
		border-top: 4px solid #3498db;
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin-bottom: 15px;
	}

	@keyframes spin {
		0% {
			transform: rotate(0deg);
		}

		100% {
			transform: rotate(360deg);
		}
	}

	/* 空状态 */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 40px 0;
		width: 100%;
		color: #666;
	}

	.empty-state p {
		margin-bottom: 15px;
		font-size: 16px;
	}

	.btn-add-small {
		padding: 8px 16px;
		background-color: #1890ff;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
		transition: background-color 0.3s;
	}

	.btn-add-small:hover {
		background-color: #40a9ff;
	}

	.filter-bar {
		display: flex;
		margin-bottom: 20px;
		align-items: center;
	}

	.filter-item {
		margin-right: 15px;
	}

	.filter-item select {
		padding: 8px 15px;
		border: 1px solid #ddd;
		border-radius: 4px;
		background-color: #fff;
	}

	.search-box {
		display: flex;
		margin-right: 15px;
		flex: 1;
	}

	.search-box input {
		flex: 1;
		padding: 8px 15px;
		border: 1px solid #ddd;
		border-radius: 4px 0 0 4px;
	}

	.search-box button {
		padding: 8px 15px;
		background-color: #f5f5f5;
		border: 1px solid #ddd;
		border-left: none;
		border-radius: 0 4px 4px 0;
	}

	.refresh-btn {
		background-color: #f5f5f5;
		color: #666;
		border: 1px solid #ddd;
		padding: 8px 15px;
		border-radius: 4px;
		cursor: pointer;
		margin-right: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.refresh-btn:hover {
		background-color: #e6e6e6;
	}

	.refresh-icon {
		display: inline-block;
		width: 16px;
		height: 16px;
		border: 2px solid #666;
		border-radius: 50%;
		border-top-color: transparent;
		position: relative;
	}

	.refresh-icon:before {
		content: '';
		position: absolute;
		top: -5px;
		right: 0;
		width: 0;
		height: 0;
		border-style: solid;
		border-width: 0 0 6px 6px;
		border-color: transparent transparent #666 transparent;
	}

	.btn-add {
		background-color: #6366f1;
		color: white;
		border: none;
		padding: 8px 15px;
		border-radius: 4px;
		cursor: pointer;
	}

	.account-list {
		margin-top: 20px;
	}

	.account-card {
		display: flex;
		align-items: center;
		padding: 15px;
		border: 1px solid #eee;
		border-radius: 8px;
		margin-bottom: 10px;
	}

	.account-avatar {
		width: 50px;
		height: 50px;
		border-radius: 50%;
		overflow: hidden;
		margin-right: 15px;
	}

	.account-avatar img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.account-info {
		display: flex;
		flex-direction: column;
		flex: 1;
	}

	.account-name {
		font-weight: bold;
		margin-bottom: 5px;
		font-size: 16px;
	}

	.account-stats {
		display: flex;
		margin-bottom: 5px;
	}

	.stat-item {
		margin-right: 15px;
		display: flex;
		align-items: center;
	}

	.stat-label {
		color: #666;
		font-size: 12px;
		margin-right: 5px;
	}

	.stat-value {
		font-weight: 500;
		font-size: 14px;
	}

	.account-status {
		font-size: 14px;
	}

	.status-normal {
		color: #10b981;
	}

	.status-warning {
		color: #f59e0b;
	}

	.status-danger {
		color: #ef4444;
	}

	.platform-tabs {
		display: flex;
		border-bottom: 1px solid #eee;
		margin-bottom: 20px;
	}

	.platform-tab {
		padding: 10px 20px;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		font-weight: 500;
		transition: all 0.2s;
	}

	.platform-tab:hover {
		color: #6366f1;
	}

	.platform-tab.active {
		color: #6366f1;
		border-bottom-color: #6366f1;
	}
</style>