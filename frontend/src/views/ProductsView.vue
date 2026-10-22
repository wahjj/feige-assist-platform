<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import { ApiError, del, get, post, put } from '../api'
import Icon from '../components/Icon.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { money, shortDate } from '../utils'

const products = ref([])
const query = ref('')
const statusFilter = ref('')
const loading = ref(true)
const showEditor = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const blankForm = () => ({
  id: '',
  name: '',
  sku: '',
  category: '',
  price: '',
  stock: 0,
  status: '上架',
  emoji: '📦',
  accent: '#e6e9df',
  description: '',
})
const form = reactive(blankForm())

const filtered = computed(() =>
  products.value.filter((product) => {
    const keyword = query.value.trim().toLowerCase()
    const matchesQuery =
      !keyword ||
      [product.name, product.sku, product.category].some((value) =>
        String(value).toLowerCase().includes(keyword),
      )
    return matchesQuery && (!statusFilter.value || product.status === statusFilter.value)
  }),
)

const totals = computed(() => ({
  count: products.value.length,
  active: products.value.filter((item) => item.status === '上架').length,
  low: products.value.filter((item) => item.stock <= 20).length,
  value: products.value.reduce((sum, item) => sum + item.price_cents * item.stock, 0),
}))

async function load() {
  loading.value = true
  try {
    products.value = await get('/api/products')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, blankForm())
  error.value = ''
  showEditor.value = true
}

function openEdit(product) {
  Object.assign(form, {
    ...product,
    price: (product.price_cents / 100).toFixed(2),
  })
  error.value = ''
  showEditor.value = true
}

async function save() {
  saving.value = true
  error.value = ''
  const payload = {
    name: form.name.trim(),
    sku: form.sku.trim(),
    category: form.category.trim() || '未分类',
    price_cents: Math.round(Number(form.price || 0) * 100),
    stock: Number(form.stock || 0),
    status: form.status,
    emoji: form.emoji || '📦',
    accent: form.accent,
    description: form.description,
  }
  try {
    if (form.id) {
      await put(`/api/products/${form.id}`, payload)
      notice.value = '商品信息已更新'
    } else {
      await post('/api/products', payload)
      notice.value = '新商品已加入店铺'
    }
    showEditor.value = false
    await load()
    window.setTimeout(() => (notice.value = ''), 2600)
  } catch (err) {
    error.value = err instanceof ApiError ? err.message : '保存失败'
  } finally {
    saving.value = false
  }
}

async function archive(product) {
  if (!window.confirm(`确认归档“${product.name}”？历史订单会保留。`)) return
  await del(`/api/products/${product.id}`)
  notice.value = '商品已归档'
  await load()
  window.setTimeout(() => (notice.value = ''), 2600)
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">CATALOG</p>
        <h1>商品管理</h1>
        <p>维护在售商品、库存与展示信息。</p>
      </div>
      <button class="button button-primary" type="button" @click="openCreate">
        <Icon name="plus" :size="18" /> 新增商品
      </button>
    </section>

    <div v-if="notice" class="toast-success">{{ notice }}</div>

    <section class="mini-stats">
      <div><span>全部商品</span><strong>{{ totals.count }}</strong><small>SKU</small></div>
      <div><span>正在销售</span><strong>{{ totals.active }}</strong><small>件</small></div>
      <div><span>低库存提醒</span><strong class="warning-text">{{ totals.low }}</strong><small>件</small></div>
      <div><span>库存货值</span><strong>{{ money(totals.value) }}</strong><small>估算</small></div>
    </section>

    <section class="panel">
      <div class="toolbar">
        <label class="search-box">
          <Icon name="search" :size="18" />
          <input v-model="query" placeholder="搜索商品、SKU 或分类" />
        </label>
        <div class="toolbar-right">
          <select v-model="statusFilter" class="select-control">
            <option value="">全部状态</option>
            <option>上架</option>
            <option>下架</option>
          </select>
          <button class="button button-ghost" type="button" @click="load">
            <Icon name="refresh" :size="17" /> 刷新
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">正在加载商品…</div>
      <div v-else class="data-table-wrap">
        <table class="data-table product-table">
          <thead>
            <tr><th>商品</th><th>分类</th><th>售价</th><th>库存</th><th>状态</th><th>更新时间</th><th /></tr>
          </thead>
          <tbody>
            <tr v-for="product in filtered" :key="product.id">
              <td>
                <div class="product-cell">
                  <div class="product-thumb" :style="{ background: product.accent }">{{ product.emoji }}</div>
                  <div><strong>{{ product.name }}</strong><small>{{ product.sku }}</small></div>
                </div>
              </td>
              <td><span class="soft-tag">{{ product.category }}</span></td>
              <td><strong>{{ money(product.price_cents) }}</strong></td>
              <td>
                <span :class="{ 'warning-text': product.stock <= 20 }">{{ product.stock }}</span>
                <small class="muted"> 件</small>
              </td>
              <td><StatusBadge :status="product.status" /></td>
              <td class="muted">{{ shortDate(product.updated_at) }}</td>
              <td class="row-actions">
                <button class="icon-text-button" type="button" @click="openEdit(product)">编辑</button>
                <button class="icon-text-button danger" type="button" @click="archive(product)">归档</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filtered.length" class="empty-state">没有找到符合条件的商品。</div>
      </div>
    </section>

    <div v-if="showEditor" class="modal-backdrop" @click.self="showEditor = false">
      <section class="modal-card product-editor">
        <div class="modal-head">
          <div>
            <span class="panel-kicker">{{ form.id ? 'EDIT PRODUCT' : 'NEW PRODUCT' }}</span>
            <h2>{{ form.id ? '编辑商品' : '新增商品' }}</h2>
          </div>
          <button class="close-button" type="button" @click="showEditor = false">×</button>
        </div>
        <form class="form-grid" @submit.prevent="save">
          <label class="field span-2"><span>商品名称</span><input v-model="form.name" required maxlength="80" /></label>
          <label class="field"><span>SKU</span><input v-model="form.sku" placeholder="自动生成" /></label>
          <label class="field"><span>分类</span><input v-model="form.category" placeholder="例如 家居香氛" /></label>
          <label class="field"><span>售价（元）</span><input v-model="form.price" type="number" min="0" step="0.01" required /></label>
          <label class="field"><span>库存</span><input v-model="form.stock" type="number" min="0" required /></label>
          <label class="field"><span>商品图标</span><input v-model="form.emoji" maxlength="4" /></label>
          <label class="field"><span>状态</span><select v-model="form.status"><option>上架</option><option>下架</option></select></label>
          <label class="field span-2"><span>商品描述</span><textarea v-model="form.description" rows="4" /></label>
          <p v-if="error" class="form-error span-2">{{ error }}</p>
          <div class="modal-actions span-2">
            <button class="button button-ghost" type="button" @click="showEditor = false">取消</button>
            <button class="button button-primary" :disabled="saving">{{ saving ? '保存中…' : '保存商品' }}</button>
          </div>
        </form>
      </section>
    </div>
  </div>
</template>
