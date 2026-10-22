import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import AppShell from './AppShell.vue'

describe('AppShell', () => {
  it('contains the Feige assist navigation and no send action', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'overview', component: { template: '<div />' } },
      ],
    })
    await router.push('/')
    await router.isReady()

    const wrapper = mount(AppShell, {
      global: {
        plugins: [router],
        stubs: { RouterLink: { template: '<a><slot /></a>' } },
      },
    })

    expect(wrapper.text()).toContain('会话中心')
    expect(wrapper.text()).toContain('AI知识库')
    expect(wrapper.text()).toContain('数据镜像')
    expect(wrapper.text()).not.toContain('发送消息')
    expect(wrapper.text()).not.toContain('接管会话')
  })
})
