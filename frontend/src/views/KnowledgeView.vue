<script setup>
import { computed, onMounted, ref } from 'vue'

import { del, get, post, put } from '../api'
import Icon from '../components/Icon.vue'
import KnowledgeEditor from '../components/KnowledgeEditor.vue'

const entries = ref([])
const products = ref([])
const selected = ref(null)
const query = ref('')
const typeFilter = ref('')
const loading = ref(true)
const saving = ref(false)
const notice = ref('')

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return entries.value.filter((entry) => {
    const match = !keyword || [entry.title, entry.content, entry.keywords]
      .join(' ')
      .toLowerCase()
      .includes(keyword)
    return match && (!typeFilter.value || entry.entry_type === typeFilter.value)
  })
})

const types = computed(() => [...new Set(entries.value.map((entry) => entry.entry_type))])

async function load() {
  loading.value = true
  try {
    const [knowledgeEntries, productRows] = await Promise.all([
      get('/api/knowledge'),
      get('/api/products'),
    ])
    entries.value = knowledgeEntries
    products.value = productRows
    selected.value = knowledgeEntries[0] || null
  } finally {
    loading.value = false
  }
}

function createEntry() {
  selected.value = null
}

async function saveEntry(payload) {
  saving.value = true
  try {
    const saved = payload.id
      ? await put(`/api/knowledge/${payload.id}`, payload)
      : await post('/api/knowledge', payload)
    const savedId = saved.id
    notice.value = payload.id ? '知识条目已更新' : '知识条目已创建'
    await load()
    selected.value = entries.value.find((entry) => entry.id === savedId) || entries.value[0] || null
    window.setTimeout(() => (notice.value = ''), 2400)
  } finally {
    saving.value = false
  }
}

async function removeEntry(id) {
  if (!window.confirm('确认删除这条知识？删除后将不再参与 AI 检索。')) return
  await del(`/api/knowledge/${id}`)
  notice.value = '知识条目已删除'
  selected.value = null
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">LOCAL RAG KNOWLEDGE</p>
        <h1>AI知识库</h1>
        <p>把服装尺码、面料、养护和售后规则沉淀成客服可用的专业参考。</p>
      </div>
      <button class="button button-primary" type="button" @click="createEntry"><Icon name="plus" :size="18" /> 新增知识</button>
    </section>

    <div class="readonly-banner knowledge-banner">
      <span class="readonly-mark">RAG</span>
      <div><strong>本地检索 · 商品绑定优先</strong><p>知识库只影响中台 AI 建议，不会修改抖店商品或直接回复买家。</p></div>
      <span class="source-refresh">关键词/全文召回</span>
    </div>

    <div v-if="notice" class="toast-success">{{ notice }}</div>

    <section class="knowledge-layout">
      <aside class="panel knowledge-list-panel">
        <div class="knowledge-list-tools">
          <label class="search-box">
            <Icon name="search" :size="18" />
            <input v-model="query" placeholder="搜索标题、内容或关键词" />
          </label>
          <select v-model="typeFilter" class="select-control">
            <option value="">全部类型</option>
            <option v-for="type in types" :key="type">{{ type }}</option>
          </select>
        </div>
        <div v-if="loading" class="loading-state">正在读取知识库…</div>
        <button
          v-for="entry in filtered"
          :key="entry.id"
          type="button"
          class="knowledge-list-item"
          :class="{ active: selected?.id === entry.id }"
          @click="selected = entry"
        >
          <span class="knowledge-list-type">{{ entry.entry_type.slice(0, 2) }}</span>
          <span><strong>{{ entry.title }}</strong><small>{{ entry.category || '通用知识' }} · {{ entry.enabled ? '启用' : '停用' }}</small></span>
          <em>{{ entry.keywords }}</em>
        </button>
        <div v-if="!filtered.length && !loading" class="empty-state">知识库中没有匹配条目。</div>
      </aside>

      <article class="panel knowledge-editor-panel">
        <KnowledgeEditor :entry="selected" :products="products" :saving="saving" @save="saveEntry" @delete="removeEntry" />
      </article>
    </section>
  </div>
</template>
