<script setup>
import { computed, ref, watch } from 'vue'
import DeskList from '@/components/desk/DeskList.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fmtDate } from '@/utils/format'
import { useDocTypeList } from '@/composables/useDocTypeList'

const props = defineProps({
  doctype: { type: String, required: true },
  fieldOrder: { type: Array, required: true },
  columns: { type: Array, default: null },
  searchFields: { type: Array, default: () => ['name'] },
  baseFilters: { type: Array, default: () => [] },
  filterValues: { type: Object, default: () => ({}) },
  filterFieldMap: { type: Object, default: () => ({}) },
  pageLength: { type: Number, default: 100 },
  paginated: { type: Boolean, default: true },
  pageSize: { type: Number, default: 10 },
  pageSizeOptions: { type: Array, default: () => [10, 20, 50, 100] },
  cacheKey: { type: [String, Array], default: null },
  initialOrderBy: { type: String, default: '' },
  rowKey: { type: String, default: 'name' },
  searchPlaceholder: { type: String, default: 'Search' },
  emptyMessage: { type: String, default: 'No records found' },
})

const emit = defineEmits(['row-click'])

const search = ref('')
const meta = ref(null)
const metaError = ref(null)
const metaLoading = ref(false)

const sortField = ref('')
const sortDirection = ref('desc')

async function loadMeta() {
  metaLoading.value = true
  metaError.value = null
  try {
    const response = await fetch(
      `/api/method/frappe.desk.form.load.getdoctype?doctype=${encodeURIComponent(props.doctype)}&with_parent=1`,
      {
        method: 'GET',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'X-Frappe-CSRF-Token': window.csrf_token || '',
        },
      },
    )

    if (!response.ok) {
      throw new Error(`Meta fetch failed with status ${response.status}`)
    }

    const payload = await response.json()
    meta.value = payload?.docs?.[0] || payload?.message || null
  } catch (error) {
    metaError.value = error
    meta.value = null
    console.warn('[buildsuite] Failed to fetch doctype meta', error)
  } finally {
    metaLoading.value = false
  }
}

const systemFields = [
  { fieldname: 'name', label: 'ID', fieldtype: 'Data' },
  { fieldname: 'owner', label: 'Owner', fieldtype: 'Link' },
  { fieldname: 'modified', label: 'Updated', fieldtype: 'Datetime' },
  { fieldname: 'creation', label: 'Created', fieldtype: 'Datetime' },
]

const fieldMetaMap = computed(() => {
  const map = new Map()
  for (const f of systemFields) map.set(f.fieldname, f)
  for (const f of meta.value?.fields || []) {
    if (f?.fieldname) map.set(f.fieldname, f)
  }
  return map
})

const configuredColumns = computed(() => {
  if (!Array.isArray(props.columns) || !props.columns.length) return null
  return props.columns.filter((column) => column?.key)
})

const resolvedFields = computed(() => {
  const candidates = configuredColumns.value
    ? configuredColumns.value.flatMap((column) => {
        if (Array.isArray(column.fields) && column.fields.length) return column.fields
        return [column.key]
      })
    : props.fieldOrder

  const valid = candidates.filter((fieldname) => fieldMetaMap.value.has(fieldname))
  const withName = valid.includes('name') ? valid : ['name', ...valid]
  return Array.from(new Set(withName))
})

function defaultColumnLabel(column) {
  const fallbackField = Array.isArray(column.fields) && column.fields.length ? column.fields[0] : column.key
  const metaField = fieldMetaMap.value.get(fallbackField)
  return column.label || metaField?.label || column.key
}

function defaultColumnAlign(column) {
  if (column.align) return column.align

  if (column.preset === 'progress') return 'right'
  if (column.preset === 'timeline') return 'left'

  const fallbackField = Array.isArray(column.fields) && column.fields.length ? column.fields[0] : column.key
  const fieldtype = fieldMetaMap.value.get(fallbackField)?.fieldtype
  const numericTypes = ['Currency', 'Float', 'Int', 'Percent']
  return numericTypes.includes(fieldtype) ? 'right' : 'left'
}

const resolvedColumns = computed(() => {
  if (configuredColumns.value) {
    return configuredColumns.value.map((column) => ({
      key: column.key,
      label: defaultColumnLabel(column),
      align: defaultColumnAlign(column),
      preset: column.preset || '',
      fields: Array.isArray(column.fields) ? column.fields : [],
      renderer: column.renderer || null,
      rendererProps: column.rendererProps || null,
    }))
  }

  return resolvedFields.value.map((fieldname) => {
    const metaField = fieldMetaMap.value.get(fieldname) || {}
    const numericTypes = ['Currency', 'Float', 'Int', 'Percent']
    return {
      key: fieldname,
      label: metaField.label || fieldname,
      align: numericTypes.includes(metaField.fieldtype) ? 'right' : 'left',
    }
  })
})

