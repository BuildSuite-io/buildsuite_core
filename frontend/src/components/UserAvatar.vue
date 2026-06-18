<script setup>
import { computed } from 'vue'
import { useDataStore } from '@/stores'
import { useUserNames } from '@/composables/useUserNames'
import { getFrappeHost } from '@/utils/session'

const props = defineProps({
  userId: String,
  // Optional explicit display name. When omitted, the name is resolved from the
  // prototype team store, then the real-user directory, then falls back to the id.
  name: { type: String, default: '' },
  // Optional explicit image URL; otherwise resolved from the user directory.
  image: { type: String, default: '' },
  size: { type: String, default: 'sm' }, // xs, sm, md, lg
  showName: { type: Boolean, default: false },
})

const store = useDataStore()
const { userName, userImage } = useUserNames()

// Saved profile image (User.user_image). Frappe stores a site-relative path
// (/files/… or /private/files/…) which needs the frappe host in dev.
const imageUrl = computed(() => {
  const raw = props.image || (props.userId ? userImage(props.userId) : '')
  if (!raw) return ''
  return raw.startsWith('/') ? `${getFrappeHost()}${raw}` : raw
})

// Prototype team member (demo users) — keeps their hand-picked initials/color.
const member = computed(() => store.teamMember(props.userId))

const displayName = computed(() =>
  props.name || member.value?.name || (props.userId ? userName(props.userId) : '')
)

const initials = computed(() => {
  if (member.value?.initials) return member.value.initials
  const n = displayName.value
  if (n && n !== props.userId) {
    const parts = n.trim().split(/\s+/).filter(Boolean)
    const ini = ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase()
    if (ini) return ini
  }
  return props.userId ? props.userId[0].toUpperCase() : '?'
})

// Deterministic color for real users (prototype members keep their own color).
const PALETTE = [
  'bg-blue-600', 'bg-violet-600', 'bg-amber-600', 'bg-rose-600',
  'bg-emerald-600', 'bg-cyan-600', 'bg-fuchsia-600', 'bg-indigo-600',
]
function hashColor(s) {
  let h = 0
  for (const ch of (s || '?')) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return PALETTE[h % PALETTE.length]
}
const colorClass = computed(() => member.value?.color || hashColor(props.userId || displayName.value))

const hasUser = computed(() => !!(props.userId || props.name || member.value))

const sizeClass = computed(() => ({
  xs: 'w-5 h-5 text-[10px]',
  sm: 'w-7 h-7 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-12 h-12 text-base',
}[props.size]))
</script>

<template>
  <div v-if="hasUser" class="inline-flex items-center gap-2">
    <img
      v-if="imageUrl"
      :src="imageUrl"
      :alt="displayName"
      :class="[sizeClass, 'rounded-full object-cover flex-shrink-0']"
    />
    <div v-else :class="[sizeClass, colorClass, 'rounded-full flex items-center justify-center text-white font-medium flex-shrink-0']">
      {{ initials }}
    </div>
    <span v-if="showName" class="text-sm text-ink-700">{{ displayName }}</span>
  </div>
  <div v-else class="inline-flex items-center gap-2">
    <div :class="[sizeClass, 'rounded-full bg-ink-200 text-ink-500 flex items-center justify-center font-medium']">?</div>
    <span v-if="showName" class="text-sm text-ink-400">Unassigned</span>
  </div>
</template>
