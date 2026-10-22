<script setup>
import { computed } from 'vue'

import Icon from './Icon.vue'

const props = defineProps({
  suggestion: { type: Object, default: null },
  modelConfigured: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

defineEmits(['regenerate', 'copy', 'configure'])
const blocked = computed(() => props.suggestion?.status === 'blocked')
</script>

<template>
  <section class="ai-suggestion-section">
    <div class="ai-panel-head">
      <div>
        <span class="panel-kicker">RAG ASSISTANT</span>
        <h2>AI 建议</h2>
      </div>
      <button
        v-if="modelConfigured"
        class="icon-button small"
        type="button"
        title="重新生成"
        :disabled="loading"
        @click="$emit('regenerate')"
      >
        <Icon name="refresh" :size="16" />
      </button>
    </div>

    <div v-if="!modelConfigured" class="ai-empty">
      <span class="ai-orb small">AI</span>
      <strong>尚未配置真实大模型</strong>
      <p>配置 OpenAI 兼容接口后，新买家消息会自动生成一次参考建议。</p>
      <button class="soft-action" type="button" @click="$emit('configure')">前往配置</button>
    </div>

    <div v-else-if="loading" class="ai-empty">
      <span class="loading-spinner" />
      <strong>正在调用模型并检索知识库…</strong>
    </div>

    <div v-else-if="error" class="ai-empty error">
      <strong>建议生成失败</strong>
      <p>{{ error }}</p>
      <button class="soft-action" type="button" @click="$emit('regenerate')">重新生成</button>
    </div>

    <div v-else-if="suggestion" class="suggestion-results">
      <div v-if="blocked" class="risk-banner">
        <span>!</span>
        <div><strong>建议包含风险内容</strong><p>检测到 {{ suggestion.warnings.join('、') }}，已禁止复制。</p></div>
      </div>
      <article
        v-for="(item, index) in suggestion.suggestions"
        :key="`${item.style}-${index}`"
        class="suggestion-card"
      >
        <div class="suggestion-card-head">
          <span>{{ item.style }}</span>
          <button
            type="button"
            :disabled="blocked"
            @click="$emit('copy', item.text)"
          >
            {{ blocked ? '风险拦截' : '复制话术' }}
          </button>
        </div>
        <p>{{ item.text }}</p>
      </article>

      <div v-if="suggestion.sources?.length" class="suggestion-sources">
        <span>知识来源</span>
        <div v-for="source in suggestion.sources" :key="source.knowledge_id || source.title">
          <strong>{{ source.title }}</strong>
          <em>{{ source.rank }}</em>
        </div>
      </div>
      <div v-else class="source-miss">本轮未命中知识库，请人工核对业务信息。</div>
    </div>

    <div v-else class="ai-empty">
      <span class="ai-orb small">AI</span>
      <strong>还没有建议</strong>
      <p>新消息进入时会自动生成一次，也可以现在手动生成。</p>
      <button class="soft-action" type="button" @click="$emit('regenerate')">生成建议</button>
    </div>

    <p class="ai-disclaimer">仅供人工参考。请在飞鸽中审核后发送，复制只记录统计，不会向买家外发。</p>
  </section>
</template>