const serverFilters = computed(() => {
  const filters = [...props.baseFilters]
  for (const [key, value] of Object.entries(props.filterValues || {})) {
    if (!value) continue
    const fieldname = props.filterFieldMap?.[key]
    if (!fieldname) continue
    filters.push([fieldname, '=', value])
  }
  return filters
})

const sortableFields = computed(() => {
  const base = new Set()
  const sortFieldFromMeta = meta.value?.sort_field
  if (sortFieldFromMeta && fieldMetaMap.value.has(sortFieldFromMeta)) {
    base.add(sortFieldFromMeta)
  }

  const sortableTypes = new Set(['Date', 'Datetime', 'Currency', 'Float', 'Int', 'Percent', 'Data', 'Link', 'Select', 'Check'])
  for (const fieldname of resolvedFields.value) {
    const field = fieldMetaMap.value.get(fieldname)
    if (!field) continue
    if (sortableTypes.has(field.fieldtype)) {
      base.add(fieldname)
    }
  }

  if (fieldMetaMap.value.has('modified')) {
    base.add('modified')
  }

  return Array.from(base).map((fieldname) => {
    const field = fieldMetaMap.value.get(fieldname)
    return {
      value: fieldname,
      label: field?.label || fieldname,
    }
  })
})

const resource = useDocTypeList(props.doctype, {
  fields: props.fieldOrder,
  filters: serverFilters.value,
  orderBy: props.initialOrderBy || 'modified desc',
  pageLength: props.pageLength,
  cache: props.cacheKey || `doctype-list:${props.doctype}`,
  auto: true,
})

const parsedDefaultOrder = computed(() => {
  if (props.initialOrderBy) {
    const [field = 'modified', direction = 'desc'] = props.initialOrderBy.split(/\s+/)
    return { field, direction: direction.toLowerCase() === 'asc' ? 'asc' : 'desc' }
  }

  const field = meta.value?.sort_field || 'modified'
  const direction = (meta.value?.sort_order || 'desc').toLowerCase() === 'asc' ? 'asc' : 'desc'
  return { field, direction }
})

watch(
  parsedDefaultOrder,
  (next) => {
    if (!sortField.value) {
      sortField.value = next.field
      sortDirection.value = next.direction
    }
  },
  { immediate: true },
)

const activeOrderBy = computed(() => `${sortField.value || 'modified'} ${sortDirection.value}`)

watch(
  () => JSON.stringify(serverFilters.value),
  () => {
    resource.update({ filters: serverFilters.value })
    resource.reload()
  },
)

watch(
  () => resolvedFields.value.join(','),
  (next, prev) => {
    if (!prev || next === prev) return
    resource.update({ fields: resolvedFields.value })
    resource.reload()
  },
)

watch(
  activeOrderBy,
  (next, prev) => {
    if (!next || next === prev) return
    resource.update({ orderBy: next })
    resource.reload()
  },
)

watch(
  () => props.doctype,
  () => {
    loadMeta()
    resource.update({ doctype: props.doctype })
    resource.reload()
  },
)

loadMeta()

function getColumnValue(row, column) {
  if (!column) return null
  if (Array.isArray(column.fields) && column.fields.length) {
    return column.fields.map((fieldname) => row?.[fieldname])
  }
  return row?.[column.key]
}

function formatValue(row, fieldname, column = null) {
  const value = row?.[fieldname]
  if (value === null || value === undefined || value === '') return '—'

  const fieldtype = fieldMetaMap.value.get(fieldname)?.fieldtype
  if (fieldtype === 'Date' || fieldtype === 'Datetime') {
    return fmtDate(value)
  }
  if (fieldtype === 'Check') {
    return value ? 'Yes' : 'No'
  }
  if (fieldtype === 'Currency' || fieldtype === 'Float' || fieldtype === 'Int' || fieldtype === 'Percent') {
    const number = Number(value)
    return Number.isFinite(number) ? number.toLocaleString() : value
  }

  return value
}

function resolvePreset(column) {
  if (!column) return ''
  if (typeof column.renderer === 'string') return column.renderer
  return column.preset || ''
}

function getTimelineValues(row, column) {
  const [startField = 'expected_start_date', endField = 'expected_end_date'] = column?.fields || []
  return {
    start: row?.[startField],
    end: row?.[endField],
  }
}

function renderPresetText(row, column) {
  const preset = resolvePreset(column)
  if (preset === 'timeline') {
    const { start, end } = getTimelineValues(row, column)
    if (!start && !end) return '—'
    return `${start ? fmtDate(start) : '—'} -> ${end ? fmtDate(end) : '—'}`
  }

  if (preset === 'progress') {
    const value = Number(row?.[column.key])
    return Number.isFinite(value) ? `${value}%` : '—'
  }

  return formatValue(row, column.key, column)
}

