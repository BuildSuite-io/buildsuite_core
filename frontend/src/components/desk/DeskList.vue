<script setup>
// List view — filter bar on top (search + filter chips + sort + columns +
// add-filter), then a table with generous row padding and hover-only row
// differentiation (no stripes). Pagination footer (page size selector + range
// indicator + prev/next) renders below the table when pagination is enabled
// AND the row set spans more than one page.
//
// The consumer passes pre-filtered/sorted rows in via props — DeskList only
// renders the chrome; it does not own filtering or sorting state. The sort
// and column buttons emit events so the consumer can wire up dropdown panels
// if/when they need them. The search input uses two-way binding via v-model.
//
// Custom cell rendering: pass `render(row)` for simple text transforms, OR
// provide a scoped slot named `cell-<columnKey>` for HTML / component
// rendering. The slot receives `{ row, value }`.
//
// Columns: [{ key, label, align?: 'left'|'right'|'center', render?: (row)=>string, class?: string }]

import { computed, ref, watch } from 'vue'

const props = defineProps({
  rows: { type: Array, required: true },
  columns: { type: Array, required: true },
  rowKey: { type: [String, Function], default: 'id' },
  modelValue: { type: String, default: '' },          // search v-model
  searchPlaceholder: { type: String, default: 'Search' },
  bulkSelect: { type: Boolean, default: false },
  selected: { type: Array, default: () => [] },       // selected row keys for bulk-select
  showSort: { type: Boolean, default: true },
  showColumns: { type: Boolean, default: true },
  showAddFilter: { type: Boolean, default: true },
  // Pagination. Opt out by passing `:paginated="false"` (small fixed lists
  // like Settings → Users don't need it). `pageSize` is the initial value;
  // the user can change it via the dropdown.
  paginated: { type: Boolean, default: true },
  pageSize: { type: Number, default: 10 },
  pageSizeOptions: { type: Array, default: () => [10, 20, 50, 100] },
})

const emit = defineEmits([
  'update:modelValue',
  'update:selected',
  'row-click',
  'add-filter',
  'sort',
  'toggle-columns',
])

function keyFor(row) {
  return typeof props.rowKey === 'function' ? props.rowKey(row) : row[props.rowKey]
}

const allSelected = computed(() =>
  props.rows.length > 0 && props.selected.length === props.rows.length
)

function toggleAll() {
  if (allSelected.value) emit('update:selected', [])
  else emit('update:selected', props.rows.map(keyFor))
}

function toggleRow(row) {
  const k = keyFor(row)
  const idx = props.selected.indexOf(k)
  const next = props.selected.slice()
  if (idx >= 0) next.splice(idx, 1)
  else next.push(k)
  emit('update:selected', next)
}

function isSelected(row) {
  return props.selected.includes(keyFor(row))
}

function alignClass(col) {
  return col.align === 'right' ? 'text-right'
    : col.align === 'center' ? 'text-center'
    : 'text-left'
}

// ----- Pagination ------------------------------------------------------------

const currentPage = ref(1)
const currentPageSize = ref(props.pageSize)

const totalPages = computed(() => {
  if (!props.paginated) return 1
  return Math.max(1, Math.ceil(props.rows.length / currentPageSize.value))
})

const pagedRows = computed(() => {
  if (!props.paginated) return props.rows
  const start = (currentPage.value - 1) * currentPageSize.value
  return props.rows.slice(start, start + currentPageSize.value)
})

const rangeStart = computed(() => {
  if (!props.rows.length) return 0
  return (currentPage.value - 1) * currentPageSize.value + 1
})
const rangeEnd = computed(() =>
  Math.min(currentPage.value * currentPageSize.value, props.rows.length)
)

// Clamp current page when rows shrink (filtering / search) so we don't end up
// past the last available page.
watch(() => props.rows.length, () => {
  if (currentPage.value > totalPages.value) currentPage.value = totalPages.value
})
// When the search input changes (consumer-driven), jump back to page 1 so
// the user sees their fresh result set from the start.
watch(() => props.modelValue, () => { currentPage.value = 1 })

function goPrev() { if (currentPage.value > 1) currentPage.value -= 1 }
function goNext() { if (currentPage.value < totalPages.value) currentPage.value += 1 }
function setPageSize(size) {
  currentPageSize.value = Number(size) || props.pageSize
  currentPage.value = 1
}

const showPagination = computed(() =>
  props.paginated && props.rows.length > Math.min(...props.pageSizeOptions)
)
</script>

