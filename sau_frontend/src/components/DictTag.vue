<template>
  <div class="dict-tag-container">
    <el-tag
      v-if="displayValue"
      :type="tagType"
      :style="{ width: tagWidth ? tagWidth + 'px' : 'auto' }"
      size="small"
    >
      {{ displayValue }}
    </el-tag>
    <span v-else-if="value">{{ value }}</span>
    <span v-else>-</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  options: {
    type: Array,
    default: () => []
  },
  value: {
    type: [String, Number, Boolean],
    default: ''
  },
  tagWidth: {
    type: [String, Number],
    default: null
  }
})

const displayValue = computed(() => {
  if (!props.options || !props.value) return props.value
  
  const option = props.options.find(item => item.value === props.value)
  return option ? option.label : props.value
})

const tagType = computed(() => {
  if (!props.options || !props.value) return 'info'
  
  const option = props.options.find(item => item.value === props.value)
  return option ? (option.type || 'info') : 'info'
})
</script>

<style scoped>
.dict-tag-container {
  display: inline-block;
}
</style>