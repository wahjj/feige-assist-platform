<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  entry: { type: Object, default: null },
  products: { type: Array, default: () => [] },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['save', 'delete'])
const form = reactive({
  id: '',
  entry_type: '尺码表',
  title: '',
  content: '',
  keywords: '',
  product_id: '',
  category: '',
  enabled: true,
})

const types = ['尺码表', '面料与养护', '搭配建议', '售后规则', '常见问答', '商品知识']

watch(
  () => props.entry,
  (entry) => {
    Object.assign(form, {
      id: entry?.id || '',
      entry_type: entry?.entry_type || '尺码表',
      title: entry?.title || '',
      content: entry?.content || '',
      keywords: entry?.keywords || '',
      product_id: entry?.product_id || '',
      category: entry?.category || '',
      enabled: entry?.enabled ?? true,
    })
  },
  { immediate: true },
)

function save() {
  emit('save', { ...form, product_id: form.product_id || null })
}
</script>

<template>
  <form class="knowledge-editor" @submit.prevent="save">
    <div class="knowledge-editor-head">
      <div>
        <span class="panel-kicker">{{ form.id ? 'EDIT KNOWLEDGE' : 'NEW KNOWLEDGE' }}</span>
        <h2>{{ form.id ? '编辑知识条目' : '新增知识条目' }}</h2>
      </div>
      <label class="toggle-field">
        <input v-model="form.enabled" type="checkbox" />
        <span>{{ form.enabled ? '已启用' : '已停用' }}</span>
      </label>
    </div>

    <div class="knowledge-form-grid">
      <label class="field span-2"><span>标题</span><input v-model="form.title" required placeholder="例如：法式连衣裙尺码建议" /></label>
      <label class="field"><span>知识类型</span><select v-model="form.entry_type"><option v-for="type in types" :key="type">{{ type }}</option></select></label>
      <label class="field"><span>关联商品</span><select v-model="form.product_id" data-testid="knowledge-product"><option value="">不绑定具体商品</option><option v-for="product in products" :key="product.id" :value="product.id">{{ product.title }}</option></select></label>
      <label class="field"><span>适用分类</span><input v-model="form.category" placeholder="例如：连衣裙" /></label>
      <label class="field"><span>关键词</span><input v-model="form.keywords" placeholder="尺码,身高,体重" /></label>
      <label class="field span-2"><span>知识正文</span><textarea v-model="form.content" rows="11" required placeholder="输入客服可参考的准确尺码、面料或售后说明…" /></label>
    </div>

    <div class="knowledge-editor-note">
      此处内容仅用于中台 RAG 检索和 AI 建议，不会修改抖店商品资料。
    </div>
    <div class="knowledge-editor-actions">
      <button v-if="form.id" class="button button-ghost danger-outline" type="button" @click="$emit('delete', form.id)">删除条目</button>
      <button class="button button-primary" :disabled="saving">{{ saving ? '保存中…' : '保存知识' }}</button>
    </div>
  </form>
</template>
