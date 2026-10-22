<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { get, post } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { initials, money, shortDate } from '../utils'

const route = useRoute()
const router = useRouter()
const conversations = ref([])
const detail = ref(null)
const selectedId = ref('')
const loading = ref(true)
const replyText = ref('')
const sending = ref(false)
const notice = ref('')
let pollTimer

const grouped = computed(() => ({
  needing: conversations.value.filter((item) => ['待人工', 'human'].includes(item.status)),
  active: conversations.value.filter((item) => item.status === 'AI处理中'),
  closed: conversations.value.filter((item) => item.status === '已结束'),
}))

async function loadList() {
  conversations.value = await get('/api/conversations')
  if (!selectedId.value && conversations.value.length) {
    selectedId.value = String(route.query.c || conversations.value[0].id)
  }
}

async function loadDetail(silent = false) {
  if (!selectedId.value) return
  if (!silent) loading.value = true
  try {
    detail.value = await get(`/api/conversations/${selectedId.value}`)
  } finally {
    loading.value = false
  }
}

async function selectConversation(conversation) {
  selectedId.value = conversation.id
  await router.replace({ name: 'service', query: { c: conversation.id } })
  await loadDetail()
}

async function takeover() {
  await post(`/api/conversations/${selectedId.value}/takeover`)
  notice.value = '已接管会话，AI 自动回复已暂停'
  await Promise.all([loadList(), loadDetail(true)])
  window.setTimeout(() => (notice.value = ''), 2600)
}

async function sendReply() {
  if (!replyText.value.trim()) return
  sending.value = true
  try {
    await post(`/api/conversations/${selectedId.value}/messages`, {
      text: replyText.value.trim(),
      role: 'human',
    })
    replyText.value = ''
    await Promise.all([loadList(), loadDetail(true)])
  } finally {
    sending.value = false
  }
}

watch(selectedId, () => loadDetail())

onMounted(async () => {
  await loadList()
  await loadDetail()
  pollTimer = window.setInterval(async () => {
    if (document.visibilityState === 'visible') {
      await loadDetail(true)
    }
  }, 5000)
})

onBeforeUnmount(() => window.clearInterval(pollTimer))
</script>

