<script setup>
// Stage Planning — list view. Desk-styled (CLAUDE.md §12.4). Stages-as-structure
// per §13.3 item 18 — NO Stage Review aggregation here (deferred to M3+).
// Reachable via Project Detail > Stage Planning tab, the Site Execution workspace
// (shortcut wired in a later prompt), or direct URL.

import { computed, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtDate } from '@/utils/format'

const store = useDataStore()
const router = useRouter()

const search = ref('')
const projectFilter = ref('')
const fromDate = ref('')
const toDate   = ref('')

const TODAY = new Date().toISOString().slice(0, 10)

function projectName(id) { return store.projectById(id)?.name || id }

// Status is a VISUAL derivation only — purely date-based. No aggregation across
// labour / GL / procurement (that's Stage Review, deferred to M3+).
function stageStatus(stage) {
  if (!stage.plannedStart && !stage.plannedEnd) return 'Not Started'
  if (stage.plannedStart && TODAY < stage.plannedStart) return 'Not Started'
  if (stage.plannedEnd   && TODAY > stage.plannedEnd)   return 'Complete'
  return 'In Progress'
}
function statusClass(s) {
  if (s === 'Complete')   return 'bg-success-50 text-success-700'
  if (s === 'In Progress')return 'bg-info-50 text-info-700'
  return 'bg-ink-100 text-ink-600'
}

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.stagePlannings.filter(sp => {
    if (projectFilter.value && sp.project !== projectFilter.value) return false
    if (fromDate.value && sp.plannedEnd   && sp.plannedEnd   < fromDate.value) return false
    if (toDate.value   && sp.plannedStart && sp.plannedStart > toDate.value)   return false
    if (term) {
      const hay = `${sp.id} ${sp.stageName} ${projectName(sp.project)} ${sp.description || ''}`.toLowerCase()
      if (!hay.includes(term)) return false
    }
    return true
  }).slice().sort((a, b) => (a.plannedStart || '~').localeCompare(b.plannedStart || '~'))
})

const columns = [
  { key: 'id',           label: 'ID' },
  { key: 'stageName',    label: 'Stage' },
  { key: 'project',      label: 'Project' },
  { key: 'plannedStart', label: 'Planned Start' },
  { key: 'plannedEnd',   label: 'Planned End' },
  { key: 'taskCount',    label: 'Tasks', align: 'right' },
  { key: 'status',       label: 'Status' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Stage Planning' },
]

const subtitle = computed(() =>
  `${items.value.length} of ${store.stagePlannings.length} · Stages-as-structure · §13.3 item 18`
)

function onRowClick(row) { router.push(`/stage-plannings/${row.id}`) }
</script>

<template>
  <DeskPage title="Stage Planning" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/stage-plannings/new" class="desk-save-btn">+ New Stage</RouterLink>
    </template>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search stages, projects, descriptions…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <!-- Project filter -->
        <DeskSelect v-if="!projectFilter" v-model="projectFilter" class="!w-56">
          <option value="">Project: Any</option>
          <option v-for="p in store.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Project"
          :value="projectName(projectFilter)"
          @remove="projectFilter = ''"
        />
        <!-- Date range (free-form, both optional). Compact inputs to keep the chip row tight. -->
        <label class="text-[11px] text-ink-500 flex items-center gap-1">
          From
          <input
            type="date"
            v-model="fromDate"
            class="desk-input !w-36 !text-xs"
          />
        </label>
        <DeskFilterChip
          v-if="fromDate"
          label="From"
          :value="fmtDate(fromDate)"
          @remove="fromDate = ''"
        />
        <label class="text-[11px] text-ink-500 flex items-center gap-1">
          To
          <input
            type="date"
            v-model="toDate"
            class="desk-input !w-36 !text-xs"
          />
        </label>
        <DeskFilterChip
          v-if="toDate"
          label="To"
          :value="fmtDate(toDate)"
          @remove="toDate = ''"
        />
      </template>

      <template #cell-id="{ row }">
        <DeskLink :to="`/stage-plannings/${row.id}`" @click.stop class="font-mono text-xs">{{ row.id }}</DeskLink>
      </template>
      <template #cell-stageName="{ row }">
        <div class="text-sm font-medium text-ink-900">{{ row.stageName }}</div>
        <div v-if="row.description" class="text-[11px] text-ink-500 truncate max-w-md">{{ row.description }}</div>
      </template>
      <template #cell-project="{ row }">
        <DeskLink :to="`/projects/${row.project}`" @click.stop class="text-xs">{{ projectName(row.project) }}</DeskLink>
      </template>
      <template #cell-plannedStart="{ row }">
        <span class="text-xs text-ink-700">{{ fmtDate(row.plannedStart) || '—' }}</span>
      </template>
      <template #cell-plannedEnd="{ row }">
        <span class="text-xs text-ink-700">{{ fmtDate(row.plannedEnd) || '—' }}</span>
      </template>
      <template #cell-taskCount="{ row }">
        <span class="text-xs text-ink-700 tabular-nums">
          {{ (row.stagePlanningTasks || []).length }} / {{ row.plannedTaskCount || 0 }}
        </span>
      </template>
      <template #cell-status="{ row }">
        <span
          class="text-[10px] px-1.5 py-0.5 font-medium"
          style="border-radius: 2px;"
          :class="statusClass(stageStatus(row))"
        >{{ stageStatus(row) }}</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No stages match these filters ·
          <RouterLink to="/stage-plannings/new" class="desk-link">Plan a stage →</RouterLink>
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
