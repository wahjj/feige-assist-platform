<script setup>
import { computed, onMounted, ref } from 'vue'

import { get } from '../api'
import Icon from '../components/Icon.vue'
import SourceFreshness from '../components/SourceFreshness.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { fullDate, money, shortDate } from '../utils'

const orders = ref([])
const query = ref('')
const filter = ref('')
const selected = ref(null)
const loading = ref(true)
const statuses = ['待付款', '待发货', '已发货', '已完成', '已取消']

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return orders.value.filter((order) => {
    const match = !keyword || order.order_no.toLowerCase().includes(keyword) ||
      order.customer_name.toLowerCase().includes(keyword)
    return match && (!filter.value || order.status === filter.value)
  })
})

const counts = computed(() =>
  statuses.reduce((result, status) => ({
    ...result,
    [status]: orders.value.filter((order) => order.status === status).length,
  }), {}),
)

async function load() {
  loading.value = true
  try {
    orders.value = await get('/api/orders')
  } finally {
    loading.value = false
  }
}

async function openOrder(order) {
  selected.value = await get(`/api/orders/${order.id}`)
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div><p class="eyebrow dark">ORDER MIRROR</p><h1>订单查询</h1><p>查询订单、物流和售后状态，所有业务操作仍在抖店完成。</p></div>
      <div class="heading-side-note"><span class="live-dot" /> 抖店同步 · 只读</div>
    </section>

    <div class="readonly-banner">
      <span class="readonly-mark"><Icon name="order" :size="17" /></span>
      <div><strong>订单和物流以抖店后台为准</strong><p>中台不提供发货、退款、补偿、改地址或修改订单状态的入口。</p></div>
      <SourceFreshness :time="orders[0]?.synced_at" />
    </div>

    <section class="order-summary-row">
      <button v-for="status in statuses.slice(0, 4)" :key="status" type="button" class="order-summary-card" :class="{ active: filter === status }" @click="filter = filter === status ? '' : status">
        <span><i class="order-dot" />{{ status }}</span><strong>{{ counts[status] || 0 }}</strong><small>查看订单</small>
      </button>
    </section>

    <section class="panel">
      <div class="toolbar">
        <label class="search-box"><Icon name="search" :size="18" /><input v-model="query" placeholder="搜索订单号或客户" /></label>
        <div class="toolbar-right">
          <select v-model="filter" class="select-control"><option value="">全部状态</option><option v-for="status in statuses" :key="status">{{ status }}</option></select>
          <button class="button button-ghost" type="button" @click="load"><Icon name="refresh" :size="17" /> 刷新</button>
        </div>
      </div>
      <div v-if="loading" class="loading-state">正在加载订单镜像…</div>
      <div v-else class="data-table-wrap">
        <table class="data-table">
          <thead><tr><th>订单编号</th><th>客户</th><th>商品</th><th>订单金额</th><th>物流</th><th>售后</th><th>状态</th><th>下单时间</th><th /></tr></thead>
          <tbody>
            <tr v-for="order in filtered" :key="order.id">
              <td><strong class="order-code">{{ order.order_no }}</strong></td>
              <td><strong>{{ order.customer_name }}</strong></td>
              <td>{{ order.item_count }} 件</td>
              <td><strong>{{ money(order.amount_cents) }}</strong></td>
              <td>{{ order.logistics_status }}</td>
              <td>{{ order.after_sales_status }}</td>
              <td><StatusBadge :status="order.status" /></td>
              <td class="muted">{{ shortDate(order.created_at) }}</td>
              <td><button class="row-link" type="button" @click="openOrder(order)">详情</button></td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filtered.length" class="empty-state">没有符合条件的订单。</div>
      </div>
    </section>

    <div v-if="selected" class="drawer-backdrop" @click.self="selected = null">
      <aside class="detail-drawer order-drawer">
        <div class="drawer-head"><div><span class="panel-kicker">READONLY ORDER</span><h2>{{ selected.order_no }}</h2></div><button class="close-button" type="button" @click="selected = null">×</button></div>
        <div class="order-hero"><div><small>订单金额</small><strong>{{ money(selected.amount_cents) }}</strong></div><StatusBadge :status="selected.status" /></div>

        <div class="detail-section">
          <div class="section-title"><h3>商品明细</h3><span>共 {{ selected.items.length }} 项</span></div>
          <div v-for="item in selected.items" :key="item.id" class="item-line">
            <span class="item-emoji">👗</span>
            <div><strong>{{ item.product_name }}</strong><small>{{ item.sku_name }} · ×{{ item.quantity }}</small></div>
            <strong>{{ money(item.unit_price_cents * item.quantity) }}</strong>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title"><h3>客户与收货</h3></div>
          <div class="info-grid">
            <div><small>客户</small><strong>{{ selected.customer_name }}</strong></div>
            <div><small>订单时间</small><strong>{{ fullDate(selected.created_at) }}</strong></div>
            <div><small>售后状态</small><strong>{{ selected.after_sales_status }}</strong></div>
            <div><small>同步时间</small><strong>{{ fullDate(selected.synced_at) }}</strong></div>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title"><h3>物流状态</h3><span>以抖店为准</span></div>
          <div class="logistics-box"><div class="truck-mark">↗</div><div><strong>{{ selected.logistics_status }}</strong><p>中台仅展示同步副本，不执行发货或物流修改。</p></div></div>
        </div>

        <div class="readonly-drawer-note">此页面只读。需要处理订单请前往抖店后台或飞鸽工作台。</div>
      </aside>
    </div>
  </div>
</template>
