<template>
	<div style="padding: 20px;">
		<button @click="openInput">添加账号</button>

		<div v-if="showQrCode" style="margin-top: 20px;">
			<h3>收到的二维码：</h3>
			<img :src="qrCodeSrc" alt="二维码" style="width: 200px;" />
		</div>

		<div v-if="message" style="margin-top: 20px;">
			<h3>收到的消息：</h3>
			<p>{{ message }}</p>
		</div>
	</div>
</template>

<script setup>
	import {
		ref
	} from 'vue'

	const showQrCode = ref(false)
	const qrCodeSrc = ref('')
	const message = ref(null)
	let eventSource = null

	// 弹出输入框并直接建立 EventSource 连接
	const openInput = () => {
		const id = prompt('请输入ID:')
		if (!id) return

		// 直接创建 EventSource 连接，带上参数 type=2&id=xxx
		const url = `http://localhost:5409/login?type=2&id=${id}&_=${Date.now()}`
		eventSource = new EventSource(url)

		let count = 0

		// 接收事件流中的消息
		eventSource.onmessage = (event) => {
			count++
			const data = event.data

			if (count === 1) {
				// 第一次收到的是 base64 图片
				console.log('收到二维码:', data)
				qrCodeSrc.value = `${data}`
				showQrCode.value = true
			} else if (count === 2) {
				// 第二次收到普通消息
				console.log('收到消息:', data)
				message.value = data

				// 主动关闭连接
				eventSource.close()
				alert('已完成操作，连接已关闭')
			}
		}

		// 错误处理
		eventSource.onerror = (err) => {
			console.error('EventSource 发生错误:', err)
			eventSource.close()
			alert('连接异常中断')
		}
	}
</script>

<style scoped>
	/* 可根据需要添加样式 */
</style>