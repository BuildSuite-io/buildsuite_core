<script setup>
import { computed } from 'vue'
import { useDataStore } from '@/stores'

const props = defineProps({
  userId: String,
  size: { type: String, default: 'sm' }, // xs, sm, md
  showName: { type: Boolean, default: false },
})

const store = useDataStore()
const user = computed(() => store.teamMember(props.userId))
const sizeClass = computed(() => ({
  xs: 'w-5 h-5 text-[10px]',
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
}[props.size]))
</script>

<template>
  <div v-if="user" class="inline-flex items-center gap-2">
    <div :class="[sizeClass, user.color, 'rounded-full flex items-center justify-center text-white font-medium flex-shrink-0']">
      {{ user.initials }}
    </div>
    <span v-if="showName" class="text-sm text-ink-700">{{ user.name }}</span>
  </div>
  <div v-else class="inline-flex items-center gap-2">
    <div :class="[sizeClass, 'rounded-full bg-ink-200 text-ink-500 flex items-center justify-center font-medium']">?</div>
    <span v-if="showName" class="text-sm text-ink-400">Unassigned</span>
  </div>
</template>
