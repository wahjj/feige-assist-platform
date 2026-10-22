<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { get } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { shortDate } from '../utils'

const router = useRouter()
const dashboard = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    dashboard.value = await get('/api/dashboard')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="loading-state">正在读取只读镜像数据…</div>
  <div v-else class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">FEIGE ASSIST · READ ONLY</p>
        <h1>给客服更专业的回答，<br />不打断飞鸽原生接待。</h1>
        <p>中台只收消息、看数据、给建议。所有业务和回复仍在飞鸽/抖店完成。</p>
      </div>
      <button class="button button-primary" type="button" @click="router.push('/conversations')">
        进入会话中心 <Icon name="arrow" :size="17" />
      </button>
    </section>

    <div class="readonly-banner">
      <span class="readonly-mark"><Icon name="approval" :size="17" /></span>
      <div><strong>只读镜像模式</strong><p>商品、订单和会话来自抖店；中台没有发送消息、修改订单或接管会话的能力。</p></div>
      <span class="source-refresh">最近同步 {{ shortDate(dashboard.last_webhook_at) }}</span>
    </div>

    <section class="stats-grid">
      <article class="stat-card">
        <div class="stat-icon stat-green"><Icon name="chat" :size="21" /></div>
        <div class="stat-copy"><span>今日同步消息</span><strong>{{ dashboard.messages_today }}</strong><em>来自飞鸽 Webhook</em></div>
      </article>
      <article class="stat-card">
        <div class="stat-icon stat-sand"><Icon name="product" :size="21" /></div>
        <div class="stat-copy"><span>商品 / SKU</span><strong>{{ dashboard.products }} / {{ dashboard.skus }}</strong><em>抖店单向同步</em></div>
      </article>
      <article class="stat-card">
        <div class="stat-icon stat-rose"><Icon name="order" :size="21" /></div>
        <div class="stat-copy"><span>订单镜像</span><strong>{{ dashboard.orders }}</strong><em>业务以抖店为准</em></div>
      </article>
      <article class="stat-card">
        <div class="stat-icon stat-blue"><Icon name="customer" :size="21" /></div>
        <div class="stat-copy"><span>活跃会话</span><strong>{{ dashboard.active_conversations }}</strong><em>飞鸽负责接待</em></div>
      </article>
    </section>

    <section class="dashboard-bottom">
      <article class="panel table-panel recent-readonly-panel">
        <div class="panel-heading">
          <div><span class="panel-kicker">LIVE MIRROR</span><h2>最近会话</h2></div>
          <button class="text-link" type="button" @click="router.push('/conversations')">查看全部 <Icon name="arrow" :size="16" /></button>
        </div>
        <button
          v-for="conversation in dashboard.recent_conversations"
          :key="conversation.id"
          type="button"
          class="conversation-preview wider"
          @click="router.push({ name: 'conversations', query: { c: conversation.id } })"
        >
          <span class="chat-avatar">{{ conversation.customer_name.slice(-2) }}</span>
          <span class="chat-preview-copy">
            <span><strong>{{ conversation.customer_name }}</strong><small>{{ shortDate(conversation.updated_at) }}</small></span>
            <p>{{ conversation.subject }} · {{ conversation.last_message }}</p>
          </span>
          <StatusBadge :status="conversation.state" />
        </button>
      </article>

      <article class="panel assist-kpis">
        <div class="panel-heading"><div><span class="panel-kicker">AI ASSIST</span><h2>辅助状态</h2></div></div>
        <div class="assist-status-row">
          <span class="status-orb" :class="{ ready: dashboard.model_configured }" />
          <div><strong>{{ dashboard.model_configured ? '模型已连接' : '等待配置模型' }}</strong><small>{{ dashboard.model_configured ? '新消息将自动生成一次建议' : '前往同步与设置填写真实模型' }}</small></div>
        </div>
        <div class="assist-status-row">
          <span class="status-orb ready" />
          <div><strong>飞鸽通道模拟连接</strong><small>{{ dashboard.connection?.shop_name }}</small></div>
        </div>
        <button class="soft-action large" type="button" @click="router.push('/sync')">查看同步状态</button>
      </article>
    </section>
  </div>
</template>
