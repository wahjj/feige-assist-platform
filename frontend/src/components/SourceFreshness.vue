<script setup>
import { computed } from 'vue'

import { shortDate } from '../utils'

const props = defineProps({
  time: { type: String, default: '' },
  label: { type: String, default: '抖店同步' },
})

const text = computed(() =>
  props.time ? `${props.label} · ${shortDate(props.time)}` : `${props.label} · 等待同步`,
)
</script>

<template>
  <span class="source-freshness"><i />{{ text }}</span>
</template>
