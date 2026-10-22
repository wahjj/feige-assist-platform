<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { get } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { initials, money, shortDate } from '../utils'

const router = useRouter()
const dashboard = ref(null)
const conversations = ref([])
const loading = ref(true)

const chartPoints = computed(() => {
  const values = dashboard.value?.sales_trend || []
  if (!values.length) return ''
  const max = Math.max(...values.map((item) => item.value))
  return values
    .map((item, index) => {
      const x = 12 + (index * 276) / Math.max(values.length - 1, 1)
      const y = 104 - (item.value / max) * 78
      return `${x},${y}`
    })
    .join(' ')
})

const stats = computed(() => {
  if (!dashboard.value) return []
  return [
    {
      label: '累计成交额',
      value: money(dashboard.value.revenue_cents),
      delta: '+18.4%',
      icon: 'order',
      tone: 'green',
    },
    {
      label: '订单总数',
      value: dashboard.value.order_count,
      delta: '+6 今日',
      icon: 'order',
      tone: 'sand',
    },
    {
      label: '客户资产',
      value: dashboard.value.customer_count,
      delta: '3 位高复购',
      icon: 'customer',
      tone: 'rose',
    },
    {
      label: '待处理事项',
      value: dashboard.value.pending_approval_count + dashboard.value.active_conversation_count,
      delta: '客服与审批',
      icon: 'approval',
      tone: 'blue',
    },
  ]
})

onMounted(async () => {
  try {
    const [dashboardData, chatData] = await Promise.all([
      get('/api/dashboard'),
      get('/api/conversations'),
    ])
    dashboard.value = dashboardData
    conversations.value = chatData.slice(0, 3)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="loading-state">正在整理店铺数据…</div>
  <div v-else class="dashboard-page">
    <section class="page-heading dashboard-heading">
      <div>
        <p class="eyebrow dark">THURSDAY, 22 OCTOBER</p>
        <h1>早上好，今天也照顾好每一份期待。</h1>
        <p>店铺整体运转平稳，有 3 项客服事项需要你关注。</p>
      </div>
      <button class="button button-primary" type="button" @click="router.push('/products')">
        <Icon name="plus" :size="18" />
        新增商品
      </button>
    </section>

    <section class="stats-grid">
      <article v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :class="`stat-${stat.tone}`"><Icon :name="stat.icon" :size="21" /></div>
        <div class="stat-copy">
          <span>{{ stat.label }}</span>
          <strong>{{ stat.value }}</strong>
          <em>{{ stat.delta }}</em>
        </div>
      </article>
    </section>

    <section class="dashboard-grid">
      <article class="panel revenue-panel">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">销售走势</span>
            <h2>近 7 日成交</h2>
          </div>
          <div class="period-switch">
            <button class="active">7 天</button>
            <button>30 天</button>
          </div>
        </div>
        <div class="revenue-highlight">
          <div>
            <small>当前周期总收入</small>
            <strong>{{ money(21070) }}</strong>
          </div>
          <span class="trend-up">↗ 12.6% 较上期</span>
        </div>
        <div class="chart-wrap">
          <div class="chart-lines"><i /><i /><i /><i /></div>
          <svg viewBox="0 0 300 116" preserveAspectRatio="none" class="sales-chart">
            <defs>
              <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#486b58" stop-opacity=".28" />
                <stop offset="100%" stop-color="#486b58" stop-opacity="0" />
              </linearGradient>
            </defs>
            <polygon :points="`12,112 ${chartPoints} 288,112`" fill="url(#chartFill)" />
            <polyline :points="chartPoints" fill="none" stroke="#355646" stroke-width="2.5" stroke-linecap="round" />
          </svg>
          <div class="chart-labels">
            <span v-for="item in dashboard.sales_trend" :key="item.label">{{ item.label }}</span>
          </div>
        </div>
      </article>

      <article class="panel notice-panel">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">需要你</span>
            <h2>待处理事项</h2>
          </div>
          <span class="round-count">3</span>
        </div>
        <button class="notice-item urgent" type="button" @click="router.push('/approvals')">
          <span class="notice-icon">!</span>
          <span><strong>物流补偿待审批</strong><small>林予安 · 等待 18 分钟</small></span>
          <Icon name="arrow" :size="17" />
        </button>
        <button class="notice-item" type="button" @click="router.push('/service')">
          <span class="notice-icon soft">✦</span>
          <span><strong>AI 已转接 2 个会话</strong><small>需要人工继续跟进</small></span>
          <Icon name="arrow" :size="17" />
        </button>
        <button class="notice-item" type="button" @click="router.push('/products')">
          <span class="notice-icon soft">↓</span>
          <span><strong>2 件商品库存偏低</strong><small>轻羽托特包等</small></span>
          <Icon name="arrow" :size="17" />
        </button>
        <div class="suggestion">
          <span>今日建议</span>
          <p>香氛与礼盒类商品最近 7 天复购率上升，可在客服话术中优先推荐。</p>
        </div>
      </article>
    </section>

    <section class="dashboard-bottom">
      <article class="panel table-panel">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">最新动态</span>
            <h2>最近订单</h2>
          </div>
          <button class="text-link" type="button" @click="router.push('/orders')">
            查看全部 <Icon name="arrow" :size="16" />
          </button>
        </div>
        <div class="data-table-wrap">
          <table class="data-table">
            <thead>
              <tr><th>订单</th><th>客户</th><th>金额</th><th>状态</th><th>时间</th></tr>
            </thead>
            <tbody>
              <tr v-for="order in dashboard.recent_orders" :key="order.id">
                <td><strong class="order-code">{{ order.order_no }}</strong></td>
                <td>
                  <div class="person-cell">
                    <span class="mini-avatar">{{ initials(order.customer_name) }}</span>
                    {{ order.customer_name }}
                  </div>
                </td>
                <td>{{ money(order.total_cents) }}</td>
                <td><StatusBadge :status="order.status" /></td>
                <td class="muted">{{ shortDate(order.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="panel chat-preview-panel">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">客服工作台</span>
            <h2>正在发生</h2>
          </div>
          <button class="text-link" type="button" @click="router.push('/service')">进入工作台</button>
        </div>
        <button
          v-for="conversation in conversations"
          :key="conversation.id"
          type="button"
          class="conversation-preview"
          @click="router.push({ name: 'service', query: { c: conversation.id } })"
        >
          <span class="chat-avatar">{{ initials(conversation.customer_name) }}</span>
          <span class="chat-preview-copy">
            <span><strong>{{ conversation.customer_name }}</strong><small>{{ shortDate(conversation.updated_at) }}</small></span>
            <p>{{ conversation.last_message }}</p>
          </span>
          <StatusBadge :status="conversation.status" />
        </button>
      </article>
    </section>
  </div>
</template>
