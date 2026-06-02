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

const resolvedFields = computed(() => {
  return Array.from(new Set([props.valueField, props.labelField, ...resolvedSearchFields.value]))
})

const serverFilters = computed(() => props.filters)

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
  const rows = optionsResource.data || []
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

function clearSelection(closePopover) {
  emit('update:modelValue', '')
  emit('change', '')
  closePopover()
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
      :body-classes="'!bg-white border border-ink-200 shadow-lg'"
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

      <template #footer="{ close }">
        <div class="border-t border-ink-200 p-1">
          <button
            v-if="selectedOption?.value !== '' && selectedOption?.value != null"
            type="button"
            class="w-full rounded px-2 py-1 text-left text-xs text-ink-600 hover:bg-ink-50"
            @click="clearSelection(close)"
          >
            Clear
          </button>
        </div>
      </template>
    </Autocomplete>
  </div>
</template>

<style scoped>
.desk-link-picker :deep(.bg-surface-modal) {
  background-color: #ffffff !important;
  opacity: 1 !important;
}

.desk-link-picker :deep(.sticky.bg-surface-modal) {
  background-color: #ffffff !important;
}
</style>