function hasComponentRenderer(column) {
  return !!column?.renderer && typeof column.renderer !== 'string'
}

function getRendererProps(row, column) {
  return {
    row,
    column,
    value: getColumnValue(row, column),
    meta: fieldMetaMap.value.get(column.key) || null,
    ...(column?.rendererProps || {}),
  }
}

function progressValue(row, column) {
  const value = Number(row?.[column.key])
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, value))
}

function progressTone(row, column) {
  const value = progressValue(row, column)
  if (value >= 100) return 'bg-success-500'
  if (value >= 50) return 'bg-info-500'
  return 'bg-warning-500'
}

const filteredRows = computed(() => {
  const rows = resource.data || []
  const term = search.value.trim().toLowerCase()
  if (!term) return rows

  return rows.filter((row) => {
    return props.searchFields.some((fieldname) => {
      const raw = row?.[fieldname]
      if (raw === null || raw === undefined) return false
      return String(raw).toLowerCase().includes(term)
    })
  })
})

const listCountText = computed(() => `${filteredRows.value.length} of ${resource.data?.length ?? 0}`)
</script>

<template>
  <div>
    <div v-if="metaError" class="mb-2 text-xs text-danger-600">
      Failed to load {{ doctype }} metadata.
    </div>

    <DeskList
      v-model="search"
      :rows="filteredRows"
      :columns="resolvedColumns"
      :row-key="rowKey"
      :paginated="paginated"
      :page-size="pageSize"
      :page-size-options="pageSizeOptions"
      :search-placeholder="searchPlaceholder"
      :show-sort="false"
      @row-click="(row) => emit('row-click', row)"
    >
      <template #filter-chips>
        <slot
          name="filter-chips"
          :resource="resource"
          :meta="meta"
          :meta-loading="metaLoading"
          :fields="resolvedFields"
        />
      </template>

      <template #pre-columns-controls>
        <div
          class="flex items-center border border-ink-200 bg-white"
          style="border-radius: 6px; overflow: hidden;"
        >
          <button
            type="button"
            class="text-xs text-ink-600 hover:text-ink-900 hover:bg-ink-50 px-2.5 py-1 border-r border-ink-200 disabled:text-ink-300 disabled:hover:bg-white"
            :title="sortDirection === 'desc' ? 'Descending' : 'Ascending'"
            :disabled="!sortableFields.length"
            @click="sortDirection = sortDirection === 'desc' ? 'asc' : 'desc'"
          >{{ sortDirection === 'desc' ? '↓' : '↑' }}</button>

          <select
            v-model="sortField"
            class="text-xs text-ink-600 bg-white hover:bg-ink-50 pl-2.5 pr-7 py-1 appearance-none"
            :disabled="!sortableFields.length"
            style="border: none; outline: none; min-width: 9.5rem;"
            :title="!sortableFields.length ? 'Sort unavailable' : 'Sort field'"
          >
            <option v-if="!sortableFields.length" value="">Sort unavailable</option>
            <option
              v-for="option in sortableFields"
              :key="option.value"
              :value="option.value"
            >{{ option.label }}</option>
          </select>

          <span class="-ml-6 pointer-events-none text-ink-400 text-[10px]">▾</span>
        </div>
      </template>

      <template
        v-for="column in resolvedColumns"
        :key="column.key"
        #[`cell-${column.key}`]="slotProps"
      >
        <slot :name="`cell-${column.key}`" v-bind="slotProps">
          <component
            :is="column.renderer"
            v-if="hasComponentRenderer(column)"
            v-bind="getRendererProps(slotProps.row, column)"
          />

          <StatusBadge
            v-else-if="resolvePreset(column) === 'status'"
            :status="slotProps.row?.[column.key]"
          />

          <div
            v-else-if="resolvePreset(column) === 'progress'"
            class="flex items-center justify-end gap-2"
          >
            <div class="w-16 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
              <div
                class="h-full"
                :class="progressTone(slotProps.row, column)"
                :style="`width:${progressValue(slotProps.row, column)}%`"
              ></div>
            </div>
            <span class="text-xs text-ink-700 tabular-nums w-8 text-right">{{ renderPresetText(slotProps.row, column) }}</span>
          </div>

          <span
            v-else-if="resolvePreset(column) === 'timeline'"
            class="text-xs text-ink-500 whitespace-nowrap"
          >{{ renderPresetText(slotProps.row, column) }}</span>

          <span v-else>{{ formatValue(slotProps.row, column.key, column) }}</span>
        </slot>
      </template>

      <template #empty>
        <slot name="empty">
          <div class="text-sm text-ink-500">{{ emptyMessage }}</div>
        </slot>
      </template>
    </DeskList>

    <div class="mt-2 text-xs text-ink-500 tabular-nums">{{ listCountText }}</div>
  </div>
</template>
