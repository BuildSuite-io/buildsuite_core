<script setup>
import { computed, ref, watch } from 'vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import { fmtDate } from '@/utils/format'
import { useDocTypeList } from '@/composables/useDocTypeList'

const props = defineProps({
  doctype: { type: String, required: true },
  fieldOrder: { type: Array, required: true },
  searchFields: { type: Array, default: () => ['name'] },
  baseFilters: { type: Array, default: () => [] },
  filterValues: { type: Object, default: () => ({}) },
  filterFieldMap: { type: Object, default: () => ({}) },
  pageLength: { type: Number, default: 100 },
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

const resolvedFields = computed(() => {
  const valid = props.fieldOrder.filter((fieldname) => fieldMetaMap.value.has(fieldname))
  const withName = valid.includes('name') ? valid : ['name', ...valid]
  return Array.from(new Set(withName))
})

const resolvedColumns = computed(() => {
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

function formatValue(row, fieldname) {
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

        <DeskSelect v-model="sortField" class="!w-44" :disabled="!sortableFields.length">
          <option v-if="!sortableFields.length" value="">Sort: unavailable</option>
          <option
            v-for="option in sortableFields"
            :key="option.value"
            :value="option.value"
          >
            Sort: {{ option.label }}
          </option>
        </DeskSelect>

        <DeskSelect v-model="sortDirection" class="!w-32">
          <option value="desc">Order: Desc</option>
          <option value="asc">Order: Asc</option>
        </DeskSelect>
      </template>

      <template
        v-for="column in resolvedColumns"
        :key="column.key"
        #[`cell-${column.key}`]="slotProps"
      >
        <slot :name="`cell-${column.key}`" v-bind="slotProps">
          <span>{{ formatValue(slotProps.row, column.key) }}</span>
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
