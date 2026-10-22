<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { get, post } from '../api'
import AiSuggestionPanel from '../components/AiSuggestionPanel.vue'
import Icon from '../components/Icon.vue'
import ReadonlyTranscript from '../components/ReadonlyTranscript.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { initials, money, shortDate } from '../utils'

const route = useRoute()
const router = useRouter()
const conversations = ref([])
const detail = ref(null)
const customer = ref(null)
const order = ref(null)
const selectedId = ref('')
const activeTab = ref('assistant')
const modelConfigured = ref(false)
const loading = ref(true)
const generating = ref(false)
const suggestionError = ref('')
const notice = ref('')
let timer

const suggestion = computed(() => detail.value?.suggestions?.[0] || null)

function displayStatus(status) {
  return status === '接待中' ? '飞鸽接待中' : status
}

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
    const requests = [get(`/api/customers/${detail.value.customer_id}`)]
    if (detail.value.order_id) requests.push(get(`/api/orders/${detail.value.order_id}`))
    const results = await Promise.all(requests)
    customer.value = results[0]
    order.value = results[1] || null
  } finally {
    loading.value = false
  }
}

async function selectConversation(item) {
  selectedId.value = item.id
  activeTab.value = 'assistant'
  await router.replace({ name: 'conversations', query: { c: item.id } })
}

async function generate() {
  if (!selectedId.value) return
  generating.value = true
  suggestionError.value = ''
  try {
    await post(`/api/conversations/${selectedId.value}/suggestions`)
    await loadDetail(true)
    notice.value = 'AI 建议已重新生成'
    window.setTimeout(() => (notice.value = ''), 2200)
  } catch (err) {
    suggestionError.value = err.message
  } finally {
    generating.value = false
  }
}

async function copySuggestion(text) {
  await navigator.clipboard.writeText(text)
  await post(`/api/suggestions/${suggestion.value.id}/copy`)
  notice.value = '话术已复制，请到飞鸽人工审核后发送'
  await loadDetail(true)
  window.setTimeout(() => (notice.value = ''), 2600)
}

watch(selectedId, () => loadDetail())

onMounted(async () => {
  try {
    const [_, model] = await Promise.all([loadList(), get('/api/settings/model')])
    modelConfigured.value = Boolean(model.configured)
    await loadDetail()
    timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') loadDetail(true)
    }, 5000)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="page-stack conversation-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">FEIGE CONVERSATIONS · READ ONLY</p>
        <h1>会话中心</h1>
        <p>查看飞鸽同步对话，让 AI 帮你准备更专业的参考话术。</p>
      </div>
      <div class="service-heading-actions">
        <span class="online-pill"><i /> 飞鸽原生接待中</span>
        <button class="button button-primary" type="button" @click="router.push('/mock-events')">
          模拟一条消息 <Icon name="plus" :size="17" />
        </button>
      </div>
    </section>

    <div v-if="notice" class="toast-success">{{ notice }}</div>
    <div class="readonly-banner compact-banner">
      <span class="readonly-mark"><Icon name="chat" :size="17" /></span>
      <div><strong>只读消息镜像</strong><p>这里没有回复框，也不会接管飞鸽。AI 内容复制后由客服在飞鸽发送。</p></div>
      <span class="source-refresh">自动刷新 5s</span>
    </div>

    <section class="service-layout readonly-service-layout panel">
      <aside class="conversation-column">
        <div class="conversation-head">
          <div><strong>会话列表</strong><span>{{ conversations.length }}</span></div>
          <button class="icon-button small" type="button" @click="loadList"><Icon name="refresh" :size="15" /></button>
        </div>
        <div class="conversation-scroll">
          <button
            v-for="conversation in conversations"
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
              <em>{{ conversation.completeness === 'complete' ? '完整会话' : '仅买家消息' }}</em>
            </span>
          </button>
        </div>
      </aside>

      <section v-if="detail" class="chat-column readonly-chat-column">
        <div class="chat-head">
          <div class="chat-person">
            <span class="large-avatar">{{ initials(detail.customer_name) }}</span>
            <div>
              <div><strong>{{ detail.customer_name }}</strong><StatusBadge :status="displayStatus(detail.state)" /></div>
              <span>{{ detail.customer_phone_masked }} · {{ detail.completeness === 'complete' ? '完整会话' : '仅同步买家消息' }}</span>
            </div>
          </div>
          <div class="chat-head-actions">
            <span class="ai-state"><i />只读同步</span>
            <button class="icon-button small" type="button" @click="loadDetail()"><Icon name="refresh" :size="16" /></button>
          </div>
        </div>
        <div class="message-stream">
          <ReadonlyTranscript :messages="detail.messages" :customer-name="detail.customer_name" />
        </div>
      </section>

      <aside v-if="detail" class="assist-column">
        <div class="assist-tabs">
          <button :class="{ active: activeTab === 'assistant' }" type="button" @click="activeTab = 'assistant'">AI建议</button>
          <button :class="{ active: activeTab === 'context' }" type="button" @click="activeTab = 'context'">订单商品</button>
          <button :class="{ active: activeTab === 'customer' }" type="button" @click="activeTab = 'customer'">客户</button>
        </div>
        <div class="assist-scroll">
          <AiSuggestionPanel
            v-if="activeTab === 'assistant'"
            :suggestion="suggestion"
            :model-configured="modelConfigured"
            :loading="generating"
            :error="suggestionError"
            @regenerate="generate"
            @copy="copySuggestion"
            @configure="router.push('/sync')"
          />

          <div v-else-if="activeTab === 'context'" class="context-detail">
            <div v-if="order" class="context-card order-context-card">
              <span class="panel-kicker">关联订单</span>
              <div class="order-context-title">
                <div><strong>{{ order.order_no }}</strong><StatusBadge :status="order.status" /></div>
                <span>{{ order.logistics_status }}</span>
              </div>
              <div v-for="item in order.items" :key="item.id" class="compact-order-item">
                <span>🧥</span>
                <div><strong>{{ item.product_name }}</strong><small>{{ item.sku_name }} · ×{{ item.quantity }}</small></div>
                <strong>{{ money(item.unit_price_cents) }}</strong>
              </div>
            </div>
            <div v-else class="ai-empty"><strong>当前会话未关联订单</strong></div>
            <p class="context-footnote">订单和物流状态以抖店后台为准。</p>
          </div>

          <div v-else class="context-detail">
            <div v-if="customer" class="context-card customer-context">
              <div class="context-customer">
                <span class="large-avatar">{{ initials(customer.name) }}</span>
                <div><strong>{{ customer.name }}</strong><span>{{ customer.phone_masked }}</span></div>
              </div>
              <div class="tag-row"><em v-for="tag in customer.tags" :key="tag">{{ tag }}</em></div>
              <p class="customer-note">{{ customer.note || '暂无中台跟进备注' }}</p>
              <div class="context-mini-grid">
                <div><span>历史订单</span><strong>{{ customer.order_count }}</strong></div>
                <div><span>累计消费</span><strong>{{ money(customer.total_spent_cents) }}</strong></div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>
