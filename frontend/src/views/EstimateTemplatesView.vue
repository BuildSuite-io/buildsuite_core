<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDocTypeList } from '@/composables/useDocTypeList'
import { fmtINR, fmtDate } from '@/utils/format'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'

const router = useRouter()

function onRowClick(row) {
  router.push(`/estimate-template/${row.id}`)
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Estimate Template' },
]

const templatesRes = useDocTypeList('Estimate Template', {
  fields: ['name', 'template_code', 'template_name', 'project_type', 'enabled', 'row_count', 'estimated_total', 'modified'],
  orderBy: 'template_code asc',
  pageLength: 0,
  cache: 'buildsuite-estimate-template-list',
  transform: (data) =>
    data.map((t) => ({
      id: t.name,
      code: t.template_code,
      name: t.template_name,
      projectType: t.project_type,
      rows: t.row_count,
      estimated: t.estimated_total,
      updated: t.modified,
      enabled: t.enabled,
    })),
})

const search = ref('')
const rows = computed(() => {
  let data = templatesRes.data || []
  const q = search.value.trim().toLowerCase()
  if (q) {
    data = data.filter(
      (t) => (t.code || '').toLowerCase().includes(q) || (t.name || '').toLowerCase().includes(q),
    )
  }
  return data
})

const columns = [
  { key: 'code', label: 'Code' },
  { key: 'name', label: 'Name' },
  { key: 'projectType', label: 'Project Type' },
  { key: 'rows', label: 'Rows', align: 'right' },
  { key: 'estimated', label: 'Estimated', align: 'right' },
  { key: 'updated', label: 'Updated' },
  { key: 'enabled', label: 'Status' },
]
</script>

<template>
  <DeskPage title="Estimate Template" :breadcrumbs="breadcrumbs">
    <template #actions>
      <DeskLink to="/assembly" class="text-xs">View Assemblies →</DeskLink>
      <RouterLink to="/estimate-template/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <DeskList v-model="search" :rows="rows" :columns="columns" row-key="id"
      search-placeholder="Search by code or name…" @row-click="onRowClick">
      <template #cell-code="{ row }">
        <DeskLink :to="`/estimate-template/${row.id}`" class="font-mono text-xs" @click.stop>{{ row.code }}</DeskLink>
      </template>
      <template #cell-name="{ row }">
        <span class="text-ink-900 font-medium">{{ row.name }}</span>
      </template>
      <template #cell-projectType="{ row }">
        <span v-if="row.projectType" class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-700 font-medium"
          style="border-radius: 9999px;">{{ row.projectType }}</span>
        <span v-else class="text-ink-300">Any</span>
      </template>
      <template #cell-rows="{ row }">
        <span class="text-xs text-ink-700 tabular-nums">{{ row.rows || 0 }}</span>
      </template>
      <template #cell-estimated="{ row }">
        <span class="text-sm font-medium text-ink-900 tabular-nums">{{ fmtINR(row.estimated) }}</span>
      </template>
      <template #cell-updated="{ row }">
        <span class="text-xs text-ink-500 whitespace-nowrap">{{ fmtDate(row.updated) }}</span>
      </template>
      <template #cell-enabled="{ row }">
        <span v-if="row.enabled" class="text-[10px] px-2 py-0.5 bg-success-50 text-success-700 font-medium"
          style="border-radius: 9999px;">Enabled</span>
        <span v-else class="text-[10px] px-2 py-0.5 bg-ink-100 text-ink-500 font-medium"
          style="border-radius: 9999px;">Disabled</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          {{ templatesRes.loading ? 'Loading templates…' : 'No estimate templates yet.' }}
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
