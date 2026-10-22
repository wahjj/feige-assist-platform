<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { get, put } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { initials, money, shortDate } from '../utils'

const router = useRouter()
const customers = ref([])
const query = ref('')
const selected = ref(null)
const loading = ref(true)
const edit = reactive({ tags: '', note: '' })
const saving = ref(false)
const notice = ref('')

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return customers.value.filter(
    (customer) =>
      !keyword ||
      customer.name.toLowerCase().includes(keyword) ||
      customer.phone.includes(keyword) ||
      customer.tags.some((tag) => tag.toLowerCase().includes(keyword)),
  )
})

const totalValue = computed(() =>
  customers.value.reduce((sum, customer) => sum + customer.total_spent_cents, 0),
)

async function load() {
  loading.value = true
  try {
    customers.value = await get('/api/customers')
  } finally {
    loading.value = false
  }
}

async function openCustomer(customer) {
  selected.value = await get(`/api/customers/${customer.id}`)
  edit.tags = selected.value.tags.join('、')
  edit.note = selected.value.note
}

async function saveCustomer() {
  saving.value = true
  try {
    await put(`/api/customers/${selected.value.id}`, {
      tags: edit.tags.split(/[、,，]/).map((tag) => tag.trim()).filter(Boolean),
      note: edit.note,
    })
    selected.value = await get(`/api/customers/${selected.value.id}`)
    notice.value = '客户资料已保存'
    await load()
    window.setTimeout(() => (notice.value = ''), 2400)
  } finally {
    saving.value = false
  }
}

function openConversation(conversation) {
  router.push({ name: 'service', query: { c: conversation.id } })
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">CUSTOMERS</p>
        <h1>客户管理</h1>
        <p>理解客户偏好，把每一次成交沉淀成长期关系。</p>
      </div>
      <div class="heading-side-note">
        当前客户资产 <strong>{{ money(totalValue) }}</strong>
      </div>
    </section>

    <div v-if="notice" class="toast-success">{{ notice }}</div>

    <section class="customer-layout">
      <article class="panel customer-list-panel">
        <div class="toolbar compact">
          <label class="search-box">
            <Icon name="search" :size="18" />
            <input v-model="query" placeholder="搜索姓名、手机号或标签" />
          </label>
          <span class="soft-tag">{{ filtered.length }} 位客户</span>
        </div>
        <div v-if="loading" class="loading-state">正在加载客户…</div>
        <button
          v-for="customer in filtered"
          :key="customer.id"
          type="button"
          class="customer-row"
          :class="{ selected: selected?.id === customer.id }"
          @click="openCustomer(customer)"
        >
          <span class="large-avatar">{{ initials(customer.name) }}</span>
          <span class="customer-main">
            <span><strong>{{ customer.name }}</strong><small>{{ customer.phone_masked }}</small></span>
            <span class="tag-row"><em v-for="tag in customer.tags" :key="tag">{{ tag }}</em></span>
          </span>
          <span class="customer-numbers">
            <strong>{{ money(customer.total_spent_cents) }}</strong>
            <small>{{ customer.order_count }} 笔订单</small>
          </span>
          <span class="chevron">›</span>
        </button>
        <div v-if="!filtered.length && !loading" class="empty-state">没有找到客户。</div>
      </article>

      <aside class="customer-insight">
        <div v-if="!selected" class="insight-empty">
          <span class="insight-symbol">◌</span>
          <h3>选择一位客户</h3>
          <p>查看客户偏好、历史订单和客服会话。</p>
        </div>
        <template v-else>
          <div class="customer-profile">
            <div class="profile-avatar">{{ initials(selected.name) }}</div>
            <div>
              <h2>{{ selected.name }}</h2>
              <p>{{ selected.phone }} · {{ selected.source }}</p>
            </div>
            <span class="customer-tier">优选客户</span>
          </div>
          <div class="profile-metrics">
            <div><strong>{{ selected.order_count }}</strong><span>有效订单</span></div>
            <div><strong>{{ money(selected.total_spent_cents) }}</strong><span>累计消费</span></div>
          </div>
          <div class="detail-section">
            <div class="section-title"><h3>客户标签</h3></div>
            <label class="field"><input v-model="edit.tags" placeholder="用顿号分隔标签" /></label>
          </div>
          <div class="detail-section">
            <div class="section-title"><h3>内部备注</h3></div>
            <textarea v-model="edit.note" class="soft-textarea" rows="4" />
            <button class="button button-primary button-small" :disabled="saving" type="button" @click="saveCustomer">
              {{ saving ? '保存中…' : '保存客户资料' }}
            </button>
          </div>
          <div class="detail-section">
            <div class="section-title"><h3>最近订单</h3><span>{{ selected.orders.length }} 笔</span></div>
            <button v-for="order in selected.orders.slice(0, 4)" :key="order.id" class="compact-row" type="button" @click="router.push('/orders')">
              <span><strong>{{ order.order_no }}</strong><small>{{ shortDate(order.created_at) }}</small></span>
              <span>{{ money(order.total_cents) }}</span>
              <StatusBadge :status="order.status" />
            </button>
          </div>
          <div class="detail-section">
            <div class="section-title"><h3>客服会话</h3><span>{{ selected.conversations.length }} 段</span></div>
            <button v-for="conversation in selected.conversations" :key="conversation.id" class="compact-row conversation-row" type="button" @click="openConversation(conversation)">
              <span><strong>{{ conversation.subject }}</strong><small>{{ conversation.last_message }}</small></span>
              <StatusBadge :status="conversation.status" />
            </button>
            <p v-if="!selected.conversations.length" class="muted empty-copy">暂无客服会话。</p>
          </div>
        </template>
      </aside>
    </section>
  </div>
</template>
