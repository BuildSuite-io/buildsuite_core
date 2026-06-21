<script setup>
// Searchable single-select. Same visual shape as DeskSelect (the trigger
// looks like a desk-input with a chevron), but on click opens a popover
// with an inline search box that filters the options as the user types.
//
// Use this in place of DeskSelect when the underlying list is large enough
// to benefit from typeahead (projects, rate-master, assemblies, SCOs,
// templates, etc.). For short fixed enums (status / priority / cost head
// with 5-6 values), keep DeskSelect — overhead isn't worth it.
//
// API:
//   v-model         the selected value (string, number, or null)
//   :options        Array of { value, label, group?, hint? }
//                     group → renders under that optgroup label
//                     hint  → secondary line below the main label
//   :placeholder    text shown on the trigger when nothing is selected
//   :disabled       blocks the trigger
//   :allow-clear    when true, shows an × to clear the value
//   :search-placeholder  override for the search input placeholder
//
// Keyboard nav: ↑/↓ move highlight, Enter selects, Esc closes.

import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: null },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '— Select —' },
  disabled: { type: Boolean, default: false },
  allowClear: { type: Boolean, default: false },
  searchPlaceholder: { type: String, default: 'Search…' },
})
const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const search = ref('')
const highlightedIndex = ref(0)
const triggerRef = ref(null)
const searchRef = ref(null)
const listRef = ref(null)
const popoverStyle = ref({})

const selected = computed(() =>
  props.options.find(o => String(o.value) === String(props.modelValue))
)

// Filtered + grouped options. Returns an ordered flat array of:
//   { type: 'group', label }       ← optgroup header row (not selectable)
//   { type: 'option', ..., _idx }  ← actual row (selectable)
// _idx lets keyboard nav skip group headers.
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const passed = props.options.filter(o => {
    if (!q) return true
    const text = `${o.label || ''} ${o.hint || ''}`.toLowerCase()
    return text.includes(q)
  })
  // Preserve original group ordering: walk the original options array and
  // emit a group header the first time each group is seen among passed items.
  const out = []
  const seenGroups = new Set()
  const groupBuckets = new Map()
  for (const o of passed) {
    const g = o.group || ''
    if (!groupBuckets.has(g)) groupBuckets.set(g, [])
    groupBuckets.get(g).push(o)
  }
  let idx = 0
  for (const [g, items] of groupBuckets) {
    if (g && !seenGroups.has(g)) {
      seenGroups.add(g)
      out.push({ type: 'group', label: g })
    }
    for (const it of items) {
      out.push({ type: 'option', ...it, _idx: idx++ })
    }
  }
  return out
})
const selectableCount = computed(() => filtered.value.filter(r => r.type === 'option').length)

function positionPopover() {
  const el = triggerRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  popoverStyle.value = {
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 260)}px`,
  }
}

function open() {
  if (props.disabled) return
  isOpen.value = true
  search.value = ''
  const sel = props.options.findIndex(o => String(o.value) === String(props.modelValue))
  highlightedIndex.value = sel >= 0 ? sel : 0
  nextTick(() => {
    positionPopover()
    searchRef.value?.focus()
    scrollHighlightedIntoView()
  })
}
function close() { isOpen.value = false }

function selectOption(o) {
  emit('update:modelValue', o.value)
  close()
  triggerRef.value?.focus()
}

function clear() {
  emit('update:modelValue', null)
  close()
}

function scrollHighlightedIntoView() {
  const el = listRef.value?.querySelector('[data-highlighted="true"]')
  if (el && typeof el.scrollIntoView === 'function') {
    el.scrollIntoView({ block: 'nearest' })
  }
}

function onSearchKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (selectableCount.value === 0) return
    highlightedIndex.value = (highlightedIndex.value + 1) % selectableCount.value
    nextTick(scrollHighlightedIntoView)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (selectableCount.value === 0) return
    highlightedIndex.value = (highlightedIndex.value - 1 + selectableCount.value) % selectableCount.value
    nextTick(scrollHighlightedIntoView)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const row = filtered.value.find(r => r.type === 'option' && r._idx === highlightedIndex.value)
    if (row) selectOption(row)
  } else if (e.key === 'Escape') {
    e.preventDefault()
    close()
  }
}

watch(filtered, () => {
  if (highlightedIndex.value >= selectableCount.value) {
    highlightedIndex.value = Math.max(0, selectableCount.value - 1)
  }
})

watch(isOpen, (v) => { if (v) nextTick(positionPopover) })

function onBackdropClick() { close() }

onMounted(() => {
  window.addEventListener('scroll', positionPopover, true)
  window.addEventListener('resize', positionPopover)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', positionPopover, true)
  window.removeEventListener('resize', positionPopover)
})
</script>

<template>
  <div class="relative">
    <!-- Trigger — looks like desk-input with a chevron -->
    <button
      ref="triggerRef"
      type="button"
      class="desk-input text-left flex items-center justify-between gap-2"
      :class="{ 'opacity-50 cursor-not-allowed': disabled }"
      :disabled="disabled"
      @click="open"
    >
      <span v-if="selected" class="truncate text-ink-900">{{ selected.label }}</span>
      <span v-else class="truncate text-ink-400">{{ placeholder }}</span>
      <span class="flex items-center gap-1 flex-shrink-0">
        <button
          v-if="allowClear && selected"
          type="button"
          class="text-ink-400 hover:text-danger-700 text-xs leading-none px-1"
          aria-label="Clear"
          @click.stop="clear"
        >×</button>
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" class="text-ink-500">
          <path d="M1 1L5 5L9 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
    </button>

    <!-- Popover -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[70]"
        @click.self="onBackdropClick"
      >
        <div
          :style="popoverStyle"
          class="absolute bg-white border border-ink-200 shadow-fp-lg flex flex-col"
          style="border-radius: 8px; min-width: 260px; max-height: 360px;"
          @click.stop
        >
          <div class="px-2 py-1.5 border-b border-ink-100">
            <input
              ref="searchRef"
              v-model="search"
              type="text"
              class="desk-input"
              :placeholder="searchPlaceholder"
              @keydown="onSearchKeydown"
            />
          </div>
          <div ref="listRef" class="overflow-y-auto flex-1 py-1">
            <template v-if="filtered.length">
              <template v-for="(row, i) in filtered" :key="i">
                <div
                  v-if="row.type === 'group'"
                  class="px-3 py-1 text-[10px] uppercase tracking-wider text-ink-500 font-medium bg-ink-50"
                >{{ row.label }}</div>
                <button
                  v-else
                  type="button"
                  class="w-full text-left px-3 py-1.5 text-sm flex items-center justify-between gap-2"
                  :class="row._idx === highlightedIndex ? 'bg-brand-50 text-brand-700' : 'hover:bg-ink-50 text-ink-900'"
                  :data-highlighted="row._idx === highlightedIndex || null"
                  @click="selectOption(row)"
                  @mouseenter="highlightedIndex = row._idx"
                >
                  <span class="min-w-0 flex-1">
                    <span class="truncate block">{{ row.label }}</span>
                    <span v-if="row.hint" class="text-[11px] text-ink-500 truncate block">{{ row.hint }}</span>
                  </span>
                  <span v-if="String(row.value) === String(modelValue)" class="text-brand-700 text-xs flex-shrink-0">✓</span>
                </button>
              </template>
            </template>
            <div v-else class="px-3 py-3 text-xs text-ink-400 italic text-center">No matches.</div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
