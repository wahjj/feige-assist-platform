import { createRouter, createWebHistory } from 'vue-router'

import { auth } from './auth'
import AnalyticsView from './views/AnalyticsView.vue'
import ConversationsView from './views/ConversationsView.vue'
import CustomersView from './views/CustomersView.vue'
import KnowledgeView from './views/KnowledgeView.vue'
import LoginView from './views/LoginView.vue'
import MockEventsView from './views/MockEventsView.vue'
import OrdersView from './views/OrdersView.vue'
import OverviewView from './views/OverviewView.vue'
import PanelPlaceholderView from './views/PanelPlaceholderView.vue'
import ProductsView from './views/ProductsView.vue'
import SyncSettingsView from './views/SyncSettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true, bare: true },
    },
    { path: '/', name: 'overview', component: OverviewView },
    { path: '/conversations', name: 'conversations', component: ConversationsView },
    { path: '/products', name: 'products', component: ProductsView },
    { path: '/orders', name: 'orders', component: OrdersView },
    { path: '/customers', name: 'customers', component: CustomersView },
    { path: '/knowledge', name: 'knowledge', component: KnowledgeView },
    { path: '/analytics', name: 'analytics', component: AnalyticsView },
    { path: '/sync', name: 'sync', component: SyncSettingsView },
    { path: '/mock-events', name: 'mock-events', component: MockEventsView },
    {
      path: '/panel',
      name: 'panel',
      component: PanelPlaceholderView,
      meta: { bare: true },
    },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.public && !auth.authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.authenticated) {
    return { name: 'overview' }
  }
  return true
})

export default router
