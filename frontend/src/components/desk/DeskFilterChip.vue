<script setup>
// A single removable filter chip for the DeskList filter bar. Rounded-full pill
// with brand-50 background, brand-700 text, and an X to remove. Renders as
// `label` or `label: value` when value is non-empty.
//
// Session 37 — pill shape (border-radius: 9999px) matching the Frappe Cloud
// reference; the prior 2px-corner block style was replaced as part of the
// §12.4 visual revision.

defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '' },
})
defineEmits(['remove'])
</script>

<template>
  <span
    class="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 leading-4 bg-brand-50 text-brand-700"
    style="border-radius: 9999px;"
  >
    <span class="truncate max-w-[12rem]">
      {{ label }}<template v-if="value !== '' && value != null">: <strong class="font-semibold">{{ value }}</strong></template>
    </span>
    <button
      type="button"
      class="text-brand-700 hover:text-brand-800 leading-none"
      style="font-size: 14px;"
      aria-label="Remove filter"
      @click="$emit('remove')"
    >×</button>
  </span>
</template>
