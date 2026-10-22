import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import KnowledgeView from './KnowledgeView.vue'

afterEach(() => vi.unstubAllGlobals())

describe('KnowledgeView', () => {
  it('renders knowledge types and product binding fields', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) => ({
        ok: true,
        status: 200,
        json: async () =>
          String(url).includes('/api/products')
            ? [{ id: 'product-1', title: '法式碎花连衣裙', category: '连衣裙' }]
            : [
                {
                  id: 'knowledge-1',
                  entry_type: '尺码表',
                  title: '连衣裙尺码表',
                  content: '身高 160-165 建议 M 码',
                  keywords: '尺码,身高',
                  product_id: 'product-1',
                  category: '连衣裙',
                  enabled: true,
                  updated_at: '2026-10-22T08:00:00Z',
                },
              ],
      })),
    )

    const wrapper = mount(KnowledgeView)
    await flushPromises()

    expect(wrapper.text()).toContain('尺码表')
    expect(wrapper.text()).toContain('面料与养护')
    expect(wrapper.find('[data-testid="knowledge-product"]').exists()).toBe(true)
  })
})
