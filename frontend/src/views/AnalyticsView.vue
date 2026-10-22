<script setup>
import { computed, onMounted, ref } from 'vue'

import { get } from '../api'
import Icon from '../components/Icon.vue'

const analytics = ref(null)
const loading = ref(true)

const maxTopic = computed(() =>
  Math.max(1, ...(analytics.value?.top_topics || []).map((item) => item.count)),
)
const maxProduct = computed(() =>
  Math.max(1, ...(analytics.value?.product_mentions || []).map((item) => item.conversations)),
)

onMounted(async () => {
  try {
    analytics.value = await get('/api/analytics')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-if="loading" class="loading-state">正在汇总中台业务数据…</div>
  <div v-else class="page-stack">
    <section class="page-heading">
      <div>
        <p class="eyebrow dark">MIDDLE-PLATFORM ANALYTICS</p>
        <h1>业务分析</h1>
        <p>只看中台独有数据：咨询主题、知识命中、AI 使用和同步质量。</p>
      </div>
      <div class="heading-side-note"><Icon name="chart" :size="16" /> 不包含飞鸽客服绩效</div>
    </section>

    <section class="stats-grid analytics-stats">
      <article class="stat-card"><div class="stat-icon stat-green"><Icon name="chat" :size="21" /></div><div class="stat-copy"><span>今日消息</span><strong>{{ analytics.messages_today }}</strong><em>镜像入站消息</em></div></article>
      <article class="stat-card"><div class="stat-icon stat-sand">AI</div><div class="stat-copy"><span>建议生成</span><strong>{{ analytics.suggestions_generated }}</strong><em>包含历史种子</em></div></article>
      <article class="stat-card"><div class="stat-icon stat-rose">↗</div><div class="stat-copy"><span>建议复制</span><strong>{{ analytics.suggestions_copied }}</strong><em>复制不等于发送</em></div></article>
      <article class="stat-card"><div class="stat-icon stat-blue">!</div><div class="stat-copy"><span>风险拦截</span><strong>{{ analytics.suggestions_blocked }}</strong><em>敏感词与站外导流</em></div></article>
    </section>

    <section class="analytics-grid">
      <article class="panel analysis-card">
        <div class="panel-heading"><div><span class="panel-kicker">TOP TOPICS</span><h2>高频咨询主题</h2></div><span class="soft-tag">本地规则分类</span></div>
        <div class="bar-list">
          <div v-for="item in analytics.top_topics" :key="item.topic" class="bar-row">
            <span>{{ item.topic }}</span>
            <div><i :style="{ width: `${(item.count / maxTopic) * 100}%` }" /></div>
            <strong>{{ item.count }}</strong>
          </div>
        </div>
      </article>

      <article class="panel analysis-card">
        <div class="panel-heading"><div><span class="panel-kicker">PRODUCT INTEREST</span><h2>商品咨询分布</h2></div></div>
        <div class="bar-list product-bar-list">
          <div v-for="item in analytics.product_mentions" :key="item.title" class="bar-row">
            <span>{{ item.title }}</span>
            <div><i :style="{ width: `${(item.conversations / maxProduct) * 100}%` }" /></div>
            <strong>{{ item.conversations }}</strong>
          </div>
        </div>
      </article>

      <article class="panel analysis-card">
        <div class="panel-heading"><div><span class="panel-kicker">KNOWLEDGE HITS</span><h2>知识命中</h2></div></div>
        <div class="rank-list">
          <div v-for="(item, index) in analytics.knowledge_hits" :key="item.title">
            <span>{{ String(index + 1).padStart(2, '0') }}</span>
            <div><strong>{{ item.title }}</strong><small>{{ item.entry_type }}</small></div>
            <em>{{ item.hits }} 次</em>
          </div>
        </div>
      </article>

      <article class="panel analysis-card">
        <div class="panel-heading"><div><span class="panel-kicker">AFTER SALES</span><h2>售后原因</h2></div></div>
        <div class="after-sales-list">
          <div v-for="item in analytics.after_sales_reasons" :key="item.reason">
            <span>{{ item.reason }}</span><strong>{{ item.count }}</strong>
          </div>
          <div v-if="!analytics.after_sales_reasons.length" class="empty-copy">暂无同步售后原因。</div>
        </div>
      </article>

      <article class="panel analysis-card sync-quality-card">
        <div class="panel-heading"><div><span class="panel-kicker">SYNC QUALITY</span><h2>同步质量</h2></div></div>
        <div class="quality-grid">
          <div><span>Webhook 失败</span><strong>{{ analytics.webhook_failures }}</strong></div>
          <div><span>同步运行</span><strong>{{ analytics.manual_pull_count }}</strong></div>
          <div><span>活跃会话</span><strong>{{ analytics.active_conversations }}</strong></div>
        </div>
        <p>所有指标来自中台镜像。接待计时、响应率和分流绩效请在飞鸽查看。</p>
      </article>
    </section>
  </div>
</template>
