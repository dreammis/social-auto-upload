<template>
	<div class="modal-overlay" v-if="visible">
		<div class="modal-container">
			<div class="modal-header">
				<h2>添加{{ getPlatformName() }}账号</h2>
				<button class="close-btn" @click="closeModal">×</button>
			</div>
			<div class="modal-body">
				<div class="input-group">
					<label for="accountId">账号ID</label>
					<input type="text" id="accountId" v-model="accountId" placeholder="请输入账号ID"
						:class="{ 'error': showError }" />
					<div class="error-message" v-if="showError">请输入账号ID</div>
				</div>

				<div class="qr-code-container" v-if="showQrCode">
					<h3>请扫描二维码登录</h3>
					<img :src="qrCodeSrc" alt="登录二维码" class="qr-code" />
				</div>

				<div class="message-container" v-if="message">
					<h3>登录状态</h3>
					<p>{{ message }}</p>
				</div>
			</div>
			<div class="modal-footer">
				<button class="cancel-btn" @click="closeModal">取消</button>
				<button class="add-btn" @click="addAccount" :disabled="isLoading">
					{{ isLoading ? '处理中...' : '添加账号' }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
	import {
		ref,
		defineProps,
		defineEmits,
		watch
	} from 'vue';
	import {
		API_BASE_URL
	} from '../config';

	const props = defineProps({
		visible: {
			type: Boolean,
			default: false
		},
		platformId: {
			type: String,
			default: 'douyin'
		}
	});

	const emit = defineEmits(['close', 'login', 'account-added']);

	// 表单数据
	const accountId = ref('');
	const showError = ref(false);
	const isLoading = ref(false);

	// SSE 连接相关
	const showQrCode = ref(false);
	const qrCodeSrc = ref('');
	const message = ref('');
	let eventSource = null;

	// 监听visible变化，重置表单
	watch(() => props.visible, (newValue) => {
		if (!newValue) {
			resetForm();
		}
	});

	// 获取平台名称
	const getPlatformName = () => {
		const platformMap = {
			'douyin': '抖音',
			'douyin2': '抖音',
			'xiaohongshu': '小红书',
			'shipinhao': '视频号'
		};
		return platformMap[props.platformId] || '';
	};

	// 关闭模态窗口
	const closeModal = () => {
		// 如果有活跃的 EventSource 连接，关闭它
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}

		emit('close');
	};

	// 重置表单
	const resetForm = () => {
		accountId.value = '';
		showError.value = false;
		isLoading.value = false;
		showQrCode.value = false;
		qrCodeSrc.value = '';
		message.value = '';

		// 确保关闭 EventSource 连接
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}
	};

	// 添加账号
	const addAccount = () => {
		// 表单验证
		if (!accountId.value.trim()) {
			showError.value = true;
			return;
		}

		showError.value = false;
		isLoading.value = true;

		// 获取平台对应的type值
		const platformTypeMap = {
			'douyin': 3,
			'kuaishou': 4, // 新增抖音平台，编号为4
			'xiaohongshu': 1,
			'shipinhao': 2
		};
		const platformType = platformTypeMap[props.platformId] || 3; // 默认使用抖音type=3

		// 创建 EventSource 连接，使用正确的平台type
		const url = `api/login?type=${platformType}&id=${accountId.value}`;
		eventSource = new EventSource(url);

		let count = 0;

		// 接收事件流中的消息
		eventSource.onmessage = (event) => {
			console.log("onmessage");
			count++;
			const data = event.data;

			if (count === 1) {
				// 第一次收到的是 base64 图片（二维码）
				console.log('收到二维码:', data);
				qrCodeSrc.value = `${data}`;
				showQrCode.value = true;

				// 通知父组件登录过程开始
				emit('login', {
					status: 'qrcode',
					platformId: props.platformId,
					accountId: accountId.value
				});
			} else if (count === 2) {
				// 第二次收到普通消息（登录结果）
				console.log('收到消息:', data);
				message.value = data;
				isLoading.value = false;

				// 主动关闭连接
				eventSource.close();
				eventSource = null;

				// 通知父组件账号添加成功
				emit('account-added', {
					status: 'success',
					platformId: props.platformId,
					accountId: accountId.value,
					message: data
				});
				
				// 显示成功提示并关闭弹窗
				ElMessage({
  message: `账号添加成功,请手动刷新: ${data}`,
  type: 'success',
  duration: 3000, // 显示时长，单位毫秒
  showClose: true, // 是否显示关闭按钮
});
				closeModal();
			}
		};

		// 错误处理
		eventSource.onerror = (err) => {
			console.error('EventSource 发生错误:', err);
			message.value = '连接异常中断';
			isLoading.value = false;

			if (eventSource) {
				eventSource.close();
				eventSource = null;
			}

			// 通知父组件登录失败
			emit('login', {
				status: 'error',
				platformId: props.platformId,
				accountId: accountId.value,
				error: '连接异常中断'
			});
			
			// 显示错误提示并关闭弹窗
			alert('登录失败: 连接异常中断');
			closeModal();
		};
	};
</script>

<style scoped>
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background-color: rgba(0, 0, 0, 0.5);
		display: flex;
		justify-content: center;
		align-items: center;
		z-index: 1000;
	}

	.modal-container {
		background-color: white;
		border-radius: 8px;
		width: 500px;
		max-width: 90%;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
		overflow: hidden;
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 16px 20px;
		border-bottom: 1px solid #eee;
	}

	.modal-header h2 {
		margin: 0;
		font-size: 18px;
		color: #333;
	}

	.close-btn {
		background: none;
		border: none;
		font-size: 24px;
		cursor: pointer;
		color: #999;
	}

	.modal-body {
		padding: 20px;
	}

	.input-group {
		margin-bottom: 20px;
	}

	.input-group label {
		display: block;
		margin-bottom: 8px;
		font-weight: 500;
		color: #333;
	}

	input {
		width: 100%;
		padding: 10px 12px;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 14px;
		transition: border-color 0.3s;
	}

	input:focus {
		outline: none;
		border-color: #1890ff;
	}

	input.error {
		border-color: #ff4d4f;
	}

	.error-message {
		color: #ff4d4f;
		font-size: 12px;
		margin-top: 4px;
	}

	.modal-footer {
		padding: 16px 20px;
		border-top: 1px solid #eee;
		display: flex;
		justify-content: flex-end;
		gap: 12px;
	}

	.cancel-btn {
		padding: 8px 16px;
		background-color: #f7f7f7;
		border: 1px solid #ddd;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
		color: #666;
	}

	.add-btn {
		padding: 8px 16px;
		background-color: #1890ff;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		font-size: 14px;
	}

	.add-btn:disabled {
		background-color: #bae7ff;
		cursor: not-allowed;
	}

	.qr-code-container {
		margin-top: 20px;
		text-align: center;
	}

	.qr-code {
		width: 200px;
		height: 200px;
		margin: 10px auto;
		display: block;
	}

	.message-container {
		margin-top: 20px;
		padding: 12px;
		background-color: #f6f6f6;
		border-radius: 4px;
	}

	.message-container h3 {
		margin-top: 0;
		margin-bottom: 8px;
		font-size: 16px;
		color: #333;
	}

	.message-container p {
		margin: 0;
		color: #666;
	}
</style>