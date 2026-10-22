<script setup>
import { onMounted, reactive, ref } from 'vue'

import { get, post, put } from '../api'
import Icon from '../components/Icon.vue'
import { shortDate } from '../utils'

const status = ref(null)
const model = ref(null)
const loading = ref(true)
const pulling = ref('')
const saving = ref(false)
const testing = ref(false)
const notice = ref('')
const error = ref('')
const modelForm = reactive({ base_url: '', model_name: '', api_key: '' })

async function load() {
  loading.value = true
  try {
    const [integration, modelSettings] = await Promise.all([
      get('/api/integration/status'),
      get('/api/settings/model'),
    ])
    status.value = integration
    model.value = modelSettings
    modelForm.base_url = modelSettings.base_url
    modelForm.model_name = modelSettings.model_name
  } finally {
    loading.value = false
  }
}

async function pull(type) {
  pulling.value = type
  try {
    const result = await post(`/api/integration/pull/${type}`)
    notice.value = `${type === 'products' ? '商品' : '订单'}同步完成：成功 ${result.success_count} 条`
    await load()
  } finally {
    pulling.value = ''
  }
}

async function saveModel() {
  saving.value = true
  error.value = ''
  try {
    await put('/api/settings/model', modelForm)
    modelForm.api_key = ''
    notice.value = '大模型配置已保存'
    await load()
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
  notice.value = '已复制'
}

onMounted(load)
</script>

<template>
  <div v-if="loading" class="loading-state">正在读取同步与模型配置…</div>
  <div v-else class="page-stack">
    <section class="page-heading">
      <div><p class="eyebrow dark">SYNC & SETTINGS</p><h1>同步与设置</h1><p>管理模拟抖店连接、数据拉取和真实大模型。</p></div>
      <span class="local-pill">仅本机 · 127.0.0.1</span>
    </section>

    <div v-if="notice" class="toast-success">{{ notice }}</div>

    <section class="sync-hero panel">
      <div class="sync-shop">
        <div class="settings-icon sync">↔</div>
        <div><span class="panel-kicker">DOUYIN CONNECTION</span><h2>{{ status.shop_name }}</h2><p>当前为本地模拟适配器，真实环境接入 OAuth 与签名 Webhook。</p></div>
      </div>
      <span class="connection-pill"><i /> {{ status.connection_status }}</span>
      <div class="sync-times">
        <div><span>商品最近同步</span><strong>{{ shortDate(status.last_product_sync_at) }}</strong></div>
        <div><span>订单最近同步</span><strong>{{ shortDate(status.last_order_sync_at) }}</strong></div>
        <div><span>最近 Webhook</span><strong>{{ shortDate(status.last_webhook_at) }}</strong></div>
      </div>
      <div class="sync-actions">
        <button class="button button-ghost" :disabled="pulling === 'products'" type="button" @click="pull('products')">{{ pulling === 'products' ? '同步中…' : '手动拉取商品' }}</button>
        <button class="button button-ghost" :disabled="pulling === 'orders'" type="button" @click="pull('orders')">{{ pulling === 'orders' ? '同步中…' : '手动拉取订单' }}</button>
        <router-link class="button button-primary" to="/mock-events">打开模拟事件 <Icon name="arrow" :size="16" /></router-link>
      </div>
    </section>

    <div class="settings-grid readonly-settings-grid">
      <section class="panel settings-card model-card">
        <div class="settings-card-head">
          <div class="settings-icon">AI</div>
          <div><span class="panel-kicker">REAL LANGUAGE MODEL</span><h2>大模型连接</h2><p>只支持配置真实模型，不提供本地模拟建议回退。</p></div>
          <span class="configured-state" :class="{ ready: model.configured }">{{ model.configured ? '已配置' : '未配置' }}</span>
        </div>
        <form class="model-form" @submit.prevent="saveModel">
          <label class="field span-2"><span>OpenAI 兼容服务地址</span><input v-model="modelForm.base_url" placeholder="https://api.example.com/v1" /></label>
          <label class="field"><span>模型名称</span><input v-model="modelForm.model_name" placeholder="例如 deepseek-chat" /></label>
          <label class="field"><span>API Key</span><input v-model="modelForm.api_key" type="password" :placeholder="model.api_key_masked" /></label>
          <p v-if="error" class="form-error span-2">{{ error }}</p>
          <div class="inline-actions span-2">
            <button class="button button-primary" :disabled="saving">{{ saving ? '保存中…' : '保存配置' }}</button>
            <button class="button button-ghost" :disabled="testing" type="button" @click="testModel">{{ testing ? '测试中…' : '测试连接' }}</button>
          </div>
        </form>
      </section>

      <section class="panel settings-card webhook-card">
        <div class="settings-card-head">
          <div class="settings-icon sync">⇢</div>
          <div><span class="panel-kicker">FEIGE WEBHOOK</span><h2>消息推送入口</h2><p>接收买家与客服消息，验签后进入只读镜像。</p></div>
        </div>
        <div class="code-field"><span>回调路径</span><code>{{ status.webhook_path }}</code><button type="button" @click="copyText(status.webhook_path)">复制</button></div>
        <div class="readonly-rule-list">
          <span>✓ 事件 ID 去重</span><span>✓ HMAC 验签</span><span>✕ 无消息发送接口</span>
        </div>
        <p class="webhook-note">真实接入时必须使用抖店开放平台可访问的 HTTPS 地址；当前仅支持本地模拟。</p>
      </section>

      <section class="panel settings-card logs-card">
        <div class="section-title"><h2>最近同步记录</h2><button class="text-link" type="button" @click="load">刷新</button></div>
        <div v-for="run in status.sync_runs.slice(0, 6)" :key="run.id" class="sync-log-row">
          <span class="log-mark">✓</span><div><strong>{{ run.sync_type }}</strong><small>成功 {{ run.success_count }} · 失败 {{ run.failed_count }}</small></div><time>{{ shortDate(run.finished_at) }}</time>
        </div>
      </section>

      <section class="panel settings-card logs-card">
        <div class="section-title"><h2>最近 Webhook 事件</h2><span>{{ status.recent_events.length }} 条</span></div>
        <div v-for="event in status.recent_events.slice(0, 6)" :key="event.event_id" class="sync-log-row">
          <span class="log-mark">{{ event.status === 'processed' ? '✓' : '!' }}</span><div><strong>{{ event.event_type }}</strong><small>{{ event.event_id }}</small></div><time>{{ shortDate(event.received_at) }}</time>
        </div>
        <div v-if="!status.recent_events.length" class="empty-state">还没有模拟事件。</div>
      </section>
    </div>
  </div>
</template>
