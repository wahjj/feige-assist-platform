<script setup>
import { computed, onMounted, ref } from 'vue'

import { get, post } from '../api'
import StatusBadge from '../components/StatusBadge.vue'
import { money, shortDate } from '../utils'

const approvals = ref([])
const selected = ref(null)
const filter = ref('pending')
const note = ref('')
const loading = ref(true)
const working = ref(false)

const filtered = computed(() =>
  approvals.value.filter((item) => !filter.value || item.status === filter.value),
)
const pendingCount = computed(() => approvals.value.filter((item) => item.status === 'pending').length)

async function load() {
  loading.value = true
  try {
    approvals.value = await get('/api/approvals')
    if (selected.value) {
      selected.value = approvals.value.find((item) => item.id === selected.value.id) || null
    } else {
      selected.value = filtered.value[0] || approvals.value[0] || null
    }
  } finally {
    loading.value = false
  }
}

async function decide(decision) {
  if (!selected.value) return
  working.value = true
  try {
    selected.value = await post(`/api/approvals/${selected.value.id}/decision`, {
      decision,
      note: note.value,
    })
    note.value = ''
    await load()
  } finally {
    working.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">AFTER SALES</p>
        <h1>售后审批</h1>
        <p>所有涉及成本的售后动作，都需要在这里被看见。</p>
      </div>
      <div class="approval-alert"><span>{{ pendingCount }}</span><div><strong>项等待处理</strong><small>建议优先处理等待最久的申请</small></div></div>
    </section>

    <section class="approval-layout">
      <article class="panel approval-list">
        <div class="toolbar compact">
          <div class="segmented compact">
            <button :class="{ active: filter === 'pending' }" type="button" @click="filter = 'pending'">待处理</button>
            <button :class="{ active: filter === 'approved' }" type="button" @click="filter = 'approved'">已通过</button>
            <button :class="{ active: filter === '' }" type="button" @click="filter = ''">全部</button>
          </div>
        </div>
        <div v-if="loading" class="loading-state">正在加载审批…</div>
        <button
          v-for="approval in filtered"
          :key="approval.id"
          class="approval-row"
          :class="{ active: selected?.id === approval.id }"
          type="button"
          @click="selected = approval"
        >
          <span class="approval-type">{{ approval.action_type.slice(0, 1) }}</span>
          <span class="approval-copy">
            <span><strong>{{ approval.action_type }}</strong><StatusBadge :status="approval.status" /></span>
            <p>{{ approval.reason }}</p>
            <small>{{ approval.customer_name }} · {{ approval.order_no }} · {{ shortDate(approval.created_at) }}</small>
          </span>
          <strong>{{ money(approval.amount_cents) }}</strong>
        </button>
        <div v-if="!filtered.length && !loading" class="empty-state">当前没有相关审批。</div>
      </article>

      <article v-if="selected" class="panel approval-detail">
        <div class="approval-detail-head">
          <div>
            <span class="panel-kicker">APPROVAL REQUEST</span>
            <h2>{{ selected.action_type }}</h2>
          </div>
          <StatusBadge :status="selected.status" />
        </div>
        <div class="approval-amount">
          <span>建议金额</span>
          <strong>{{ money(selected.amount_cents) }}</strong>
          <small>{{ selected.customer_name }} · {{ selected.order_no }}</small>
        </div>
        <div class="detail-section">
          <div class="section-title"><h3>AI 建议理由</h3><span>需人工确认</span></div>
          <p class="quote-box">{{ selected.reason }}</p>
        </div>
        <div class="detail-section">
          <div class="section-title"><h3>核验证据</h3></div>
          <div class="evidence-card">
            <span>物流状态</span>
            <strong>{{ selected.logistics_status }}</strong>
            <p>{{ selected.evidence }}</p>
          </div>
        </div>
        <div class="detail-section">
          <div class="section-title"><h3>审批备注</h3></div>
          <textarea v-model="note" class="soft-textarea" rows="3" placeholder="记录判断依据，便于后续追溯" :disabled="selected.status !== 'pending'" />
        </div>
        <div v-if="selected.status === 'pending'" class="approval-actions">
          <button class="button button-ghost" type="button" :disabled="working" @click="decide('reject')">拒绝申请</button>
          <button class="button button-primary" type="button" :disabled="working" @click="decide('approve')">通过并记录</button>
        </div>
        <div v-else class="decision-note">
          审批已处理 {{ selected.note ? `· ${selected.note}` : '' }}
        </div>
      </article>
    </section>
  </div>
</template>
