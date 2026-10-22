import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AiSuggestionPanel from './AiSuggestionPanel.vue'

describe('AiSuggestionPanel', () => {
  it('shows copy actions but no send or takeover controls', () => {
    const wrapper = mount(AiSuggestionPanel, {
      props: {
        modelConfigured: true,
        suggestion: {
          id: 'suggestion-1',
          status: 'success',
          suggestions: [
            { style: '专业说明', text: '建议一' },
            { style: '简洁直接', text: '建议二' },
            { style: '温和安抚', text: '建议三' },
          ],
          sources: [],
          warnings: [],
        },
      },
    })

    expect(wrapper.text()).toContain('复制话术')
    expect(wrapper.text()).not.toContain('发送消息')
    expect(wrapper.text()).not.toContain('接管会话')
  })
})
