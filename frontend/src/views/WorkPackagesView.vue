<script setup>
// Work Packages list — migrated to the generic DocType list shell and
// adapter-backed project lookup filters.

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DocTypeListView from '@/components/doctype/DocTypeListView.vue'
import { fmtCompactINR } from '@/utils/format'
import { createDataAdapter } from '@/data/adapters'

const store = useDataStore()
const router = useRouter()
const projectFilter = ref('')

const adapter = createDataAdapter(store)

const projectsResource = adapter.list('Project', {
  fields: ['name', 'project_name', 'custom_project_id'],
  orderBy: 'project_name asc',
  pageLength: 100,
  cache: 'buildsuite-project-filter-options',
})

const projectRows = computed(() => {
  const raw = projectsResource.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
})

const projectLabelMap = computed(() => {
  const map = new Map()
  for (const p of projectRows.value) {
    const label = p?.project_name || p?.name
    if (p?.name) map.set(p.name, label)
  }
  return map
})

const filterValues = computed(() => ({
  project: projectFilter.value,
}))

// Schedule-based traffic-light for the progress bar.
function wpVariance(row) {
  if (!row?.start_date || !row?.end_date) return 0
  const today = new Date().getTime()
  const start = new Date(row.start_date).getTime()
  const end = new Date(row.end_date).getTime()
  const total = end - start
  if (total <= 0) return 0
  const elapsed = Math.max(0, Math.min(total, today - start))
  const expected = (elapsed / total) * 100
  if (expected <= 0) return 0
  return ((expected - (Number(row?.progress) || 0)) / expected) * 100
}

function progressBarColor(row) {
  const v = wpVariance(row)
  if (v > 15) return 'bg-danger-500'
  if (v > 5) return 'bg-warning-500'
  return 'bg-success-500'
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Work Package' },
]

function onRowClick(row) { router.push(`/app/work-packages/${row.name}`) }
</script>

<template>
  <DeskPage title="Work Package" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/app/work-packages/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <DocTypeListView
      doctype="Work Package"
      :field-order="[
        'code',
        'work_package_name',
        'project',
        'status',
        'budget',
        'progress',
        'start_date',
        'end_date',
        'owner_user',
      ]"
      :columns="[
        { key: 'code', label: 'Code' },
        { key: 'work_package_name', label: 'Name' },
        { key: 'project', label: 'Project' },
        { key: 'status', label: 'Status', preset: 'status' },
        { key: 'budget', label: 'Budget' },
        { key: 'progress', label: 'Progress', preset: 'progress' },
        { key: 'timeline', label: 'Timeline', preset: 'timeline', fields: ['start_date', 'end_date'] },
        { key: 'owner_user', label: 'Owner' },
      ]"
      :search-fields="['work_package_name', 'code', 'name']"
      :filter-values="filterValues"
      :filter-field-map="{ project: 'project' }"
      cache-key="buildsuite-work-package-list-generic"
      row-key="name"
      search-placeholder="Search by name or code…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskLinkPicker
          v-model="projectFilter"
          class="!w-56"
          doctype="Project"
          label-field="project_name"
          value-field="name"
          :search-fields="['project_name', 'custom_project_id', 'name']"
          :page-length="10"
          placeholder="Project: Any"
        />
      </template>

      <template #cell-code="{ row }">
        <DeskLink :to="`/app/work-packages/${row.name}`" @click.stop class="font-mono text-xs">
          {{ row.code || row.name }}
        </DeskLink>
      </template>
      <template #cell-work_package_name="{ row }">
        <span class="text-ink-900 font-medium">{{ row.work_package_name || row.name }}</span>
      </template>
      <template #cell-project="{ row }">
        <DeskLink
          v-if="row.project"
          :to="`/app/projects/${row.project}`"
          @click.stop
          class="text-xs"
        >{{ projectLabelMap.get(row.project) || row.project }}</DeskLink>
        <span v-else class="text-ink-500 text-xs">—</span>
      </template>
      <template #cell-budget="{ row }">
        <span class="tabular-nums">{{ fmtCompactINR(row.budget || 0) }}</span>
      </template>
      <template #cell-progress="{ row }">
        <div class="flex items-center justify-end gap-2">
          <div class="w-14 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
            <div class="h-full" :class="progressBarColor(row)" :style="`width:${row.progress || 0}%`"></div>
          </div>
          <span class="text-xs tabular-nums w-8 text-right">{{ Number(row.progress || 0) }}%</span>
        </div>
      </template>
      <template #cell-owner_user="{ row }">
        <UserAvatar :user-id="row.owner_user || row.owner" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No work packages match these filters.</div>
      </template>
    </DocTypeListView>
  </DeskPage>
</template>
