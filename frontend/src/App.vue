<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from './components/AppShell.vue'

const route = useRoute()
const bare = computed(() => Boolean(route.meta.bare))
</script>

<template>
  <router-view v-if="bare" />
  <AppShell v-else>
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </AppShell>
</template>
