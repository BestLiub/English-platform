<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const current = computed(() => (route.name === 'immersion' ? 'immersion' : 'plan'))
const tabs = [
  { key: 'plan', label: '计划模式', to: '/study' },
  { key: 'immersion', label: '沉浸模式', to: '/study/immersion' }
]
</script>

<template>
  <div class="mb-8 inline-flex rounded-lg border p-0.5">
    <router-link
      v-for="tab in tabs"
      :key="tab.key"
      :to="tab.to"
      class="whitespace-nowrap rounded-md px-4 py-1.5 text-sm transition-colors"
      :class="current === tab.key ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'"
    >
      {{ tab.label }}
    </router-link>
  </div>
</template>
