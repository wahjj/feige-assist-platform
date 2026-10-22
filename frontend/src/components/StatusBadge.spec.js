import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StatusBadge from './StatusBadge.vue'

describe('StatusBadge', () => {
  it('renders a Chinese order status with the matching tone class', () => {
    const wrapper = mount(StatusBadge, {
      props: { status: '待发货' },
    })

    expect(wrapper.text()).toBe('待发货')
    expect(wrapper.classes()).toContain('tone-warning')
  })
})
