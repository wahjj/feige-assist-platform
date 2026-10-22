<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { auth } from '../auth'

const route = useRoute()
const router = useRouter()
const username = ref('admin')
const password = ref('admin123')
const loading = ref(false)
const error = ref('')

async function submit() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.detail || '登录失败')
    }
    auth.setSession(payload)
    router.push(route.query.redirect || { name: 'dashboard' })
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-story">
      <div class="login-brand">
        <div class="brand-mark large">禾</div>
        <div>
          <strong>禾光生活研究所</strong>
          <span>MERCHANT STUDIO</span>
        </div>
      </div>
      <div class="story-copy">
        <p class="eyebrow">YOUR EVERYDAY, BEAUTIFULLY MANAGED.</p>
        <h1>把每一次咨询，<br />变成一次好生意。</h1>
        <p class="story-lead">
          在一处查看商品、订单与客户，和 AI 客服并肩处理每一段对话。
        </p>
      </div>
      <div class="story-panel">
        <div class="story-panel-head">
          <span><i /> 今日经营状态</span>
          <strong>10 / 22</strong>
        </div>
        <div class="story-metrics">
          <div><small>成交订单</small><strong>28</strong><em>+12.8%</em></div>
          <div><small>客服响应</small><strong>1m 42s</strong><em>持续改善</em></div>
        </div>
        <div class="story-bars">
          <i v-for="height in [32, 45, 39, 64, 52, 72, 84, 67, 91]" :key="height" :style="{ height: `${height}%` }" />
        </div>
      </div>
      <p class="login-footnote">本地演示版 · 数据仅保存在你的电脑</p>
    </section>

    <section class="login-panel">
      <div class="login-form-wrap">
        <span class="login-kicker">欢迎回来</span>
        <h2>登录商家中心</h2>
        <p class="login-subtitle">使用演示账号体验完整的店铺管理流程。</p>

        <form @submit.prevent="submit">
          <label class="field">
            <span>管理员账号</span>
            <input v-model="username" autocomplete="username" />
          </label>
          <label class="field">
            <span>登录密码</span>
            <input v-model="password" type="password" autocomplete="current-password" />
          </label>
          <p v-if="error" class="form-error">{{ error }}</p>
          <button class="button button-primary login-button" :disabled="loading">
            {{ loading ? '正在登录…' : '进入商家中心' }}
          </button>
        </form>

        <div class="demo-credentials">
          <span>演示账号</span>
          <code>admin</code>
          <code>admin123</code>
        </div>
        <router-link class="customer-link" to="/chat">以消费者身份打开咨询页 →</router-link>
      </div>
    </section>
  </main>
</template>
