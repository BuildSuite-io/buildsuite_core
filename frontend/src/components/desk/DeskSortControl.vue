<script setup>
const props = defineProps({
  sortField: { type: String, default: '' },
  sortDirection: { type: String, default: 'desc' },
  options: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:sortField', 'update:sortDirection'])

function toggleDirection() {
  emit('update:sortDirection', props.sortDirection === 'desc' ? 'asc' : 'desc')
}

function updateField(event) {
  emit('update:sortField', event.target.value)
}
</script>

<template>
  <div
    class="flex items-center border border-ink-200 bg-white"
    style="border-radius: 6px; overflow: hidden;"
  >
    <button
      type="button"
      class="text-xs text-ink-600 hover:text-ink-900 hover:bg-ink-50 px-2.5 py-1 border-r border-ink-200 disabled:text-ink-300 disabled:hover:bg-white"
      :title="sortDirection === 'desc' ? 'Descending' : 'Ascending'"
      :disabled="!options.length"
      @click="toggleDirection"
    >{{ sortDirection === 'desc' ? '↓' : '↑' }}</button>

    <select
      :value="sortField"
      class="text-xs text-ink-600 bg-white hover:bg-ink-50 pl-2.5 pr-7 py-1 appearance-none"
      :disabled="!options.length"
      style="border: none; outline: none; min-width: 9.5rem;"
      :title="!options.length ? 'Sort unavailable' : 'Sort field'"
      @change="updateField"
    >
      <option v-if="!options.length" value="">Sort unavailable</option>
      <option v-else-if="!sortField" value="">Sort by</option>
      <option
        v-for="option in options"
        :key="option.value"
        :value="option.value"
      >{{ option.label }}</option>
    </select>

    <span class="-ml-6 pointer-events-none text-ink-400 text-[10px]">▾</span>
  </div>
</template>
