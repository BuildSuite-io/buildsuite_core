<script setup>
// Work Packages list — Desk-styled (CLAUDE.md §12.4 destination: Desk in production).
// Data flow (single projectFilter dropdown filtering store.workPackages) is unchanged.

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtCompactINR, fmtDate } from '@/utils/format'

const store = useDataStore()
const router = useRouter()
const search = ref('')
const projectFilter = ref('')

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.workPackages.filter(wp => {
    if (projectFilter.value && wp.projectId !== projectFilter.value) return false
    if (term && !(wp.name.toLowerCase().includes(term) || (wp.code || '').toLowerCase().includes(term))) return false
    return true
  })
})

function projectName(id) {
  return store.projectById(id)?.name || id
}

// Schedule-based traffic-light for the progress bar — same shape as ProjectsView.
const today = new Date()
function wpVariance(w) {
  if (!w.startDate || !w.endDate) return 0
  const start = new Date(w.startDate).getTime()
  const end = new Date(w.endDate).getTime()
  const total = end - start
  if (total <= 0) return 0
  const elapsed = Math.max(0, Math.min(total, today.getTime() - start))
  const expected = (elapsed / total) * 100
  if (expected <= 0) return 0
  return ((expected - w.progress) / expected) * 100
}
function progressBarColor(w) {
  const v = wpVariance(w)
  if (v > 15) return 'bg-danger-500'
  if (v > 5) return 'bg-warning-500'
  return 'bg-success-500'
}

const columns = [
  { key: 'code',      label: 'Code' },
  { key: 'name',      label: 'Name' },
  { key: 'projectId', label: 'Project' },
  { key: 'status',    label: 'Status' },
  { key: 'budget',    label: 'Budget',   align: 'right' },
  { key: 'progress',  label: 'Progress', align: 'right' },
  { key: 'timeline',  label: 'Timeline' },
  { key: 'owner',     label: 'Owner' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Work Package' },
]

const subtitle = computed(() => `${items.value.length} of ${store.workPackages.length}`)

function onRowClick(row) { router.push(`/app/work-packages/${row.id}`) }
function clearProjectFilter() { projectFilter.value = '' }
const filteredProjectName = computed(() => projectName(projectFilter.value))
</script>

<template>
  <DeskPage title="Work Package" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/app/work-packages/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search by name or code…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskSelect v-if="!projectFilter" v-model="projectFilter" class="!w-48">
          <option value="">Project: Any</option>
          <option v-for="p in store.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Project"
          :value="filteredProjectName"
          @remove="clearProjectFilter"
        />
      </template>

      <template #cell-code="{ row }">
        <DeskLink :to="`/app/work-packages/${row.id}`" @click.stop class="font-mono text-xs">{{ row.code }}</DeskLink>
      </template>
      <template #cell-name="{ row }">
        <span class="text-ink-900 font-medium">{{ row.name }}</span>
      </template>
      <template #cell-projectId="{ row }">
        <span class="text-ink-700 text-xs">{{ projectName(row.projectId) }}</span>
      </template>
      <template #cell-status="{ row }">
        <StatusBadge :status="row.status" />
      </template>
      <template #cell-budget="{ row }">
        <span class="tabular-nums">{{ fmtCompactINR(row.budget) }}</span>
      </template>
      <template #cell-progress="{ row }">
        <div class="flex items-center justify-end gap-2">
          <div class="w-14 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
            <div class="h-full" :class="progressBarColor(row)" :style="`width:${row.progress}%`"></div>
          </div>
          <span class="text-xs tabular-nums w-8 text-right">{{ row.progress }}%</span>
        </div>
      </template>
      <template #cell-timeline="{ row }">
        <span class="text-xs text-ink-500 whitespace-nowrap">{{ fmtDate(row.startDate) }} → {{ fmtDate(row.endDate) }}</span>
      </template>
      <template #cell-owner="{ row }">
        <UserAvatar :user-id="row.owner" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No work packages match these filters.</div>
      </template>
    </DeskList>
  </DeskPage>
</template>
