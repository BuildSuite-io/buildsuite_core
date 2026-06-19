<script setup>
// Estimation workspace — date + title, BOQ shortcut, and a "Setup" group.
// Setup has only Rate Master for now (Assembly + Estimate Templates come later).

import { computed } from 'vue'
import WorkspaceShortcut from '@/components/WorkspaceShortcut.vue'

const today = computed(() =>
  new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }),
)

const ESTIMATES = [
  { to: '/boq', icon: 'chart-bar', label: 'BOQ' },
]
const SETUP = [
  { to: '/rate-master', icon: 'tag', label: 'Rate Master', description: 'Price book for materials, labour, and equipment.' },
]
</script>

<template>
  <div class="bg-white min-h-full">
    <div class="max-w-6xl mx-auto px-6 py-8">
      <div class="mb-6">
        <div class="text-xs text-ink-500 mb-1">{{ today }}</div>
        <h1 class="text-2xl font-semibold text-ink-900">Estimation</h1>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
        <WorkspaceShortcut
          v-for="sc in ESTIMATES"
          :key="sc.to"
          :to="sc.to"
          :icon="sc.icon"
          :label="sc.label"
        />
      </div>

      <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">Setup</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <WorkspaceShortcut
          v-for="sc in SETUP"
          :key="sc.to"
          :to="sc.to"
          :icon="sc.icon"
          :label="sc.label"
          :description="sc.description"
        />
      </div>
    </div>
  </div>
</template>
