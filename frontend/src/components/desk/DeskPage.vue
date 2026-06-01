<script setup>
// Page-level chrome for a Desk-styled page. Renders:
//   [ breadcrumb › trail        ]
//   [ Title  <StatusBadge>      <actions slot> ]
//   [ optional subtitle line    ]
//   [ slot: page body            ]
//
// Sharp corners on the outer container (Desk doesn't round its page chrome), tight
// vertical padding, white background. Place a DeskList, DeskForm, or freeform body
// inside via the default slot.

import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import StatusBadge from '@/components/StatusBadge.vue'

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  breadcrumbs: { type: Array, default: () => [] },     // [{ label, to? }]
  // Accepts a single status string OR an array of status strings (each rendered as a
  // StatusBadge inline with the title — useful for status + priority pairs).
  status: { type: [String, Array], default: '' },
})

const statusList = computed(() => {
  if (!props.status) return []
  return Array.isArray(props.status) ? props.status.filter(Boolean) : [props.status]
})
</script>

<template>
  <div class="desk-page">
    <nav
      v-if="breadcrumbs.length"
      class="text-[11px] text-ink-500 flex items-center gap-1.5 flex-wrap mb-1.5"
      aria-label="Breadcrumb"
    >
      <template v-for="(c, i) in breadcrumbs" :key="i">
        <RouterLink v-if="c.to" :to="c.to" class="desk-link">{{ c.label }}</RouterLink>
        <span v-else>{{ c.label }}</span>
        <span v-if="i < breadcrumbs.length - 1" class="text-ink-300">›</span>
      </template>
    </nav>

    <div class="flex items-start justify-between gap-3 mb-3">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <h1 class="text-base font-semibold text-ink-900 leading-tight">{{ title }}</h1>
          <StatusBadge v-for="s in statusList" :key="s" :status="s" />
        </div>
        <p v-if="subtitle" class="text-xs text-ink-500 mt-0.5">{{ subtitle }}</p>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0">
        <slot name="actions" />
      </div>
    </div>

    <slot />
  </div>
</template>
