<script setup>
// Shared workspace shortcut tile. Session 40 — extracted from
// SiteExecutionWorkspace.vue so every workspace landing (Site Execution,
// the 11 PlaceholderView-backed workspaces, AccountingWorkspace, and the
// Reports group) renders the same tile shape:
//
//   [icon]  Label                              →
//           one-line description in ink-500
//
// Visual standard (matches the frappe-ui / Frappe Cloud feel locked in S37):
//   - white background, ink-200 border, 8px rounded corners
//   - hover → brand-400 border + slight shadow + label flips to brand-700
//   - 3xl emoji icon on the left, generous p-4 padding
//   - right arrow in ink-300, hovers to brand-500
//   - description is optional; tiles without it stay vertically clean
//
// External / non-router targets pass `href` instead of `to`. `prevent` is
// used by the AccountingWorkspace stubs whose shortcut targets aren't wired
// in the prototype.

import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  to:          { type: [String, Object], default: null },
  href:        { type: String, default: null },
  icon:        { type: String, default: '📌' },
  label:       { type: String, required: true },
  description: { type: String, default: '' },
  // Set true when the click should NOT navigate (stub tiles, e.g.
  // AccountingWorkspace's illustrative shortcuts).
  prevent:     { type: Boolean, default: false },
})

const tag = computed(() => {
  if (props.prevent) return 'a'
  if (props.to)       return RouterLink
  return 'a'
})
const bindings = computed(() => {
  if (props.prevent) return { href: props.href || '#' }
  if (props.to)       return { to: props.to }
  return { href: props.href || '#' }
})

function onClick(e) {
  if (props.prevent) e.preventDefault()
}
</script>

<template>
  <component
    :is="tag"
    v-bind="bindings"
    class="bg-white border border-ink-200 hover:border-brand-400 hover:shadow-sm p-4 transition-all group block"
    style="border-radius: 8px;"
    @click="onClick"
  >
    <div class="flex items-start gap-3">
      <div class="text-3xl leading-none flex-shrink-0">{{ icon }}</div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <div class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors">{{ label }}</div>
          <slot name="badge" />
        </div>
        <div v-if="description" class="text-[11px] text-ink-500 mt-1 leading-snug">{{ description }}</div>
        <slot />
      </div>
      <div class="text-ink-300 group-hover:text-brand-500 transition-colors">→</div>
    </div>
  </component>
</template>
