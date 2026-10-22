<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import { get, post } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { shortDate } from '../utils'

const conversationId = ref('')
const status = ref('AI处理中')
const messages = ref([])
const text = ref('')
const sending = ref(false)
const streamRef = ref(null)
let pollTimer

const suggestions = ['物流三天没更新', '订单可以开发票吗？', '我要申请补偿', '请帮我转人工']

async function scrollToBottom() {
  await nextTick()
  if (streamRef.value) {
    streamRef.value.scrollTop = streamRef.value.scrollHeight
  }
}

async function loadMessages() {
  if (!conversationId.value) return
  const payload = await get(`/api/public/chat/${conversationId.value}`)
  status.value = payload.status
  messages.value = payload.messages
  await scrollToBottom()
}

async function sendMessage(value = text.value) {
  const content = value.trim()
  if (!content || sending.value) return
  sending.value = true
  text.value = ''
  try {
    messages.value.push({ role: 'customer', text: content, created_at: new Date().toISOString() })
    await scrollToBottom()
    const result = await post(`/api/public/chat/${conversationId.value}/messages`, { text: content })
    status.value = result.status
    messages.value.push({ role: 'ai', text: result.reply, created_at: new Date().toISOString() })
    await scrollToBottom()
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  const started = await post('/api/public/chat/start')
  conversationId.value = started.conversation_id
  await loadMessages()
  pollTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') loadMessages()
  }, 5000)
})

onBeforeUnmount(() => window.clearInterval(pollTimer))
</script>

<template>
  <main class="consumer-chat-page">
    <section class="consumer-chat-shell">
      <header class="consumer-chat-head">
        <div class="consumer-brand">
          <div class="brand-mark">禾</div>
          <div><strong>禾光生活研究所</strong><span>把日常过得更有质感</span></div>
        </div>
        <div class="consumer-status"><span class="live-dot" />在线 · <StatusBadge :status="status" /></div>
      </header>

      <div ref="streamRef" class="consumer-messages">
        <div class="consumer-ai-intro">
          <div class="ai-orb">✦</div>
          <h1>你好，我是禾光客服小禾</h1>
          <p>可以帮你查询订单、物流和商品信息。涉及退款或补偿时，会提交商家审核。</p>
        </div>
        <div v-for="(message, index) in messages" :key="`${message.created_at}-${index}`" class="consumer-message-row" :class="message.role">
          <div v-if="message.role !== 'customer'" class="consumer-ai-avatar">禾</div>
          <div class="consumer-bubble-wrap">
            <span>{{ message.role === 'customer' ? '我' : message.role === 'ai' ? 'AI 客服小禾' : '店铺客服' }}</span>
            <div class="consumer-bubble">{{ message.text }}</div>
            <small>{{ shortDate(message.created_at) }}</small>
          </div>
        </div>
      </div>

      <div class="quick-replies">
        <button v-for="suggestion in suggestions" :key="suggestion" type="button" @click="sendMessage(suggestion)">
          {{ suggestion }}
        </button>
      </div>

      <form class="consumer-composer" @submit.prevent="sendMessage()">
        <textarea v-model="text" rows="2" placeholder="输入你的问题…" />
        <button type="submit" :disabled="sending || !text.trim()">
          <Icon name="send" :size="19" />
        </button>
      </form>
      <footer class="consumer-footer">
        <span>安全提示：请勿发送银行卡、密码等敏感信息</span>
        <router-link to="/login">商家入口</router-link>
      </footer>
    </section>
    <aside class="consumer-side-card">
      <p class="eyebrow">LIVE DEMO</p>
      <h2>这是一段可操作的客服体验。</h2>
      <p>发送一条消息，看看 AI 如何查询业务信息、生成回复，以及何时转交人工。</p>
      <div class="demo-flow">
        <span><i>1</i>消费者发起咨询</span>
        <span><i>2</i>AI 分析并回复</span>
        <span><i>3</i>售后或风险转人工</span>
      </div>
      <router-link class="button button-light" to="/service">查看商家工作台 →</router-link>
    </aside>
  </main>
</template>
