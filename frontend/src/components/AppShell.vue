<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { auth } from '../auth'
import Icon from './Icon.vue'

const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

const nav = [
  { name: 'dashboard', label: '概览', icon: 'home' },
  { name: 'products', label: '商品管理', icon: 'product' },
  { name: 'orders', label: '订单管理', icon: 'order' },
  { name: 'customers', label: '客户管理', icon: 'customer' },
  { name: 'service', label: '客服工作台', icon: 'chat', badge: 2 },
  { name: 'approvals', label: '售后审批', icon: 'approval', badge: 1 },
  { name: 'settings', label: '设置', icon: 'settings' },
]

const currentLabel = computed(
  () => nav.find((item) => item.name === route.name)?.label || '商家中心',
)

async function logout() {
  await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' })
  auth.clear()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar" :class="{ open: menuOpen }">
      <div class="brand">
        <div class="brand-mark">禾</div>
        <div>
          <strong>禾光</strong>
          <span>MERCHANT STUDIO</span>
        </div>
      </div>

      <div class="store-card">
        <span class="store-dot" />
        <div>
          <small>当前店铺</small>
          <strong>禾光生活研究所</strong>
        </div>
      </div>

      <nav class="side-nav">
        <router-link
          v-for="item in nav"
          :key="item.name"
          :to="{ name: item.name }"
          class="nav-link"
          @click="menuOpen = false"
        >
          <Icon :name="item.icon" :size="19" />
          <span>{{ item.label }}</span>
          <em v-if="item.badge">{{ item.badge }}</em>
        </router-link>
      </nav>

      <div class="sidebar-note">
        <div class="pulse-dot" />
        <div>
          <strong>本地演示环境</strong>
          <span>数据仅保存在此电脑</span>
        </div>
      </div>
    </aside>

    <button class="mobile-menu" type="button" @click="menuOpen = !menuOpen">☰</button>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-title">
          <span>禾光商家中心</span>
          <strong>{{ currentLabel }}</strong>
        </div>
        <div class="topbar-actions">
          <div class="top-search">
            <Icon name="search" :size="18" />
            <input aria-label="全局搜索" placeholder="搜索订单、客户或商品" />
            <kbd>⌘ K</kbd>
          </div>
          <button class="icon-button" aria-label="通知">
            <Icon name="bell" :size="19" />
            <i />
          </button>
          <div class="profile">
            <div class="avatar">管</div>
            <div>
              <strong>店铺管理员</strong>
              <span>{{ auth.username || 'admin' }}</span>
            </div>
            <button class="text-button" type="button" @click="logout">退出</button>
          </div>
        </div>
      </header>

      <main class="page-content">
        <slot />
      </main>
    </div>
  </div>
</template>
