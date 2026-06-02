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
import { getWorkspaceIconPath, resolveWorkspaceIconSlug } from '@/utils/workspaceIcons'

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
const iconSlug = computed(() => resolveWorkspaceIconSlug(props.icon))

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
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-lg bg-ink-50 group-hover:bg-brand-50 text-ink-600 group-hover:text-brand-700 flex items-center justify-center flex-shrink-0 transition-colors">
        <svg
          class="w-5 h-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          v-html="getWorkspaceIconPath(iconSlug)"
        />
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <div class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors">{{ label }}</div>
          <slot name="badge" />
        </div>
        <div v-if="description" class="text-[11px] text-ink-500 mt-1 leading-snug">{{ description }}</div>
        <slot />
      </div>
      <svg
        class="w-4 h-4 text-ink-300 group-hover:text-brand-500 transition-colors"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m9 6 6 6-6 6" />
      </svg>
    </div>
  </component>
</template>
