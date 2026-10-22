<script setup>
import { onMounted, reactive, ref } from 'vue'

import { get, post } from '../api'
import Icon from '../components/Icon.vue'

const status = ref(null)
const submitting = ref(false)
const result = ref(null)
const error = ref('')
const form = reactive({
  event_type: 'buyer_message',
  external_event_id: `webhook-${Date.now()}`,
  external_conversation_id: 'conv-demo-001',
  external_message_id: `message-${Date.now()}`,
  text: '这条裙子我身高 165、体重 52kg，应该选什么码？',
  state: '接待中',
})

const presets = [
  ['尺码咨询', 'buyer_message', '这条裙子我身高 165、体重 52kg，应该选什么码？'],
  ['面料问题', 'buyer_message', '这件开衫的面料会起球吗？应该怎么洗？'],
  ['物流催件', 'buyer_message', '快递三天没有更新了，可以帮我看看吗？'],
  ['申请退款', 'buyer_message', '这件衣服不合适，我想申请退款。'],
  ['飞鸽客服回复', 'service_agent_message', '您好，这款建议选择 M 码，版型会更合适。'],
]

function applyPreset(preset) {
  form.event_type = preset[1]
  form.text = preset[2]
  form.external_event_id = `webhook-${Date.now()}`
  form.external_message_id = `message-${Date.now()}`
}

async function submit() {
  submitting.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await post('/api/demo/events', { ...form })
    form.external_event_id = `webhook-${Date.now()}`
    form.external_message_id = `message-${Date.now()}`
    await loadStatus()
  } catch (err) {
    error.value = err.message
  } finally {
    submitting.value = false
  }
}

async function loadStatus() {
  status.value = await get('/api/integration/status')
}

onMounted(loadStatus)
</script>

<template>
  <div class="page-stack">
    <section class="page-heading">
      <div><p class="eyebrow dark">LOCAL EVENT SIMULATOR</p><h1>模拟飞鸽事件</h1><p>用本地事件验证验签、去重、会话镜像和建议生成。</p></div>
      <router-link class="button button-ghost" to="/conversations">查看会话中心 <Icon name="arrow" :size="16" /></router-link>
    </section>

    <div class="readonly-banner">
      <span class="readonly-mark">ⓘ</span>
      <div><strong>仅用于本地验收</strong><p>事件会提交到模拟 Webhook 入口，不会调用抖音真实接口或向买家发送任何消息。</p></div>
    </div>

    <section class="simulator-grid">
      <article class="panel simulator-form-card">
        <div class="panel-heading"><div><span class="panel-kicker">EVENT PAYLOAD</span><h2>生成一条事件</h2></div><span class="soft-tag">HMAC 签名</span></div>
        <div class="preset-row">
          <button v-for="preset in presets" :key="preset[0]" type="button" @click="applyPreset(preset)">{{ preset[0] }}</button>
        </div>
        <form class="simulator-form" @submit.prevent="submit">
          <label class="field"><span>事件类型</span><select v-model="form.event_type"><option value="buyer_message">买家消息</option><option value="service_agent_message">飞鸽客服消息</option><option value="session_state">会话状态变化</option></select></label>
          <label class="field"><span>外部事件 ID</span><input v-model="form.external_event_id" required /></label>
          <label class="field"><span>外部会话 ID</span><input v-model="form.external_conversation_id" required /></label>
          <label class="field"><span>外部消息 ID</span><input v-model="form.external_message_id" required /></label>
          <label v-if="form.event_type !== 'session_state'" class="field span-2"><span>消息内容</span><textarea v-model="form.text" rows="5" /></label>
          <label v-else class="field span-2"><span>新会话状态</span><select v-model="form.state"><option>接待中</option><option>已关闭</option></select></label>
          <p v-if="error" class="form-error span-2">{{ error }}</p>
          <div class="span-2 simulator-actions"><button class="button button-primary" :disabled="submitting">{{ submitting ? '正在推送…' : '发送模拟事件' }}</button></div>
        </form>
      </article>

      <article class="panel simulator-side">
        <div class="panel-heading"><div><span class="panel-kicker">RESULT</span><h2>事件结果</h2></div></div>
        <div v-if="result" class="event-result" :class="result.status">
          <span>{{ result.status === 'accepted' ? '✓' : result.status === 'duplicate' ? '↺' : '!' }}</span>
          <div><strong>{{ result.status }}</strong><p>{{ result.status === 'accepted' ? '事件已进入只读镜像。' : result.status === 'duplicate' ? '重复事件已被幂等去重。' : result.detail }}</p></div>
        </div>
        <div v-else class="insight-empty event-empty"><span class="insight-symbol">⌁</span><h3>等待事件</h3><p>提交后在这里查看 Webhook 处理结果。</p></div>
        <div class="detail-section">
          <div class="section-title"><h3>模拟接入状态</h3></div>
          <div class="mini-track"><i class="done" /><i class="done" /><i class="current" /><i /></div>
          <div class="track-labels"><span>签名</span><span>去重</span><span>镜像</span><span>建议</span></div>
        </div>
        <div class="event-tip"><strong>未配置模型？</strong><p>消息仍会正常同步到会话；AI 建议区会提示配置真实模型。</p></div>
      </article>
    </section>
  </div>
</template>
