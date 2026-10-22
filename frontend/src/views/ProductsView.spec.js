import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ProductsView from './ProductsView.vue'

afterEach(() => vi.unstubAllGlobals())

describe('ProductsView', () => {
  it('renders source freshness and no product edit action', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => [
          {
            id: 'product-1',
            external_id: 'product-001',
            title: '法式碎花连衣裙',
            category: '连衣裙',
            image_emoji: '👗',
            source: 'douyin',
            synced_at: '2026-10-22T08:00:00Z',
            knowledge_bound: true,
            skus: [
              {
                id: 'sku-1',
                sku_name: '雾蓝 M',
                color: '雾蓝',
                size: 'M',
                stock: 12,
                price_cents: 26900,
              },
            ],
          },
        ],
      })),
    )

    const wrapper = mount(ProductsView)
    await flushPromises()

    expect(wrapper.text()).toContain('抖店同步')
    expect(wrapper.text()).toContain('法式碎花连衣裙')
    expect(wrapper.text()).not.toContain('新增商品')
    expect(wrapper.text()).not.toContain('归档')
  })
})
