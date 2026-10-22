<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 20 },
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'home'">
      <path d="M3.5 10.5 12 3l8.5 7.5" />
      <path d="M5.5 9.5V21h13V9.5M9.5 21v-6h5v6" />
    </template>
    <template v-else-if="name === 'product'">
      <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
      <path d="m4.2 7.7 7.8 4.5 7.8-4.5M12 12.2V21" />
    </template>
    <template v-else-if="name === 'order'">
      <path d="M7 3h10v18H7z" />
      <path d="M9.5 7h5M9.5 11h5M9.5 15h3" />
    </template>
    <template v-else-if="name === 'customer'">
      <circle cx="12" cy="8" r="3.3" />
      <path d="M5.5 20c.6-4 2.8-6 6.5-6s5.9 2 6.5 6" />
    </template>
    <template v-else-if="name === 'chat'">
      <path d="M4 5.5h16v11H9l-4.5 3v-3H4z" />
      <path d="M8 9h8M8 12.5h5" />
    </template>
    <template v-else-if="name === 'approval'">
      <path d="M5 3.5h14v17H5z" />
      <path d="m8 12 2.4 2.3L16 8.8" />
    </template>
    <template v-else-if="name === 'settings'">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6 7.2 7.2M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6" />
    </template>
    <template v-else-if="name === 'chart'">
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m15 15 5 5" />
    </template>
    <template v-else-if="name === 'bell'">
      <path d="M6.5 10c0-4 2-6 5.5-6s5.5 2 5.5 6v5l2 2h-15l2-2v-5Z" />
      <path d="M10 20h4" />
    </template>
    <template v-else-if="name === 'plus'">
      <path d="M12 5v14M5 12h14" />
    </template>
    <template v-else-if="name === 'arrow'">
      <path d="M5 12h14M14 7l5 5-5 5" />
    </template>
    <template v-else-if="name === 'refresh'">
      <path d="M20 7v5h-5M4 17v-5h5" />
      <path d="M6.1 8.3A7 7 0 0 1 19 12M5 12a7 7 0 0 0 12.9 3.7" />
    </template>
    <template v-else-if="name === 'send'">
      <path d="m3 4 18 8-18 8 3-8-3-8Z" />
      <path d="M6 12h15" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="8" />
    </template>
  </svg>
</template>
