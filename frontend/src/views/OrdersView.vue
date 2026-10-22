<script setup>
import { computed, onMounted, ref } from 'vue'

import { get, patch } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { fullDate, money, shortDate } from '../utils'

const orders = ref([])
const query = ref('')
const filter = ref('')
const selected = ref(null)
const loading = ref(true)
const updating = ref(false)

const statuses = ['待付款', '待发货', '已发货', '已完成', '已取消']

const counts = computed(() =>
  statuses.reduce(
    (result, status) => ({
      ...result,
      [status]: orders.value.filter((order) => order.status === status).length,
    }),
    {},
  ),
)

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return orders.value.filter((order) => {
    const matchesKeyword =
      !keyword ||
      order.order_no.toLowerCase().includes(keyword) ||
      order.customer_name.toLowerCase().includes(keyword)
    return matchesKeyword && (!filter.value || order.status === filter.value)
  })
})

async function load() {
  loading.value = true
  try {
    orders.value = await get('/api/orders')
    if (selected.value) {
      selected.value = await get(`/api/orders/${selected.value.id}`)
    }
  } finally {
    loading.value = false
  }
}

async function openOrder(order) {
  selected.value = await get(`/api/orders/${order.id}`)
}

async function changeStatus(status) {
  if (!selected.value || status === selected.value.status) return
  updating.value = true
  try {
    await patch(`/api/orders/${selected.value.id}/status`, { status })
    selected.value = await get(`/api/orders/${selected.value.id}`)
    await load()
  } finally {
    updating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">ORDERS</p>
        <h1>订单管理</h1>
        <p>掌握履约进度，及时处理待发货与售后订单。</p>
      </div>
      <div class="heading-side-note">
        <span class="live-dot" />
        数据与同步接口实时一致
      </div>
    </section>

    <section class="order-summary-row">
      <button
        v-for="status in statuses.slice(0, 4)"
        :key="status"
        type="button"
        class="order-summary-card"
        :class="{ active: filter === status }"
        @click="filter = filter === status ? '' : status"
      >
        <span><i :class="`order-dot status-${status}`" />{{ status }}</span>
        <strong>{{ counts[status] || 0 }}</strong>
        <small>查看订单</small>
      </button>
    </section>

    <section class="panel">
      <div class="toolbar">
        <label class="search-box">
          <Icon name="search" :size="18" />
          <input v-model="query" placeholder="搜索订单号或客户" />
        </label>
        <div class="toolbar-right">
          <select v-model="filter" class="select-control">
            <option value="">全部状态</option>
            <option v-for="status in statuses" :key="status">{{ status }}</option>
          </select>
          <button class="button button-ghost" type="button" @click="load">
            <Icon name="refresh" :size="17" /> 刷新
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">正在加载订单…</div>
      <div v-else class="data-table-wrap">
        <table class="data-table">
          <thead>
            <tr><th>订单编号</th><th>客户</th><th>商品</th><th>订单金额</th><th>物流</th><th>状态</th><th>下单时间</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="order in filtered" :key="order.id">
              <td><strong class="order-code">{{ order.order_no }}</strong></td>
              <td>
                <strong>{{ order.customer_name }}</strong>
                <small class="block-muted">{{ order.receiver }}</small>
              </td>
              <td>{{ order.item_count }} 件</td>
              <td><strong>{{ money(order.total_cents) }}</strong></td>
              <td>
                <span>{{ order.logistics_company || '尚未发货' }}</span>
                <small class="block-muted">{{ order.logistics_status }}</small>
              </td>
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
        <div class="drawer-head">
          <div>
            <span class="panel-kicker">ORDER DETAIL</span>
            <h2>{{ selected.order_no }}</h2>
          </div>
          <button class="close-button" type="button" @click="selected = null">×</button>
        </div>

        <div class="order-hero">
          <div>
            <small>订单金额</small>
            <strong>{{ money(selected.total_cents) }}</strong>
          </div>
          <StatusBadge :status="selected.status" />
        </div>

        <div class="detail-section">
          <div class="section-title"><h3>订单状态</h3><span>变更后将立即生效</span></div>
          <div class="status-steps">
            <button
              v-for="status in statuses"
              :key="status"
              type="button"
              :class="{ active: selected.status === status }"
              :disabled="updating"
              @click="changeStatus(status)"
            >
              {{ status }}
            </button>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title"><h3>商品明细</h3><span>{{ selected.items.length }} 个商品</span></div>
          <div v-for="item in selected.items" :key="item.id" class="item-line">
            <span class="item-emoji">{{ item.emoji }}</span>
            <div><strong>{{ item.product_name }}</strong><small>{{ money(item.unit_price_cents) }} × {{ item.quantity }}</small></div>
            <strong>{{ money(item.unit_price_cents * item.quantity) }}</strong>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title"><h3>客户与收货</h3></div>
          <div class="info-grid">
            <div><small>客户</small><strong>{{ selected.customer_name }}</strong></div>
            <div><small>收货人</small><strong>{{ selected.receiver }}</strong></div>
            <div><small>联系电话</small><strong>{{ selected.phone.slice(0, 3) }}****{{ selected.phone.slice(-4) }}</strong></div>
            <div><small>下单时间</small><strong>{{ fullDate(selected.created_at) }}</strong></div>
            <div class="span-2"><small>收货地址</small><strong>{{ selected.address }}</strong></div>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title"><h3>物流信息</h3></div>
          <div class="logistics-box">
            <div class="truck-mark">↗</div>
            <div>
              <strong>{{ selected.logistics_company || '等待发货' }}</strong>
              <p>{{ selected.logistics_status }}</p>
              <small>{{ selected.tracking_no || '暂无运单号' }}</small>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
