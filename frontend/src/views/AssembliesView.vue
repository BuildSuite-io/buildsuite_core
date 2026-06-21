<script setup>

import { computed, ref } from 'vue'
import { useDocTypeList } from '@/composables/useDocTypeList'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { fmtINR } from '@/utils/format'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'

const { selectOptions } = useDoctypeMeta('Assembly')
const categoryOptions = computed(() => selectOptions('category'))

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Assembly' },
]

const assembliesRes = useDocTypeList('Assembly', {
  fields: ['name', 'assembly_code', 'assembly_name', 'category', 'uom', 'rate_per_unit', 'component_count', 'notes'],
  orderBy: 'assembly_code asc',
  pageLength: 0,
  cache: 'buildsuite-assembly-list',
  transform: (data) =>
    data.map((a) => ({
      id: a.name,
      code: a.assembly_code,
      name: a.assembly_name,
      category: a.category,
      unit: a.uom,
      ratePerUnit: a.rate_per_unit,
      componentCount: a.component_count,
      notes: a.notes
    })),
})

const search = ref('')
const categoryFilter = ref('')
const rows = computed(() => {
  let data = assembliesRes.data || []
  if (categoryFilter.value) data = data.filter((a) => a.category === categoryFilter.value)
  const q = search.value.trim().toLowerCase()
  if (q) {
    data = data.filter(
      (a) => (a.code || '').toLowerCase().includes(q) || (a.name || '').toLowerCase().includes(q),
    )
  }
  return data
})

const columns = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Name' },
  { key: 'category', label: 'Category' },
  { key: 'unit', label: 'Unit' },
  { key: 'componentCount', label: 'Components', align: 'right' },
  { key: 'ratePerUnit', label: 'Rate / unit', align: 'right' },
]
</script>

<template>
  <DeskPage title="Assembly" :breadcrumbs="breadcrumbs">
    <template #actions>
      <DeskLink to="/rate-master" class="text-xs">View Rate Master →</DeskLink>
      <RouterLink to="/assembly/new" class="desk-save-btn">+ New</RouterLink>

    </template>

    <DeskList v-model="search" :rows="rows" :columns="columns" row-key="id"
      search-placeholder="Search by code or name…">
      <template #filter-chips>
        <DeskSelect v-if="!categoryFilter" v-model="categoryFilter" class="!w-40">
          <option value="">Category: Any</option>
          <option v-for="c in categoryOptions" :key="c">{{ c }}</option>
        </DeskSelect>
        <DeskFilterChip v-else label="Category" :value="categoryFilter" @remove="categoryFilter = ''" />
      </template>

      <template #cell-code="{ row }">
        <span class="font-mono text-xs text-ink-800">{{ row.code }}</span>
      </template>
      <template #cell-name="{ row }">
        <span class="text-ink-900 font-medium">{{ row.name }}</span>
        <div v-if="row.notes" class="text-[11px] text-ink-500 truncate">{{ row.notes }}</div>
      </template>
      <template #cell-category="{ row }">
        <span v-if="row.category" class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-700 font-medium"
          style="border-radius: 9999px;">{{ row.category }}</span>
        <span v-else class="text-ink-300">—</span>
      </template>
      <template #cell-unit="{ row }">
        <span class="text-ink-600 text-xs">{{ row.unit }}</span>
      </template>
      <template #cell-componentCount="{ row }">
        <span class="text-xs text-ink-700 tabular-nums">{{ row.componentCount || 0 }}</span>
      </template>
      <template #cell-ratePerUnit="{ row }">
        <span class="text-sm font-medium text-ink-900 tabular-nums">{{ fmtINR(row.ratePerUnit) }}</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          {{ assembliesRes.loading ? 'Loading assemblies…' : 'No assemblies match your filters.' }}
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
