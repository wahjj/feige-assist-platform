<script setup>
import { onMounted, reactive, ref } from 'vue'

import { get, post, put } from '../api'
import Icon from '../components/Icon.vue'
import { shortDate } from '../utils'

const settings = ref(null)
const loading = ref(true)
const saving = ref(false)
const testing = ref(false)
const notice = ref('')
const error = ref('')
const form = reactive({
  base_url: '',
  model: '',
  api_key: '',
})

async function load() {
  loading.value = true
  try {
    settings.value = await get('/api/settings')
    form.base_url = settings.value.model_base_url
    form.model = settings.value.model_name
  } finally {
    loading.value = false
  }
}

async function saveModel() {
  saving.value = true
  error.value = ''
  try {
    await put('/api/settings/model', form)
    form.api_key = ''
    notice.value = '大模型配置已保存'
    await load()
    window.setTimeout(() => (notice.value = ''), 2600)
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function testModel() {
  testing.value = true
  error.value = ''
  try {
    const result = await post('/api/settings/model/test')
    notice.value = `连接成功：${result.preview}`
  } catch (err) {
    error.value = err.message
  } finally {
    testing.value = false
  }
}

async function copyText(text) {
  await navigator.clipboard.writeText(text)
  notice.value = '接口地址已复制'
  window.setTimeout(() => (notice.value = ''), 1800)
}

onMounted(load)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">SETTINGS</p>
        <h1>系统设置</h1>
        <p>连接真实大模型，并为商家系统开放数据同步接口。</p>
      </div>
      <span class="local-pill">仅限本机 · 127.0.0.1</span>
    </section>

    <div v-if="notice" class="toast-success">{{ notice }}</div>

    <div v-if="loading" class="loading-state">正在读取本地配置…</div>
    <div v-else class="settings-grid">
      <section class="panel settings-card model-card">
        <div class="settings-card-head">
          <div class="settings-icon">AI</div>
          <div><span class="panel-kicker">LANGUAGE MODEL</span><h2>大模型连接</h2><p>支持 OpenAI 兼容的 Chat Completions 接口。</p></div>
          <span class="configured-state" :class="{ ready: settings.model_configured }">{{ settings.model_configured ? '已配置' : '待配置' }}</span>
        </div>
        <form class="model-form" @submit.prevent="saveModel">
          <label class="field span-2"><span>服务地址</span><input v-model="form.base_url" placeholder="https://api.example.com/v1" /></label>
          <label class="field"><span>模型名称</span><input v-model="form.model" placeholder="例如 deepseek-chat" /></label>
          <label class="field"><span>API Key</span><input v-model="form.api_key" type="password" :placeholder="settings.model_api_key_masked" /></label>
          <p v-if="error" class="form-error span-2">{{ error }}</p>
          <div class="inline-actions span-2">
            <button class="button button-primary" :disabled="saving">{{ saving ? '保存中…' : '保存配置' }}</button>
            <button class="button button-ghost" type="button" :disabled="testing" @click="testModel">{{ testing ? '测试中…' : '测试连接' }}</button>
          </div>
        </form>
      </section>

      <section class="panel settings-card sync-card">
        <div class="settings-card-head">
          <div class="settings-icon sync">↔</div>
          <div><span class="panel-kicker">SYNC ADAPTER</span><h2>数据同步接口</h2><p>让商家系统批量录入商品、订单、客户和消息。</p></div>
        </div>
        <div class="sync-status"><span class="live-dot" /><div><strong>接口运行中</strong><small>最近调用 {{ shortDate(settings.sync_last_at) }}</small></div></div>
        <div class="code-field">
          <span>API 地址</span>
          <code>{{ settings.sync_base_url }}</code>
          <button type="button" @click="copyText(settings.sync_base_url)">复制</button>
        </div>
        <div class="code-field">
          <span>API Key</span>
          <code>{{ settings.sync_api_key_masked }}</code>
          <button type="button">轮换</button>
        </div>
        <div class="endpoint-list">
          <span><em>POST</em> /products</span>
          <span><em>POST</em> /customers</span>
          <span><em>POST</em> /orders</span>
          <span><em>POST</em> /messages</span>
        </div>
      </section>

      <section class="panel settings-card interface-guide">
        <div class="section-title"><h2>接入说明</h2><span>JSON / Bearer Token</span></div>
        <p>商家系统向接口发送批量数组，以 <code>external_id</code> 保证幂等。同步不会覆盖后台维护的客户备注和标签。</p>
        <pre><code>curl -X POST "{{ settings.sync_base_url }}/products"
  -H "Authorization: Bearer YOUR_KEY"
  -H "Content-Type: application/json"
  -d '[{"external_id":"p-1001",
       "name":"新品",
       "price_cents":12900,
       "stock":20}]'</code></pre>
      </section>

      <section class="panel settings-card logs-card">
        <div class="section-title"><h2>最近同步记录</h2><button class="text-link" type="button" @click="load">刷新</button></div>
        <div v-for="log in settings.sync_logs" :key="log.id" class="sync-log-row">
          <span class="log-mark">✓</span>
          <div><strong>{{ log.endpoint }}</strong><small>{{ log.summary }}</small></div>
          <time>{{ shortDate(log.created_at) }}</time>
        </div>
        <div v-if="!settings.sync_logs.length" class="empty-state">暂无同步记录。</div>
      </section>

      <section class="panel settings-card data-card">
        <div class="settings-card-head">
          <div class="settings-icon data">↧</div>
          <div><span class="panel-kicker">LOCAL DATA</span><h2>本地数据</h2><p>SQLite 数据库和商品图片仅保存在当前电脑。</p></div>
        </div>
        <div class="data-path"><span>数据位置</span><code>./data/demo.db</code></div>
        <p class="muted">正式交付时将提供加密备份与恢复；当前演示版可直接查看本地数据持久化效果。</p>
      </section>
    </div>
  </div>
</template>
