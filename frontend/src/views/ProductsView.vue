<script setup>
import { computed, onMounted, ref } from 'vue'

import { get } from '../api'
import Icon from '../components/Icon.vue'
import SourceFreshness from '../components/SourceFreshness.vue'
import { money, shortDate } from '../utils'

const products = ref([])
const query = ref('')
const categoryFilter = ref('')
const expandedId = ref('')
const loading = ref(true)

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return products.value.filter((product) => {
    const searchable = [
      product.title,
      product.category,
      ...(product.skus || []).flatMap((sku) => [sku.sku_name, sku.size, sku.color]),
    ].join(' ').toLowerCase()
    return (!keyword || searchable.includes(keyword)) &&
      (!categoryFilter.value || product.category === categoryFilter.value)
  })
})

const categories = computed(() => [...new Set(products.value.map((item) => item.category))])
const skuCount = computed(() =>
  products.value.reduce((total, product) => total + (product.skus?.length || 0), 0),
)

async function load() {
  loading.value = true
  try {
    products.value = await get('/api/products')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div><p class="eyebrow dark">CATALOG MIRROR</p><h1>商品资料</h1><p>商品、SKU、价格和库存从抖店单向同步，仅供客服参考。</p></div>
      <div class="heading-side-note"><span class="live-dot" /> 抖店同步 · 只读</div>
    </section>

    <div class="readonly-banner">
      <span class="readonly-mark"><Icon name="product" :size="17" /></span>
      <div><strong>商品数据只读</strong><p>所有上架、改价和库存操作请回抖店后台完成，中台修改不会反向同步。</p></div>
      <SourceFreshness :time="products[0]?.synced_at" />
    </div>

    <section class="mini-stats">
      <div><span>商品档案</span><strong>{{ products.length }}</strong><small>个</small></div>
      <div><span>SKU 总数</span><strong>{{ skuCount }}</strong><small>个规格</small></div>
      <div><span>知识已绑定</span><strong>{{ products.filter((item) => item.knowledge_bound).length }}</strong><small>个商品</small></div>
      <div><span>库存偏少</span><strong class="warning-text">{{ products.filter((item) => item.skus?.some((sku) => sku.stock < 10)).length }}</strong><small>个商品</small></div>
    </section>

    <section class="panel">
      <div class="toolbar">
        <label class="search-box"><Icon name="search" :size="18" /><input v-model="query" placeholder="搜索商品、SKU、颜色或尺码" /></label>
        <div class="toolbar-right">
          <select v-model="categoryFilter" class="select-control"><option value="">全部分类</option><option v-for="category in categories" :key="category">{{ category }}</option></select>
          <button class="button button-ghost" type="button" @click="load"><Icon name="refresh" :size="17" /> 刷新</button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">正在加载商品镜像…</div>
      <div v-else class="data-table-wrap">
        <table class="data-table product-table">
          <thead><tr><th>商品</th><th>分类</th><th>SKU / 尺码</th><th>价格</th><th>总库存</th><th>知识</th><th>同步时间</th><th /></tr></thead>
          <tbody>
            <template v-for="product in filtered" :key="product.id">
              <tr class="product-readonly-row">
                <td><div class="product-cell"><div class="product-thumb" :style="{ background: '#edf0e9' }">{{ product.image_emoji }}</div><div><strong>{{ product.title }}</strong><small>{{ product.external_id }}</small></div></div></td>
                <td><span class="soft-tag">{{ product.category }}</span></td>
                <td><strong>{{ product.skus?.length || 0 }}</strong><small class="block-muted">{{ product.skus?.map((sku) => sku.size).join(' / ') }}</small></td>
                <td>{{ money(Math.min(...(product.skus || [{ price_cents: 0 }]).map((sku) => sku.price_cents))) }}</td>
                <td>{{ product.skus?.reduce((sum, sku) => sum + sku.stock, 0) || 0 }}</td>
                <td><span class="knowledge-state" :class="{ bound: product.knowledge_bound }">{{ product.knowledge_bound ? '已绑定' : '未绑定' }}</span></td>
                <td class="muted">{{ shortDate(product.synced_at) }}</td>
                <td><button class="row-link" type="button" @click="expandedId = expandedId === product.id ? '' : product.id">{{ expandedId === product.id ? '收起' : 'SKU' }}</button></td>
              </tr>
              <tr v-if="expandedId === product.id" class="sku-expanded-row">
                <td colspan="8"><div class="sku-grid"><div v-for="sku in product.skus" :key="sku.id" class="sku-chip"><span>{{ sku.sku_name }}</span><strong>{{ money(sku.price_cents) }}</strong><small>库存 {{ sku.stock }}</small></div></div></td>
              </tr>
            </template>
          </tbody>
        </table>
        <div v-if="!filtered.length" class="empty-state">没有找到符合条件的商品。</div>
      </div>
    </section>
  </div>
</template>
