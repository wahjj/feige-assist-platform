<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: '',
  },
})

const tone = computed(() => {
  if (['已完成', '上架', 'approved', '已通过', 'AI处理中'].includes(props.status)) {
    return 'tone-success'
  }
  if (['待发货', '待付款', 'pending', '待审批'].includes(props.status)) {
    return 'tone-warning'
  }
  if (['已发货', 'human', '人工处理中', '接待中'].includes(props.status)) {
    return 'tone-info'
  }
  if (['已取消', 'rejected', '已拒绝', '待人工'].includes(props.status)) {
    return 'tone-danger'
  }
  return props.status === '已关闭' ? 'tone-neutral' : 'tone-neutral'
})
</script>

<template>
  <span class="status-badge" :class="tone">
    <i />
    {{ status }}
  </span>
</template>
