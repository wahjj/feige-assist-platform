import { createRouter, createWebHistory } from 'vue-router'

import { auth } from './auth'
import ApprovalsView from './views/ApprovalsView.vue'
import CustomersView from './views/CustomersView.vue'
import DashboardView from './views/DashboardView.vue'
import LoginView from './views/LoginView.vue'
import OrdersView from './views/OrdersView.vue'
import ProductsView from './views/ProductsView.vue'
import PublicChatView from './views/PublicChatView.vue'
import ServiceView from './views/ServiceView.vue'
import SettingsView from './views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true, bare: true },
    },
    {
      path: '/chat',
      name: 'public-chat',
      component: PublicChatView,
      meta: { public: true, bare: true },
    },
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/products', name: 'products', component: ProductsView },
    { path: '/orders', name: 'orders', component: OrdersView },
    { path: '/customers', name: 'customers', component: CustomersView },
    { path: '/service', name: 'service', component: ServiceView },
    { path: '/approvals', name: 'approvals', component: ApprovalsView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.public && !auth.authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.authenticated) {
    return { name: 'dashboard' }
  }
  return true
})

export default router
