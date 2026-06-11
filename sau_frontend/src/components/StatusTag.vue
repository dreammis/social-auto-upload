<template>
  <!--
    账号状态标签：
    - 正常/验证中：纯 tag
    - 异常且 statusDetail 非空：tag 包 el-tooltip，hover 显示详细异常
      （淘宝页面 .error-desc-- 的文本，如 "账号违规: 原创性不足"）
    - 异常但 statusDetail 为空：tag，无 tooltip（说明抓不到具体原因，
      通常是 cookie 失效导致页面没渲染出状态栏）

    故意不支持点击：异常时由「操作」列的「重登」按钮触发重登流程，
    避免与 hover tooltip 触发误触以及误以为是按钮。
  -->
  <el-tooltip
    v-if="status === '异常' && statusDetail"
    :content="statusDetail"
    placement="top"
    :show-after="200"
  >
    <el-tag :type="tagType" effect="plain" class="status-tag">
      <el-icon v-if="status === '验证中'" class="is-loading">
        <Loading />
      </el-icon>
      {{ status }}
    </el-tag>
  </el-tooltip>
  <el-tag v-else :type="tagType" effect="plain" class="status-tag">
    <el-icon v-if="status === '验证中'" class="is-loading">
      <Loading />
    </el-icon>
    {{ status }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  status: { type: String, required: true },        // '正常' | '异常' | '验证中'
  statusDetail: { type: String, default: '' },     // 异常详情，可空
})

const tagType = computed(() => {
  if (props.status === '验证中') return 'info'
  if (props.status === '正常') return 'success'
  return 'danger'
})
</script>