<template>
  <div class="service-page">
    <section class="page-heading service-heading">
      <div>
        <p class="eyebrow dark">SERVICE DESK</p>
        <h1>客服工作台</h1>
        <p>AI 先接待，你只需要在关键时刻出现。</p>
      </div>
      <div class="service-heading-actions">
        <span class="online-pill"><i /> AI 客服在线</span>
        <router-link class="button button-primary" to="/chat" target="_blank">
          打开客户咨询演示 <Icon name="arrow" :size="17" />
        </router-link>
      </div>
    </section>

    <div v-if="notice" class="toast-success">{{ notice }}</div>

    <section class="service-layout panel">
      <aside class="conversation-column">
        <div class="conversation-head">
          <div><strong>全部会话</strong><span>{{ conversations.length }}</span></div>
          <button class="icon-button small" type="button" @click="loadList"><Icon name="refresh" :size="16" /></button>
        </div>
        <div class="conversation-scroll">
          <template v-for="group in [{ label: '待处理', items: grouped.needing }, { label: 'AI 正在接待', items: grouped.active }, { label: '已结束', items: grouped.closed }]" :key="group.label">
            <div v-if="group.items.length" class="conversation-group-label">{{ group.label }} · {{ group.items.length }}</div>
            <button
              v-for="conversation in group.items"
              :key="conversation.id"
              type="button"
              class="conversation-item"
              :class="{ active: selectedId === conversation.id }"
              @click="selectConversation(conversation)"
            >
              <span class="chat-avatar">{{ initials(conversation.customer_name) }}</span>
              <span class="conversation-item-copy">
                <span><strong>{{ conversation.customer_name }}</strong><small>{{ shortDate(conversation.updated_at) }}</small></span>
                <span>{{ conversation.last_message }}</span>
                <em>{{ conversation.subject }}</em>
              </span>
              <i v-if="conversation.unread">{{ conversation.unread }}</i>
            </button>
          </template>
        </div>
      </aside>

      <section v-if="detail" class="chat-column">
        <div class="chat-head">
          <div class="chat-person">
            <span class="large-avatar">{{ initials(detail.customer_name) }}</span>
            <div>
              <div><strong>{{ detail.customer_name }}</strong><StatusBadge :status="detail.status" /></div>
              <span>{{ detail.customer_phone }} · {{ detail.customer_tags.join(' / ') }}</span>
            </div>
          </div>
          <div class="chat-head-actions">
            <span class="ai-state" :class="{ off: detail.status === 'human' }"><i />{{ detail.status === 'human' ? '人工处理中' : 'AI 自动接待' }}</span>
            <button v-if="detail.status !== 'human'" class="button button-ghost button-small" type="button" @click="takeover">接管会话</button>
            <button class="icon-button small" type="button" @click="loadDetail()"><Icon name="refresh" :size="17" /></button>
          </div>
        </div>

        <div class="message-stream">
          <div class="message-day">今天</div>
          <div v-for="message in detail.messages" :key="message.id" class="message-row" :class="message.role">
            <span v-if="message.role !== 'customer'" class="message-avatar">{{ message.role === 'ai' ? 'AI' : '管' }}</span>
            <div class="message-bubble-wrap">
              <span class="message-author">{{ message.role === 'customer' ? detail.customer_name : message.role === 'ai' ? 'AI 客服助手' : '店铺管理员' }}</span>
              <div class="message-bubble">{{ message.text }}</div>
              <small>{{ shortDate(message.created_at) }}</small>
            </div>
            <span v-if="message.role === 'customer'" class="message-avatar customer">{{ initials(detail.customer_name).slice(-1) }}</span>
          </div>
          <div v-if="detail.status === '待人工'" class="handoff-banner">
            <span>!</span>
            <div><strong>等待人工接管</strong><p>AI 已完成初步答复，消费者需要进一步协助。</p></div>
          </div>
        </div>

        <div class="reply-composer">
          <textarea
            v-model="replyText"
            rows="2"
            :placeholder="detail.status === 'human' ? '输入要发送给客户的消息…' : '接管会话后可发送人工消息'"
            :disabled="detail.status !== 'human' || sending"
            @keydown.enter.exact.prevent="sendReply"
          />
          <div class="composer-foot">
            <span>{{ detail.status === 'human' ? 'Enter 发送 · 发送后 AI 将保持暂停' : '点击右上角“接管会话”开始人工回复' }}</span>
            <button class="send-button" type="button" :disabled="detail.status !== 'human' || sending || !replyText.trim()" @click="sendReply">
              <Icon name="send" :size="17" /> {{ sending ? '发送中' : '发送' }}
            </button>
          </div>
        </div>
      </section>

      <aside v-if="detail" class="context-column">
        <div class="context-head"><strong>客户与订单</strong><router-link :to="{ name: 'customers' }">客户档案 →</router-link></div>
        <div class="context-card customer-context">
          <div class="context-customer">
            <span class="large-avatar">{{ initials(detail.customer_name) }}</span>
            <div><strong>{{ detail.customer_name }}</strong><span>{{ detail.customer_tags.join(' · ') }}</span></div>
          </div>
          <div class="context-mini-grid">
            <div><span>当前订单</span><strong>{{ detail.order_no || '—' }}</strong></div>
            <div><span>订单金额</span><strong>{{ money(detail.total_cents || 0) }}</strong></div>
          </div>
        </div>
        <div v-if="detail.order_no" class="context-card">
          <span class="panel-kicker">关联订单</span>
          <div class="order-context-title">
            <div><strong>{{ detail.order_no }}</strong><StatusBadge :status="detail.order_status" /></div>
            <span>{{ detail.logistics_status }}</span>
          </div>
          <div class="mini-track"><i class="done" /><i class="done" /><i class="current" /><i /></div>
          <div class="track-labels"><span>已下单</span><span>已揽收</span><span>运输中</span><span>已签收</span></div>
        </div>
        <div class="context-card">
          <span class="panel-kicker">智能提示</span>
          <p class="ai-suggestion">
            客户已等待较长时间，建议先表达理解，再明确说明下一步处理时间。
          </p>
          <button class="soft-action" type="button" @click="replyText = '非常抱歉让您久等了，我来继续帮您跟进这笔订单。'">
            使用建议话术
          </button>
        </div>
        <router-link class="context-card approval-shortcut" to="/approvals">
          <span class="shortcut-mark">!</span>
          <span><strong>售后审批</strong><small>查看退款、补偿与补发申请</small></span>
          <Icon name="arrow" :size="16" />
        </router-link>
      </aside>
    </section>
  </div>
</template>
