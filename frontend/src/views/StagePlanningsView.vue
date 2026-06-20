<script setup>
// Stage Planning list — adapter-backed DocType list shell (matches TasksView pattern).

import { ref, computed } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DocTypeListView from '@/components/doctype/DocTypeListView.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { usePermissions } from '@/composables/usePermissions'
import { fmtDate } from '@/utils/format'

const store = useDataStore()
const router = useRouter()
const route = useRoute()
const adapter = createDataAdapter(store)
const { canCreate, canRead } = usePermissions()

const projectFilter = ref('')
// Approval-lifecycle state (Frappe workflow_state). Honors ?status= deep links.
const workflowStateFilter = ref(route.query.status || '')
const fromDate = ref('')
const toDate = ref('')

const TODAY = new Date().toISOString().slice(0, 10)

function resourceRows(resource) {
  const raw = resource?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
}

const projectsResource = adapter.list('Project', {
  fields: ['name', 'project_name'],
  orderBy: 'project_name asc',
  pageLength: 100,
  cache: 'buildsuite-stage-project-filters',
})
const projectRows = computed(() => resourceRows(projectsResource))
const projectsMap = computed(() => {
  const map = {}
  projectRows.value.forEach((p) => {
    map[p.name] = p.project_name || p.name
  })
  return map
})

function projectName(id) { return projectsMap.value[id] || id }

// Visual-only schedule status — no Stage Review aggregation.
function stageStatus(row) {
  if (!row.planned_start && !row.planned_end) return 'Not Started'
  if (row.planned_start && TODAY < row.planned_start) return 'Not Started'
  if (row.planned_end && TODAY > row.planned_end) return 'Complete'
  return 'In Progress'
}
function statusClass(s) {
  if (s === 'Complete') return 'bg-success-50 text-success-700'
  if (s === 'In Progress') return 'bg-info-50 text-info-700'
  return 'bg-ink-100 text-ink-600'
}

function taskCountDisplay(row) {
  const children = Array.isArray(row.stage_planning_tasks)
    ? row.stage_planning_tasks.length
    : null
  const planned = Number(row.planned_task_count) || 0
  if (children !== null) return `${children} / ${planned}`
  return String(planned)
}

const filterValues = computed(() => ({
  project: projectFilter.value,
  workflowState: workflowStateFilter.value,
}))

const dateBaseFilters = computed(() => {
  const filters = []
  if (fromDate.value) filters.push(['planned_end', '>=', fromDate.value])
  if (toDate.value) filters.push(['planned_start', '<=', toDate.value])
  return filters
})

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Stage Planning' },
]

function onRowClick(row) { router.push(`/stage-plannings/${row.name}`) }
</script>

<template>
  <DeskPage title="Stage Planning" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink v-if="canCreate('stagePlanning')" to="/stage-plannings/new" class="desk-save-btn">+ New Stage</RouterLink>
    </template>

    <!-- PRM-014 — roles without Stage Planning access get a restricted notice. -->
    <div v-if="!canRead('stagePlanning')" class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700" style="border-radius: 6px;">
      You don't have access to Stage Planning.
    </div>

    <DocTypeListView
      v-else
      doctype="Stage Planning"
      :field-order="[
        'stage_name',
        'project',
        'description',
        'planned_start',
        'planned_end',
        'planned_task_count',
        'workflow_state',
        'stage_planning_tasks',
      ]"
      :columns="[
        { key: 'name', label: 'ID' },
        { key: 'stage_name', label: 'Stage', fields: ['stage_name', 'description'] },
        { key: 'project', label: 'Project' },
        { key: 'planned_start', label: 'Planned Start' },
        { key: 'planned_end', label: 'Planned End' },
        { key: 'planned_task_count', label: 'Tasks', align: 'right' },
        { key: 'workflow_state', label: 'State' },
        { key: '_status', label: 'Status', fields: ['planned_start', 'planned_end'] },
      ]"
      :search-fields="['stage_name', 'name', 'description']"
      :filter-values="filterValues"
      :filter-field-map="{ project: 'project', workflowState: 'workflow_state' }"
      :base-filters="dateBaseFilters"
      cache-key="buildsuite-stage-planning-list-generic"
      row-key="name"
      initial-order-by="planned_start asc"
      search-placeholder="Search stages, projects, descriptions…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskLinkPicker
          v-if="!projectFilter"
          v-model="projectFilter"
          class="!w-56"
          doctype="Project"
          label-field="project_name"
          value-field="name"
          :search-fields="['project_name', 'custom_project_id', 'name']"
          :page-length="10"
          placeholder="Project: Any"
        />
        <DeskFilterChip
          v-else
          label="Project"
          :value="projectName(projectFilter)"
          @remove="projectFilter = ''"
        />

        <!-- Approval state (workflow_state): select when empty, chip when set -->
        <DeskSelect v-if="!workflowStateFilter" v-model="workflowStateFilter" class="!w-44">
          <option value="">State: Any</option>
          <option>Draft</option>
          <option>Pending Approval</option>
          <option>Approved</option>
          <option>Rejected</option>
          <option>Cancelled</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="State"
          :value="workflowStateFilter"
          @remove="workflowStateFilter = ''"
        />

        <label class="text-[11px] text-ink-500 flex items-center gap-1">
          From
          <input
            v-model="fromDate"
            type="date"
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
            v-model="toDate"
            type="date"
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

      <template #cell-name="{ row }">
        <DeskLink :to="`/stage-plannings/${row.name}`" class="font-mono text-xs" @click.stop>
          {{ row.name }}
        </DeskLink>
      </template>
      <template #cell-stage_name="{ row }">
        <div class="text-sm font-medium text-ink-900">{{ row.stage_name || 'Untitled stage' }}</div>
        <div v-if="row.description" class="text-[11px] text-ink-500 truncate max-w-md">{{ row.description }}</div>
      </template>
      <template #cell-project="{ row }">
        <DeskLink
          v-if="row.project"
          :to="`/projects/${row.project}`"
          class="text-xs"
          @click.stop
        >{{ projectName(row.project) }}</DeskLink>
        <span v-else class="text-xs text-ink-500">—</span>
      </template>
      <template #cell-planned_start="{ row }">
        <span class="text-xs text-ink-700">{{ fmtDate(row.planned_start) || '—' }}</span>
      </template>
      <template #cell-planned_end="{ row }">
        <span class="text-xs text-ink-700">{{ fmtDate(row.planned_end) || '—' }}</span>
      </template>
      <template #cell-planned_task_count="{ row }">
        <span class="text-xs text-ink-700 tabular-nums">{{ taskCountDisplay(row) }}</span>
      </template>
      <template #cell-workflow_state="{ row }">
        <StatusBadge v-if="row.workflow_state" :status="row.workflow_state" size="xs" />
        <span v-else class="text-xs text-ink-400">—</span>
      </template>
      <template #cell-_status="{ row }">
        <span
          class="text-[10px] px-1.5 py-0.5 font-medium rounded-full"
          :class="statusClass(stageStatus(row))"
        >{{ stageStatus(row) }}</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No stages match these filters ·
          <RouterLink v-if="canCreate('stagePlanning')" to="/stage-plannings/new" class="desk-link">Plan a stage →</RouterLink>
        </div>
      </template>
    </DocTypeListView>
  </DeskPage>
</template>
