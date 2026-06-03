<script setup>
import { computed, ref, watch } from 'vue'
import { watchDebounced } from '@vueuse/core'
import Autocomplete from '../../../node_modules/frappe-ui/src/components/Autocomplete/Autocomplete.vue'
import { useDocTypeList } from '@/composables/useDocTypeList'

const props = defineProps({
  doctype: { type: String, required: true },
  modelValue: { type: [String, Number, null], default: '' },
  label: { type: String, default: '' },
  placeholder: { type: String, default: 'Select' },
  disabled: { type: Boolean, default: false },
  filters: { type: [Array, Object, String], default: () => [] },
  labelField: { type: String, default: 'name' },
  valueField: { type: String, default: 'name' },
  searchFields: { type: Array, default: () => [] },
  pageLength: { type: Number, default: 10 },
  maxOptions: { type: Number, default: 10 },
  orderBy: { type: String, default: '' },
  placement: { type: String, default: 'bottom-start' },
  size: { type: String, default: 'sm' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const query = ref('')

const resolvedSearchFields = computed(() => {
  const fields = props.searchFields.length
    ? props.searchFields
    : [props.labelField, props.valueField, 'name']
  return Array.from(new Set(fields.filter(Boolean)))
})

const filterFieldNames = computed(() => {
  const filters = props.filters
  if (!filters) return []

  if (!Array.isArray(filters) && typeof filters === 'object') {
    return Object.keys(filters)
  }

  if (!Array.isArray(filters)) return []

  return filters
    .map((f) => (Array.isArray(f) ? f[0] : null))
    .filter(Boolean)
})

const resolvedFields = computed(() => {
  return Array.from(new Set([
    props.valueField,
    props.labelField,
    ...resolvedSearchFields.value,
    ...filterFieldNames.value,
  ]))
})

const serverFilters = computed(() => props.filters)

function matchesFilterValue(actual, operator, expected) {
  if (operator === '=') {
    if (actual === expected) return true
    if (actual == null || expected == null) return false

    // Frappe list responses often mix numeric-like strings and numbers
    // (e.g. is_group as "1" vs filter value 1). Normalize before compare.
    const actualText = String(actual).trim()
    const expectedText = String(expected).trim()
    if (actualText === expectedText) return true

    const actualNum = Number(actualText)
    const expectedNum = Number(expectedText)
    if (!Number.isNaN(actualNum) && !Number.isNaN(expectedNum)) {
      return actualNum === expectedNum
    }

    return false
  }
  if (operator === 'like') {
    const needle = String(expected || '').replaceAll('%', '').toLowerCase()
    return String(actual || '').toLowerCase().includes(needle)
  }
  if (operator === 'in') {
    const candidates = Array.isArray(expected) ? expected : []
    return candidates.some((candidate) => matchesFilterValue(actual, '=', candidate))
  }
  return true
}

function applyClientFilters(rows, filters = []) {
  if (!filters || (Array.isArray(filters) && !filters.length)) return rows

  if (!Array.isArray(filters) && typeof filters === 'object') {
    return rows.filter((row) => {
      return Object.entries(filters).every(([fieldname, condition]) => {
        const actual = row?.[fieldname]
        if (Array.isArray(condition)) {
          const [operator = '=', expected] = condition
          return matchesFilterValue(actual, operator, expected)
        }
        return actual === condition
      })
    })
  }

  return rows.filter((row) => {
    return filters.every((f) => {
      const [fieldname, operator = '=', value] = f || []
      const actual = row?.[fieldname]
      return matchesFilterValue(actual, operator, value)
    })
  })
}

const serverOrFilters = computed(() => {
  const term = query.value.trim()
  if (!term) return []

  return resolvedSearchFields.value.map((fieldname) => [fieldname, 'like', `%${term}%`])
})

const listOrderBy = computed(() => props.orderBy || `${props.labelField} asc`)

const optionsResource = useDocTypeList(props.doctype, {
  fields: resolvedFields.value,
  filters: serverFilters.value,
  orFilters: serverOrFilters.value,
  orderBy: listOrderBy.value,
  pageLength: props.pageLength,
  auto: false,
})

const selectedResource = useDocTypeList(props.doctype, {
  fields: resolvedFields.value,
  filters: [[props.valueField, '=', props.modelValue]],
  orderBy: listOrderBy.value,
  pageLength: 1,
  auto: false,
})

const selectedRecord = computed(() => selectedResource.data?.[0] || null)

const selectedOption = computed(() => {
  const record = selectedRecord.value
  if (record) {
    return buildOption(record)
  }

  const currentValue = props.modelValue
  if (currentValue === '' || currentValue == null) return null
  return {
    label: String(currentValue),
    value: currentValue,
  }
})

const options = computed(() => {
  const rows = applyClientFilters(optionsResource.data || [], serverFilters.value)
  const mapped = rows.map(buildOption)
  if (!selectedOption.value) return mapped

  const selectedValue = selectedOption.value.value
  if (mapped.some((option) => option.value === selectedValue)) {
    return mapped
  }

  return [selectedOption.value, ...mapped]
})

const loading = computed(() => optionsResource.loading || selectedResource.loading)

watchDebounced(
  query,
  () => {
    optionsResource.update({
      fields: resolvedFields.value,
      filters: serverFilters.value,
      orFilters: serverOrFilters.value,
      orderBy: listOrderBy.value,
      pageLength: props.pageLength,
      start: 0,
    })
    optionsResource.list.fetch()
  },
  { debounce: 250, immediate: true },
)

watch(
  () => props.doctype,
  () => {
    query.value = ''
    optionsResource.update({
      fields: resolvedFields.value,
      filters: serverFilters.value,
      orFilters: [],
      orderBy: listOrderBy.value,
      pageLength: props.pageLength,
      start: 0,
    })
    optionsResource.list.fetch()
    fetchSelectedRecord()
  },
)

watch(
  () => props.filters,
  () => {
    optionsResource.update({
      fields: resolvedFields.value,
      filters: serverFilters.value,
      orFilters: serverOrFilters.value,
      orderBy: listOrderBy.value,
      pageLength: props.pageLength,
      start: 0,
    })
    optionsResource.list.fetch()
  },
  { deep: true },
)

watch(
  () => props.modelValue,
  () => {
    fetchSelectedRecord()
  },
  { immediate: true },
)

function fetchSelectedRecord() {
  if (props.modelValue === '' || props.modelValue == null) {
    selectedResource.setData([])
    return
  }

  selectedResource.update({
    fields: resolvedFields.value,
    filters: [[props.valueField, '=', props.modelValue]],
    orderBy: listOrderBy.value,
    pageLength: 1,
    start: 0,
  })
  selectedResource.list.fetch()
}

function buildOption(record) {
  const label = record?.[props.labelField] ?? record?.[props.valueField] ?? ''
  const value = record?.[props.valueField]
  return {
    label: label == null ? '' : String(label),
    value,
    description: record?.description || record?.abbr || '',
    record,
  }
}

function onChange(option) {
  const nextValue = option?.value ?? ''
  emit('update:modelValue', nextValue)
  emit('change', nextValue)
}

function onQueryUpdate(value) {
  query.value = value || ''
}
</script>

<template>
  <div class="space-y-1.5 min-w-0">
    <label v-if="label" class="block text-[11px] font-medium text-ink-700">
      {{ label }}
    </label>

    <Autocomplete
      class="desk-link-picker"
      :model-value="selectedOption"
      :options="options"
      :loading="loading"
      :max-options="maxOptions"
      :placement="placement"
      :hide-search="false"
      :body-classes="'desk-link-picker-popover !bg-white border border-ink-200 shadow-lg z-[80]'"
      :compare-fn="(a, b) => a?.value === b?.value"
      @change="onChange"
      @update:query="onQueryUpdate"
    >
      <template #target="{ togglePopover, isOpen }">
        <button
          type="button"
          class="flex h-7 w-full items-center justify-between gap-2 border border-ink-200 bg-white px-2 text-left text-sm text-ink-700 transition-colors hover:bg-ink-50"
          style="border-radius: 6px;"
          :class="{ 'ring-2 ring-brand-100 border-brand-300': isOpen, 'opacity-60 cursor-not-allowed': disabled }"
          :disabled="disabled"
          @click="togglePopover"
        >
          <span class="min-w-0 flex-1 truncate">
            {{ selectedOption?.label || placeholder }}
          </span>
          <span class="text-[10px] text-ink-400">▾</span>
        </button>
      </template>
    </Autocomplete>
  </div>
</template>

<style>
/* Reka popover renders through a portal wrapper; this wrapper must sit above
   modal overlays, otherwise the list appears to not open inside modals. */
[data-radix-popper-content-wrapper]:has(.desk-link-picker-popover),
.PopoverContent:has(.desk-link-picker-popover) {
  z-index: 80 !important;
}

.desk-link-picker-popover {
  background-color: #ffffff !important;
  opacity: 1 !important;
  z-index: 80 !important;
  border: 1px solid theme('colors.ink.200') !important;
  border-radius: 6px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
}

/* Force compact typography inside teleported popover */
.desk-link-picker-popover,
.desk-link-picker-popover * {
  font-size: 0.75rem !important;
  line-height: 1rem !important;
}

/* Tighter padding for list items to feel more like Desk */
.desk-link-picker-popover li {
  padding-top: 4px !important;
  padding-bottom: 4px !important;
  padding-left: 8px !important;
  padding-right: 8px !important;
}

/* Ensure the description/abbr is also small */
.desk-link-picker-popover li .text-sm {
  font-size: 0.6875rem !important;
}

/* Style the search input to match DeskInput */
.desk-link-picker-popover input.form-input {
  border-radius: 4px !important;
  border: 1px solid theme('colors.ink.200') !important;
  height: 24px !important;
  padding: 2px 8px !important;
  padding-right: 24px !important; /* space for x button */
}

.desk-link-picker-popover input.form-input:focus {
  border-color: #16A34A !important;
  box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.2) !important;
}

/* Fix the 'x' button alignment in the search bar */
.desk-link-picker-popover .relative.w-full > .absolute {
  top: 50% !important;
  transform: translateY(-50%) !important;
  right: 0px !important;
  height: 24px !important;
  width: 24px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.desk-link-picker-popover .relative.w-full > .absolute button {
  height: 100% !important;
  width: 100% !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.desk-link-picker-popover .relative.w-full > .absolute svg {
  width: 12px !important;
  height: 12px !important;
}

/* Hide groups if they are empty or styled weirdly */
.desk-link-picker-popover .truncate.bg-surface-modal {
  font-size: 11px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.025em !important;
  color: theme('colors.ink.400') !important;
  padding-top: 8px !important;
}

.desk-link-picker-popover .sticky.bg-surface-modal {
  background-color: #ffffff !important;
}
</style>
