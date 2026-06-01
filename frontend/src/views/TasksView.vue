<script setup>
// Tasks list — Desk-styled (CLAUDE.md §12.4). Multi-filter preserved exactly:
// search + status + priority + project + assignee. Inactive filters show as a
// DeskSelect picker; active filters render as DeskFilterChip with × to clear,
// matching real Frappe Desk's filter-chip pattern.

import { ref, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtDate } from '@/utils/format'

const store = useDataStore()
const router = useRouter()

const search = ref('')
const statusFilter = ref('')
const priorityFilter = ref('')
const projectFilter = ref('')
const assigneeFilter = ref('')
const taskTypeFilter = ref('')  // proposal §M2 Select — Activity / Milestone / Inspection

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.tasks.filter(t => {
    if (term && !t.name.toLowerCase().includes(term)) return false
    if (statusFilter.value && t.status !== statusFilter.value) return false
    if (priorityFilter.value && t.priority !== priorityFilter.value) return false
    if (projectFilter.value && t.projectId !== projectFilter.value) return false
    if (assigneeFilter.value && t.assignee !== assigneeFilter.value) return false
    if (taskTypeFilter.value && (t.task_type || 'Activity') !== taskTypeFilter.value) return false
    return true
  })
})

function projectName(id) { return store.projectById(id)?.name || id }
function wpName(id) { return store.workPackageById(id)?.name || '—' }
function memberName(id) { return store.teamMember(id)?.name || id }

const columns = [
  { key: 'name',     label: 'Task' },
  { key: 'project',  label: 'Project · WP' },
  { key: 'status',   label: 'Status' },
  { key: 'priority', label: 'Priority' },
  // proposal §M2 — task_type Select inserted between Priority and Assignee.
  { key: 'task_type', label: 'Task Type' },
  { key: 'assignee', label: 'Assignee' },
  { key: 'endDate',  label: 'Due' },
  { key: 'progress', label: 'Progress', align: 'right' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Task' },
]

const subtitle = computed(() => `${items.value.length} of ${store.tasks.length}`)

function onRowClick(row) { router.push(`/app/tasks/${row.id}`) }
</script>

<template>
  <DeskPage title="Task" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/app/activity-types" class="desk-link text-xs mr-3">View Activity Types →</RouterLink>
      <RouterLink to="/app/tasks/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search tasks…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <!-- Status: select when empty, chip when set -->
        <DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-36">
          <option value="">Status: Any</option>
          <option>Open</option>
          <option>In Progress</option>
          <option>Completed</option>
          <option>Cancelled</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Status"
          :value="statusFilter"
          @remove="statusFilter = ''"
        />

        <!-- Priority -->
        <DeskSelect v-if="!priorityFilter" v-model="priorityFilter" class="!w-36">
          <option value="">Priority: Any</option>
          <option>Low</option>
          <option>Medium</option>
          <option>High</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Priority"
          :value="priorityFilter"
          @remove="priorityFilter = ''"
        />

        <!-- Project -->
        <DeskSelect v-if="!projectFilter" v-model="projectFilter" class="!w-48">
          <option value="">Project: Any</option>
          <option v-for="p in store.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Project"
          :value="projectName(projectFilter)"
          @remove="projectFilter = ''"
        />

        <!-- Assignee -->
        <DeskSelect v-if="!assigneeFilter" v-model="assigneeFilter" class="!w-44">
          <option value="">Assignee: Any</option>
          <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Assignee"
          :value="memberName(assigneeFilter)"
          @remove="assigneeFilter = ''"
        />

        <!-- Task Type (proposal §M2 Select) -->
        <DeskSelect v-if="!taskTypeFilter" v-model="taskTypeFilter" class="!w-40">
          <option value="">Task Type: Any</option>
          <option>Activity</option>
          <option>Milestone</option>
          <option>Inspection</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Task Type"
          :value="taskTypeFilter"
          @remove="taskTypeFilter = ''"
        />
      </template>

      <template #cell-name="{ row }">
        <DeskLink :to="`/app/tasks/${row.id}`" @click.stop>{{ row.name }}</DeskLink>
      </template>
      <template #cell-project="{ row }">
        <div class="text-xs text-ink-500">
          <div>{{ projectName(row.projectId) }}</div>
          <div class="text-ink-400">{{ wpName(row.workPackageId) }}</div>
        </div>
      </template>
      <template #cell-status="{ row }">
        <StatusBadge :status="row.status" />
      </template>
      <template #cell-priority="{ row }">
        <StatusBadge :status="row.priority" size="xs" />
      </template>
      <template #cell-task_type="{ row }">
        <StatusBadge :status="row.task_type || 'Activity'" size="xs" />
      </template>
      <template #cell-assignee="{ row }">
        <UserAvatar :user-id="row.assignee" size="xs" />
      </template>
      <template #cell-endDate="{ row }">
        <span class="text-xs text-ink-500">{{ fmtDate(row.endDate) }}</span>
      </template>
      <template #cell-progress="{ row }">
        <div class="flex items-center justify-end gap-2">
          <div class="w-14 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
            <div class="h-full" :class="row.progress === 100 ? 'bg-success-500' : 'bg-info-500'" :style="`width:${row.progress}%`"></div>
          </div>
          <span class="text-xs tabular-nums w-8 text-right">{{ row.progress }}%</span>
        </div>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No tasks match these filters ·
          <RouterLink to="/app/tasks/new" class="desk-link">Create a task →</RouterLink>
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