<template>
  <div class="bg-white border border-ink-200" style="border-radius: 8px;">
    <!-- Filter bar — flat white background, pill inputs, soft small buttons -->
    <div class="border-b border-ink-200 px-3 py-2 flex items-center gap-2 flex-wrap">
      <!-- Search with leading magnifier icon -->
      <div class="relative">
        <svg
          class="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-400 pointer-events-none"
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
        </svg>
        <input
          type="text"
          :value="modelValue"
          :placeholder="searchPlaceholder"
          class="desk-input"
          style="width: 14rem; padding-left: 28px;"
          @input="emit('update:modelValue', $event.target.value)"
        />
      </div>
      <slot name="filter-chips" />
      <button
        v-if="showAddFilter"
        type="button"
        class="desk-link text-xs px-1.5"
        @click="emit('add-filter')"
      >+ Add filter</button>

      <div class="ml-auto flex items-center gap-1">
        <button
          v-if="showSort"
          type="button"
          class="text-xs text-ink-600 hover:text-ink-900 hover:bg-ink-50 px-2.5 py-1 border border-ink-200 bg-white"
          style="border-radius: 6px;"
          @click="emit('sort')"
        >Sort by ▾</button>

        <slot name="pre-columns-controls" />

        <button
          v-if="showColumns"
          type="button"
          class="text-xs text-ink-600 hover:text-ink-900 hover:bg-ink-50 px-2.5 py-1 border border-ink-200 bg-white"
          style="border-radius: 6px;"
          @click="emit('toggle-columns')"
        >Columns ▾</button>
        <!-- Consumer-supplied action button(s) sit at the far right, after
             Sort + Columns. Convention: primary "+ New / + Add" CTAs go here. -->
        <slot name="actions" />
      </div>
    </div>

    <!-- Table — no row stripes, hover-only row tint, generous vertical padding -->
    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="border-b border-ink-200">
            <th v-if="bulkSelect" class="w-9 px-3 py-2.5">
              <input
                type="checkbox"
                :checked="allSelected"
                aria-label="Select all rows"
                @change="toggleAll"
              />
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              class="text-[11px] uppercase tracking-wider font-medium text-ink-500 px-3 py-2.5 whitespace-nowrap"
              :class="alignClass(col)"
            >{{ col.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in pagedRows"
            :key="keyFor(row)"
            class="border-b border-ink-100 cursor-pointer hover:bg-brand-50/40 transition-colors"
            @click="emit('row-click', row)"
          >
            <td v-if="bulkSelect" class="w-9 px-3 py-3" @click.stop>
              <input
                type="checkbox"
                :checked="isSelected(row)"
                :aria-label="`Select row ${keyFor(row)}`"
                @change="toggleRow(row)"
              />
            </td>
            <td
              v-for="col in columns"
              :key="col.key"
              class="px-3 py-3 text-ink-800"
              :class="[alignClass(col), col.class || '']"
            >
              <slot
                :name="`cell-${col.key}`"
                :row="row"
                :value="row[col.key]"
              >{{ col.render ? col.render(row) : row[col.key] }}</slot>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td
              :colspan="columns.length + (bulkSelect ? 1 : 0)"
              class="px-3 py-12 text-center"
            >
              <slot name="empty">
                <div class="text-sm text-ink-500">No records found</div>
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination footer — only renders when there's more than one page worth -->
    <div
      v-if="showPagination"
      class="border-t border-ink-200 px-3 py-2 flex items-center gap-3 flex-wrap text-xs text-ink-600"
    >
      <div class="flex items-center gap-2">
        <span class="text-ink-500">Rows per page</span>
        <select
          :value="currentPageSize"
          class="text-xs border border-ink-200 bg-white text-ink-700 hover:bg-ink-50 cursor-pointer"
          style="border-radius: 6px; padding: 4px 8px;"
          @change="setPageSize($event.target.value)"
        >
          <option v-for="opt in pageSizeOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </div>

      <div class="text-ink-500 tabular-nums">
        Showing <span class="text-ink-800 font-medium">{{ rangeStart }}–{{ rangeEnd }}</span>
        of <span class="text-ink-800 font-medium">{{ rows.length }}</span>
      </div>

      <div class="ml-auto flex items-center gap-1">
        <button
          type="button"
          class="text-xs text-ink-700 hover:bg-ink-50 disabled:text-ink-300 disabled:hover:bg-transparent disabled:cursor-not-allowed border border-ink-200 bg-white"
          style="border-radius: 6px; padding: 4px 10px;"
          :disabled="currentPage <= 1"
          @click="goPrev"
        >‹ Prev</button>
        <span class="text-ink-500 tabular-nums px-2">
          Page <span class="text-ink-800 font-medium">{{ currentPage }}</span>
          of <span class="text-ink-800 font-medium">{{ totalPages }}</span>
        </span>
        <button
          type="button"
          class="text-xs text-ink-700 hover:bg-ink-50 disabled:text-ink-300 disabled:hover:bg-transparent disabled:cursor-not-allowed border border-ink-200 bg-white"
          style="border-radius: 6px; padding: 4px 10px;"
          :disabled="currentPage >= totalPages"
          @click="goNext"
        >Next ›</button>
      </div>
    </div>
  </div>
</template>
