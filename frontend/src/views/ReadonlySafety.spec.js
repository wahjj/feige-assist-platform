import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import PanelPlaceholderView from './PanelPlaceholderView.vue'

describe('PanelPlaceholderView', () => {
  it('shows only a non-interactive side-panel placeholder', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    })
    await router.push('/')
    await router.isReady()
    const wrapper = mount(PanelPlaceholderView, { global: { plugins: [router] } })

    expect(wrapper.text()).toContain('飞鸽右侧 AI 辅助面板规划中')
    expect(wrapper.find('button').exists()).toBe(false)
    expect(wrapper.find('iframe').exists()).toBe(false)
  })
})
