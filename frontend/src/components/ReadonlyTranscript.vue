<script setup>
import { shortDate } from '../utils'

defineProps({
  messages: { type: Array, default: () => [] },
  customerName: { type: String, default: '买家' },
})

function roleLabel(role) {
  if (role === 'buyer') return '买家'
  if (role === 'service_agent') return '飞鸽客服'
  return '未知角色'
}
</script>

<template>
  <div class="readonly-transcript">
    <div class="transcript-note">
      <span>只读对话</span>
      <p>消息来自飞鸽同步，中台无法在此回复或修改。</p>
    </div>
    <div v-for="message in messages" :key="message.id" class="message-row" :class="message.role">
      <span v-if="message.role !== 'buyer'" class="message-avatar">{{ message.role === 'service_agent' ? '服' : '?' }}</span>
      <div class="message-bubble-wrap">
        <span class="message-author">{{ roleLabel(message.role) }}</span>
        <div class="message-bubble">
          <a v-if="message.message_type === 'image'" :href="message.content" target="_blank" rel="noopener">查看图片消息</a>
          <template v-else>{{ message.content }}</template>
        </div>
        <small>{{ shortDate(message.sent_at) }}</small>
      </div>
      <span v-if="message.role === 'buyer'" class="message-avatar customer">{{ customerName.slice(-1) }}</span>
    </div>
    <div v-if="!messages.length" class="empty-state">会话中暂时没有消息。</div>
  </div>
</template>
