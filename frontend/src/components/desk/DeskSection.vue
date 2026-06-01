<script setup>
// A named form section: bold uppercase title + thin separator + two-column field grid
// (default 2; tunable via cols). Matches Frappe Desk's form section pattern.
//
// Tailwind JIT note: the grid-cols class strings must be present in source as-is for
// the compiler to pick them up — the `gridClass` computed below explicitly enumerates
// the supported column counts rather than interpolating `grid-cols-${cols}`.

import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  cols: { type: Number, default: 2 },              // 1, 2, 3, or 4
})

const gridClass = computed(() => ({
  1: 'grid-cols-1',
  2: 'grid-cols-1 md:grid-cols-2',
  3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
}[props.cols] || 'grid-cols-1 md:grid-cols-2'))
</script>

<template>
  <section class="mb-6">
    <div v-if="title" class="mb-1">
      <h3 class="desk-section-title">{{ title }}</h3>
      <hr class="desk-divider" />
    </div>
    <div class="grid gap-x-6 gap-y-3" :class="gridClass">
      <slot />
    </div>
  </section>
</template>
