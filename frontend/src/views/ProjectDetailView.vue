<script setup>
// Project Detail — Desk-styled (CLAUDE.md §12.4 destination: Desk in production).
// All computed properties, actions, and store calls are preserved exactly from the
// pre-rebuild version. Only markup and styling change.

import { ref, computed, watch, nextTick } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { useConfirm } from '@/composables/useConfirm'
import { usePermissions } from '@/composables/usePermissions'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DocTypeListView from '@/components/doctype/DocTypeListView.vue'
import { createDataAdapter } from '@/data/adapters'
import { toDateInputValue } from '@/utils/dateInput'
import { fmtINR, fmtCompactINR, fmtDate } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'
import ProjectEditModal from '@/views/project-detail/ProjectEditModal.vue'
import ProjectTeamMemberModal from '@/views/project-detail/ProjectTeamMemberModal.vue'
import OverviewTab from '@/views/project-detail/tabs/OverviewTab.vue'
import AttachmentsTab from '@/views/project-detail/tabs/AttachmentsTab.vue'
import TeamTab from '@/views/project-detail/tabs/TeamTab.vue'
import ActivityTab from '@/views/project-detail/tabs/ActivityTab.vue'
import {
  BOQ_COLS,
  PROJECT_REPORTS,
  SCO_COLS,
  SUB_COLS,
  TASK_COLS,
  TEAM_COLS,
  WP_COLS,
} from '@/views/project-detail/projectDetailConfig'
import { useProjectDetailListFilters } from '@/views/project-detail/useProjectDetailListFilters'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()
const confirmDialog = useConfirm()
const { canEdit, canDelete, canCreate } = usePermissions()
const adapter = createDataAdapter(store)

const { errors: editErrors, applyServerErrors: applyEditErrors, setErrors: setEditErrors, clearError: clearEditError } = useFormErrors({
  project_name:        'name',
  custom_project_id:   'code',
  company:             'company',
  customer:            'client',
  project_type:        'type',
  expected_end_date:   'endDate',
  expected_start_date: 'startDate',
  owner:               'pm',
})

function firstResourceRow(resource) {
  if (resource?.doc) return resource.doc
  const raw = resource?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  if (raw && typeof raw === 'object' && 'value' in raw) return raw.value || null
  return raw || null
}

const projectResource = ref(null)

// Route param is a Frappe record name first; seed-data aliases are only a
// fallback for local prototype sessions that still carry older records.
function loadProjectResource() {
  if (!props.id) {
    projectResource.value = null
    return
  }

  projectResource.value = adapter.read('Project', props.id, {
    nameField: 'name',
    fields: [
      'name',
      'custom_project_id',
      'project_name',
      'customer',
      'project_type',
      'status',
      'priority',
      'estimated_costing',
      'percent_complete',
      'expected_start_date',
      'expected_end_date',
      'owner',
      'company',
      'is_group',
      'notes',
      'creation',
      'modified',
      'parent_project',
    ],
    cache: `buildsuite-project-detail:${props.id}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || row?.id,
        code: row?.custom_project_id || '',
        name: row?.project_name || row?.name || '',
        client: row?.customer || '',
        status: row?.status || '',
        priority: row?.priority || 'Medium',
        type: row?.project_type || '',
        company: row?.company || '',
        startDate: row?.expected_start_date || null,
        endDate: row?.expected_end_date || null,
        budget: Number(row?.estimated_costing) || 0,
        progress: Number(row?.percent_complete) || 0,
        pm: row?.owner || '',
        location: row?.location || '',
        description: row?.notes || row?.description || '',
        isGroup: Number(row?.is_group ?? (row?.parent_project ? 0 : 1)) === 1,
        parentId: row?.parent_project || null,
        createdAt: row?.creation || null,
      }))
    },
  })
}

watch(() => props.id, loadProjectResource, { immediate: true })

const project = computed(() => {
  const backendProject = firstResourceRow(projectResource.value)
  if (backendProject) return backendProject

  const key = props.id
  return (
    store.projectById(key)
    || store.projects.find((p) => p.code === key)
    || store.projects.find((p) => p.name === key)
    || null
  )
})
const resolvedProjectId = computed(() => project.value?.id || props.id)
const parent = computed(() => project.value?.parentId ? store.projectById(project.value.parentId) : null)
const subprojectsResource = ref(null)
const subprojectFilterKey = computed(() => resolvedProjectId.value)

function loadSubprojectsResource() {
  if (!resolvedProjectId.value) {
    subprojectsResource.value = null
    return
  }

  const subprojectFields = [
    'name',
    'custom_project_id',
    'project_name',
    'status',
    'estimated_costing',
    'percent_complete',
    'owner',
    'parent_project',
  ]
  const subprojectFilters = {
    parent_project: ['=', resolvedProjectId.value],
  }

  subprojectsResource.value = adapter.list('Project', {
    fields: subprojectFields,
    filters: subprojectFilters,
    orderBy: 'modified desc',
    pageLength: 100,
    cache: `buildsuite-project-detail-subs:${resolvedProjectId.value}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || row?.id,
        code: row?.custom_project_id || '',
        name: row?.project_name || row?.name || '',
        status: row?.status || '',
        budget: Number(row?.estimated_costing) || 0,
        progress: Number(row?.percent_complete) || 0,
        pm: row?.owner || '',
        parentId: row?.parent_project || resolvedProjectId.value,
      }))
    },
  })
}

watch(subprojectFilterKey, () => {
  loadSubprojectsResource()
}, { immediate: true })

const subs = computed(() => {
  const raw = subprojectsResource.value?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
})

const subprojectIdsKey = computed(() => subs.value.map((p) => p.id).filter(Boolean).join('|'))

const workPackageProjectIds = computed(() => {
  const ids = [resolvedProjectId.value, ...subs.value.map((p) => p.id)].filter(Boolean)
  return Array.from(new Set(ids))
})
const workPackagesResource = ref(null)
const workPackageFilterKey = computed(() => workPackageProjectIds.value.join('|'))

function loadWorkPackagesResource() {
  if (!workPackageProjectIds.value.length) {
    workPackagesResource.value = null
    return
  }

  const workPackageFields = [
    'name',
    'code',
    'work_package_name',
    'project',
    'status',
    'budget',
    'progress',
    'start_date',
    'end_date',
  ]
  const workPackageFilters = {
    project: ['in', workPackageProjectIds.value],
  }
  const workPackageScopeKey = workPackageProjectIds.value.join('|')

  workPackagesResource.value = adapter.list('Work Package', {
    fields: workPackageFields,
    filters: workPackageFilters,
    orderBy: 'modified desc',
    pageLength: 200,
    cache: `buildsuite-project-detail-wp:${resolvedProjectId.value}:${workPackageScopeKey}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || row?.id,
        code: row?.code || '',
        name: row?.work_package_name || row?.name || '',
        projectId: row?.project || row?.projectId || '',
        status: row?.status || '',
        budget: Number(row?.budget) || 0,
        progress: Number(row?.progress) || 0,
        startDate: row?.start_date || row?.startDate || null,
        endDate: row?.end_date || row?.endDate || null,
      }))
    },
  })
}

watch(workPackageFilterKey, () => {
  loadWorkPackagesResource()
}, { immediate: true })

watch(subprojectIdsKey, (next, prev) => {
  if (next === prev) return
  loadWorkPackagesResource()
})

const workPackages = computed(() => {
  const raw = workPackagesResource.value?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
})

const taskProjectIds = computed(() => {
  const ids = [resolvedProjectId.value, ...subs.value.map((p) => p.id)].filter(Boolean)
  return Array.from(new Set(ids))
})
const tasksResource = ref(null)
const taskFilterKey = computed(() => taskProjectIds.value.join('|'))

function loadTasksResource() {
  if (!taskProjectIds.value.length) {
    tasksResource.value = null
    return
  }

  const taskFields = [
    'name',
    'subject',
    'project',
    'task_type',
    'status',
    'priority',
    'progress',
    'owner',
    'exp_start_date',
    'exp_end_date',
  ]
  const taskFilters = {
    project: ['in', taskProjectIds.value],
  }
  const taskScopeKey = taskProjectIds.value.join('|')

  tasksResource.value = adapter.list('Task', {
    fields: taskFields,
    filters: taskFilters,
    orderBy: 'modified desc',
    pageLength: 300,
    cache: `buildsuite-project-detail-task:${resolvedProjectId.value}:${taskScopeKey}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || row?.id,
        name: row?.subject || row?.task_name || row?.name || '',
        projectId: row?.project || '',
        status: row?.status || 'Open',
        priority: row?.priority || 'Medium',
        task_type: row?.task_type || 'Activity',
        assignee: row?.owner || row?.assignee || '',
        startDate: row?.exp_start_date || row?.start_date || null,
        endDate: row?.exp_end_date || row?.end_date || null,
        progress: Number(row?.progress) || 0,
      }))
    },
  })
}

watch(taskFilterKey, () => {
  loadTasksResource()
}, { immediate: true })

watch(subprojectIdsKey, (next, prev) => {
  if (next === prev) return
  loadTasksResource()
})

const tasks = computed(() => {
  const raw = tasksResource.value?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
})

const scos = computed(() => store.scosByProject(resolvedProjectId.value))

const stageCount = ref(null)
const stageListRef = ref(null)
const stageBaseFilters = computed(() => {
  const ids = workPackageProjectIds.value
  if (!ids.length) return []
  return [['project', 'in', ids]]
})

// Attachment count — fetched eagerly (not behind the tab v-if) so the badge
// shows on the tab heading without the user needing to open the tab first.
const fileCountResource = ref(null)

function loadFileCount(projectId) {
  if (!projectId) { fileCountResource.value = null; return }
  fileCountResource.value = adapter.list('File', {
    filters: [
      ['attached_to_doctype', '=', 'Project'],
      ['attached_to_name', '=', projectId],
    ],
    fields: ['name'],
    pageLength: 500,
  })
}

watch(resolvedProjectId, loadFileCount, { immediate: true })

const attachmentCount = computed(() => {
  const raw = fileCountResource.value?.data
  if (Array.isArray(raw)) return raw.length
  if (Array.isArray(raw?.value)) return raw.value.length
  return null
})
const boqs = computed(() => store.boqsByProject(resolvedProjectId.value).slice().sort((a,b) => (b.preparedDate || '').localeCompare(a.preparedDate || '')))
const activeBoq = computed(() => store.activeBoqForProject(resolvedProjectId.value) ||
  boqs.value.find(b => b.status === 'Approved'))

// Cost rollups for the summary strip. Planned honours the active BOQ's
// planned total when one exists, otherwise falls back to the project budget.
// Actual is 0 until an Approved BOQ exists and its actuals have been
// recalculated.
const plannedCost = computed(() => {
  if (activeBoq.value) return store.boqTotals(activeBoq.value.id).planned
  return project.value?.budget || 0
})
const actualCost = computed(() => {
  if (activeBoq.value) return store.boqTotals(activeBoq.value.id).actual
  return 0
})
const costDeviation = computed(() => actualCost.value - plannedCost.value)
const costDeviationPct = computed(() =>
  plannedCost.value ? (costDeviation.value / plannedCost.value) * 100 : 0
)
function deviationColor(pct) {
  if (Math.abs(pct) < 0.5) return 'text-ink-500'
  return pct > 0 ? 'text-danger-700' : 'text-success-700'
}

// Schedule helpers — elapsed / total / remaining days, plus a planned-progress
// % that we render alongside actual progress in the Overview hero so the user
// sees expected-vs-actual at a glance.
const scheduleSummary = computed(() => {
  const p = project.value
  if (!p || !p.startDate || !p.endDate) return null
  const start = new Date(p.startDate).getTime()
  const end = new Date(p.endDate).getTime()
  const today = new Date().getTime()
  const total = end - start
  if (total <= 0) return null
  const totalDays = Math.ceil(total / 86400000)
  const elapsedRaw = today - start
  const elapsedDays = Math.max(0, Math.min(totalDays, Math.ceil(elapsedRaw / 86400000)))
  const remainingDays = Math.max(0, Math.ceil((end - today) / 86400000))
  const elapsedPct = Math.max(0, Math.min(100, (elapsedRaw / total) * 100))
  return { totalDays, elapsedDays, remainingDays, elapsedPct }
})

// Days the project is running behind expected schedule. Same logic as the
// Project Dashboard helper — larger of progress-slip and calendar overrun.
const delayedDays = computed(() => {
  const p = project.value
  if (!p || !p.startDate || !p.endDate) return 0
  const today = new Date()
  const start = new Date(p.startDate).getTime()
  const end = new Date(p.endDate).getTime()
  const total = end - start
  if (total <= 0) return 0
  const totalDays = total / 86400000
  const elapsed = Math.max(0, today.getTime() - start)
  const expectedPct = Math.min(100, (elapsed / total) * 100)
  const progressSlip = expectedPct > p.progress
    ? Math.ceil(((expectedPct - p.progress) / 100) * totalDays)
    : 0
  const overdueDays = today.getTime() > end && p.progress < 100
    ? Math.ceil((today.getTime() - end) / 86400000)
    : 0
  return Math.max(progressSlip, overdueDays)
})

// Reset to the Overview tab whenever the route navigates to a different
// project record (Vue Router reuses the component instance when only the
// `id` param changes, so the previously-active tab would otherwise persist
// across projects — surfaces a blank panel when clicking into a subproject
// from the parent's Subprojects tab, since Subprojects is filtered out for
// subprojects themselves).
const tab = ref('overview')
const editing = ref(false)
const editForm = ref({})

watch(() => props.id, () => {
  tab.value = 'overview'
  editing.value = false
})

// Project team — PM always first, then user-added members.
const projectTeam = computed(() => store.projectTeamMembers(resolvedProjectId.value))

// Add-team-member modal state.
const teamModalOpen = ref(false)
const teamPickUserId = ref('')
const availableTeamCandidates = computed(() => {
  const memberIds = new Set(projectTeam.value.map(m => m.id))
  return store.team.filter(m => !memberIds.has(m.id))
})
function openTeamModal() {
  teamPickUserId.value = availableTeamCandidates.value[0]?.id || ''
  teamModalOpen.value = true
}
function closeTeamModal() {
  teamModalOpen.value = false
}
function confirmAddMember() {
  if (!teamPickUserId.value) return
  store.addProjectTeamMember(resolvedProjectId.value, teamPickUserId.value)
  teamModalOpen.value = false
}
async function removeTeamMember(userId) {
  if (!userId || userId === project.value?.pm) return
  const m = store.teamMember(userId)
  const ok = await confirmDialog({
    title: 'Remove team member',
    message: `Remove ${m?.name || userId} from this project's team?`,
    confirmLabel: 'Remove',
    destructive: true,
  })
  if (!ok) return
  store.removeProjectTeamMember(resolvedProjectId.value, userId)
}

function buildProjectEditForm(source) {
  if (!source) return {}

  return {
    ...source,
    startDate: toDateInputValue(source.startDate),
    endDate: toDateInputValue(source.endDate),
  }
}

function startEdit() {
  editForm.value = buildProjectEditForm(project.value)
  setEditErrors({})
  editing.value = true
}
async function saveEdit() {
  try {
    await adapter.update('Project', resolvedProjectId.value, {
      project_name: editForm.value.name,
      custom_project_id: editForm.value.code,
      is_group: editForm.value.isGroup ? 1 : 0,
      status: editForm.value.status,
      priority: editForm.value.priority,
      percent_complete: editForm.value.progress,
      expected_start_date: editForm.value.startDate,
      expected_end_date: editForm.value.endDate,
      customer: editForm.value.client,
      project_type: editForm.value.type,
      company: editForm.value.company,
      estimated_costing: Number(editForm.value.budget),
      owner: editForm.value.pm,
      notes: editForm.value.description,
    })
    editing.value = false
    projectResource.value?.reload?.()
    showToast('Project updated')
  } catch (err) {
    showToast(applyEditErrors(err) ?? 'Failed to save project', 'error')
  }
}
function cancelEdit() {
  editForm.value = buildProjectEditForm(project.value)
  setEditErrors({})
  editing.value = false
}
function onPrimary() {
  if (editing.value) saveEdit()
  else startEdit()
}

const showDeleteConfirm = ref(false)
const deleteLoading = ref(false)

function deleteProject() {
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  deleteLoading.value = true
  try {
    await adapter.remove('Project', resolvedProjectId.value)
    showDeleteConfirm.value = false
    await router.push('/projects')
    await nextTick()
    showToast('Project deleted')
  } catch (err) {
    showToast('Failed to delete project', 'error')
    console.error('deleteProject failed:', err)
  } finally {
    deleteLoading.value = false
  }
}

function addSubproject() {
  // Nested subprojects are not allowed — guard the action even though the
  // entry button is hidden by `isSubproject`.
  if (project.value?.parentId) return
  if (project.value?.isGroup === false) return
  router.push({ path: '/projects/new', query: { parentId: resolvedProjectId.value } })
}

async function seedFromTemplate() {
  const tpl = store.templateForProjectType(project.value.type)
  if (!tpl) return
  const n = tpl.defaultStages.length
  const ok = await confirmDialog({
    title: 'Seed default stages',
    message: `Seed ${n} default stages from the ${project.value.type} template?\n\nThis will create ${n} stages on top of any existing ones — it does not replace or merge.`,
    confirmLabel: 'Seed stages',
  })
  if (!ok) return
  store.seedStagesFromTemplate(resolvedProjectId.value)
  stageListRef.value?.reload()
}

const {
  boqSearch,
  boqsFiltered,
  scoSearch,
  scosFiltered,
  subSearch,
  subsFiltered,
  taskProjectFilter,
  taskProjectFilterOptions,
  taskProjectNameById,
  taskSearch,
  taskStats,
  tasksFiltered,
  wpFiltered,
  wpProgress,
  wpProjectFilter,
  wpProjectFilterOptions,
  wpSearch,
} = useProjectDetailListFilters({
  project,
  subs,
  workPackages,
  tasks,
  scos,
  boqs,
})

// Visual-only stage status derivation. Same logic as StagePlanningsView; kept
// inline here to avoid an extra import for one helper. NO Stage Review aggregation.
const TODAY_STR = new Date().toISOString().slice(0, 10)
function stageStatus(s) {
  if (!s.planned_start && !s.planned_end) return 'Not Started'
  if (s.planned_start && TODAY_STR < s.planned_start) return 'Not Started'
  if (s.planned_end   && TODAY_STR > s.planned_end)   return 'Complete'
  return 'In Progress'
}
function stageStatusClass(s) {
  if (s === 'Complete')   return 'bg-success-50 text-success-700'
  if (s === 'In Progress')return 'bg-info-50 text-info-700'
  return 'bg-ink-100 text-ink-600'
}

// Subprojects tab + the "+ Add Subproject" button are hidden when this
// record IS itself a subproject — nested subprojects are not allowed.
const isSubproject = computed(() => !!project.value?.parentId)
const subprojectsEnabled = computed(() => !isSubproject.value && project.value?.isGroup !== false)

const projectReports = PROJECT_REPORTS

const tabs = computed(() => {
  // Each tab carries a count when it corresponds to a list of child records.
  // Counts render as " (N)" appended to the label. Overview / Activity have
  // no count.
  const all = [
    { id: 'overview',       label: 'Overview',       count: null },
    { id: 'subprojects',    label: 'Subprojects',    count: subs.value.length },
    { id: 'work-packages',  label: 'Work Packages',  count: workPackages.value.length },
    { id: 'tasks',          label: 'Tasks',          count: tasks.value.length },
    { id: 'stage-planning', label: 'Stage Planning', count: stageCount.value },
    { id: 'boq',            label: 'BOQ',            count: boqs.value.length },
    { id: 'scos',           label: 'Scope Changes',  count: scos.value.length },
    { id: 'attachments',    label: 'Attachments',    count: attachmentCount.value },
    { id: 'team',           label: 'Team',           count: projectTeam.value.length },
    { id: 'activity',       label: 'Activity',       count: null },
  ]
  return subprojectsEnabled.value ? all : all.filter(t => t.id !== 'subprojects')
})

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Project', to: '/projects' },
  ]
  if (parent.value) out.push({ label: parent.value.name, to: `/projects/${parent.value.id}` })
  return out
})

const titleStatuses = computed(() => project.value ? [project.value.status, project.value.priority] : [])

// Schedule-based variance + progress-bar color, same as the list view.
const today = new Date()
function scheduleVariance(p) {
  const start = new Date(p.startDate).getTime()
  const end = new Date(p.endDate).getTime()
  const total = end - start
  if (total <= 0) return 0
  const elapsed = Math.max(0, Math.min(total, today.getTime() - start))
  const expected = (elapsed / total) * 100
  if (expected <= 0) return 0
  return ((expected - p.progress) / expected) * 100
}
function progressBarColor(p) {
  if (!p) return 'bg-ink-300'
  const v = scheduleVariance(p)
  if (v > 15) return 'bg-danger-500'
  if (v > 5) return 'bg-warning-500'
  return 'bg-success-500'
}

const subCols = SUB_COLS
const wpCols = WP_COLS
const taskCols = TASK_COLS
const boqCols = BOQ_COLS
const scoCols = SCO_COLS
const teamCols = TEAM_COLS

function onSubRowClick(row) { router.push(`/projects/${row.id}`) }
function onWpRowClick(row) { router.push(`/work-packages/${row.id}`) }
function onTaskRowClick(row) { router.push(`/tasks/${row.id}`) }
function onBoqRowClick(row) { router.push(`/boq/${row.id}`) }
</script>

<template>
  <DeskPage
    v-if="project"
    :title="project.name"
    :subtitle="`${project.id}${project.code ? ` · ${project.code}` : ''}`"
    :breadcrumbs="breadcrumbs"
    :status="titleStatuses"
  >
    <!-- Edit + Delete buttons share the title row (DeskPage #actions slot) -->
    <template #actions>
      <button
        v-if="canEdit('project')"
        type="button"
        class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
        style="border-radius: 6px;"
        @click="startEdit"
      >Edit</button>
      <button
        v-if="canDelete('project')"
        type="button"
        class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
        style="border-radius: 6px;"
        @click="deleteProject"
      >Delete</button>
    </template>

    <div>
      <!-- Tabs (thin underline, brand-green for active) -->
      <div class="border-b border-ink-200 flex overflow-x-auto scrollbar-thin mb-0">
        <button
          v-for="t in tabs"
          :key="t.id"
          type="button"
          class="px-3 py-2 text-xs font-medium whitespace-nowrap transition-colors"
          :class="tab === t.id ? 'text-brand-600' : 'text-ink-600 hover:text-ink-900'"
          :style="tab === t.id ? 'border-bottom: 2px solid currentColor; margin-bottom: -1px;' : 'border-bottom: 2px solid transparent; margin-bottom: -1px;'"
          @click="tab = t.id"
        >{{ t.label }}<span v-if="t.count !== null" class="ml-1 text-ink-400 tabular-nums">({{ t.count }})</span></button>
      </div>

      <!-- ===== Tab content ===== -->

      <!-- Overview — view mode -->
      <OverviewTab
        v-if="tab === 'overview'"
        :project="project"
        :active-boq="activeBoq"
        :project-reports="projectReports"
        :delayed-days="delayedDays"
        :schedule-summary="scheduleSummary"
        :progress-bar-color="progressBarColor"
        @edit="startEdit"
      />

      <!-- Subprojects — hidden when this record is itself a subproject -->
      <div v-if="tab === 'subprojects' && subprojectsEnabled" class="pt-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs text-ink-500">
            <span class="text-ink-900 font-medium">{{ subs.length }} subproject{{ subs.length === 1 ? '' : 's' }}</span>
          </span>
          <button v-if="canCreate('project')" type="button" class="desk-save-btn ml-auto" @click="addSubproject">+ New Subproject</button>
        </div>
        <DeskList
          v-model="subSearch"
          :rows="subsFiltered"
          :columns="subCols"
          row-key="id"
          search-placeholder="Search subprojects…"
          @row-click="onSubRowClick"
        >
          <template #cell-code="{ row }">
            <DeskLink :to="`/projects/${row.id}`" @click.stop class="font-mono text-xs">{{ row.code }}</DeskLink>
          </template>
          <template #cell-name="{ row }">
            <span class="text-ink-900 font-medium">{{ row.name }}</span>
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
          <template #cell-pm="{ row }">
            <UserAvatar :user-id="row.pm" size="xs" />
          </template>
          <template #empty>
            <div class="text-sm text-ink-500">
              No subprojects yet · <DeskLink @click="addSubproject">Create the first one →</DeskLink>
            </div>
          </template>
        </DeskList>
      </div>

      <!-- Work Packages -->
      <div v-if="tab === 'work-packages'" class="pt-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs text-ink-500">
            {{ workPackages.length }} package{{ workPackages.length === 1 ? '' : 's' }} · avg progress
            <span class="text-ink-900 font-medium">{{ wpProgress }}%</span>
          </span>
          <RouterLink
            v-if="canCreate('workPackage')"
            :to="{ name: 'wp-new', query: { projectId: project.id } }"
            class="desk-save-btn ml-auto"
          >+ Add Work Package</RouterLink>
        </div>
        <DeskList
          v-model="wpSearch"
          :rows="wpFiltered"
          :columns="wpCols"
          row-key="id"
          search-placeholder="Search work packages…"
          @row-click="onWpRowClick"
        >
          <template #filter-chips>
            <DeskSelect v-model="wpProjectFilter" class="!w-52">
              <option value="">Project: Any</option>
              <option
                v-for="p in wpProjectFilterOptions"
                :key="p.id"
                :value="p.id"
              >{{ p.name }}</option>
            </DeskSelect>
          </template>
          <template #cell-code="{ row }">
            <DeskLink :to="`/work-packages/${row.id}`" @click.stop class="font-mono text-xs">{{ row.code }}</DeskLink>
          </template>
          <template #cell-name="{ row }">
            <span class="text-ink-900 font-medium">{{ row.name }}</span>
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
                <div class="h-full bg-success-500" :style="`width:${row.progress}%`"></div>
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
            <div class="text-sm text-ink-500">No work packages yet.</div>
          </template>
        </DeskList>
      </div>

      <!-- Tasks -->
      <div v-if="tab === 'tasks'" class="pt-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs text-ink-500">
            <span class="text-ink-900 font-medium">{{ taskStats.total }} tasks</span>
            · {{ taskStats.completed }} completed · {{ taskStats.inProgress }} in progress · {{ taskStats.open }} open
          </span>
          <RouterLink
            v-if="canCreate('task')"
            :to="{ name: 'task-new', query: { projectId: project.id } }"
            class="desk-save-btn ml-auto"
          >+ Add Task</RouterLink>
        </div>
        <DeskList
          v-model="taskSearch"
          :rows="tasksFiltered"
          :columns="taskCols"
          row-key="id"
          search-placeholder="Search tasks…"
          @row-click="onTaskRowClick"
        >
          <template #filter-chips>
            <DeskSelect v-model="taskProjectFilter" class="!w-52">
              <option value="">Project: Any</option>
              <option
                v-for="p in taskProjectFilterOptions"
                :key="p.id"
                :value="p.id"
              >{{ p.name }}</option>
            </DeskSelect>
          </template>
          <template #cell-name="{ row }">
            <DeskLink :to="`/tasks/${row.id}`" @click.stop class="text-ink-900 hover:text-ink-900">{{ row.name }}</DeskLink>
          </template>
          <template #cell-project="{ row }">
            <DeskLink
              v-if="row.projectId"
              :to="`/projects/${row.projectId}`"
              @click.stop
              class="text-xs text-ink-900 hover:text-ink-900"
            >{{ taskProjectNameById.get(row.projectId) || row.projectId }}</DeskLink>
            <span v-else class="text-xs text-ink-500">—</span>
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
              No tasks yet ·
              <RouterLink :to="{ name: 'task-new', query: { projectId: project.id } }" class="desk-link">Create the first task →</RouterLink>
            </div>
          </template>
        </DeskList>
      </div>

      <!-- Stage Planning — always mounted (v-show) so @count-change fires on load
           and the tab badge populates before the user switches to this tab. -->
      <div v-show="tab === 'stage-planning'" class="pt-4">
        <DocTypeListView
          ref="stageListRef"
          doctype="Stage Planning"
          :field-order="['stage_name', 'description', 'planned_start', 'planned_end', 'planned_task_count']"
          :columns="[
            { key: 'stage_name', label: 'Stage', fields: ['stage_name', 'description'] },
            { key: 'planned_start', label: 'Start' },
            { key: 'planned_end', label: 'End' },
            { key: 'planned_task_count', label: 'Tasks' },
            { key: '_status', label: 'Status', fields: ['planned_start', 'planned_end'] },
            { key: '_open', label: '', fields: ['name'], align: 'right' },
          ]"
          :base-filters="stageBaseFilters"
          :search-fields="['stage_name', 'name']"
          cache-key="buildsuite-stage-planning-project-tab"
          row-key="name"
          initial-order-by="planned_start asc"
          search-placeholder="Search stages…"
          :compact="true"
          @row-click="row => router.push('/stage-plannings/' + row.name)"
          @count-change="stageCount = $event"
        >
          <template #actions>
            <RouterLink
              v-if="canCreate('stagePlanning')"
              :to="{ name: 'stage-planning-new', query: { projectId: project.id } }"
              class="desk-save-btn"
            >+ Add Stage</RouterLink>
          </template>

          <template #cell-stage_name="{ row }">
            <span class="text-ink-900 font-medium">{{ row.stage_name }}</span>
            <div v-if="row.description" class="text-[11px] text-ink-500 truncate mt-0.5">{{ row.description }}</div>
          </template>
          <template #cell-planned_start="{ row }">
            <span class="text-xs text-ink-700">{{ fmtDate(row.planned_start) || '—' }}</span>
          </template>
          <template #cell-planned_end="{ row }">
            <span class="text-xs text-ink-700">{{ fmtDate(row.planned_end) || '—' }}</span>
          </template>
          <template #cell-planned_task_count="{ row }">
            <span class="text-xs text-ink-700 tabular-nums">{{ row.planned_task_count || 0 }}</span>
          </template>
          <template #cell-_status="{ row }">
            <span
              class="text-[10px] px-1.5 py-0.5 font-medium"
              style="border-radius: 2px;"
              :class="stageStatusClass(stageStatus(row))"
            >{{ stageStatus(row) }}</span>
          </template>
          <template #cell-_open="{ row }">
            <DeskLink :to="`/stage-plannings/${row.name}`" @click.stop class="text-xs">Open →</DeskLink>
          </template>

          <template #empty>
            <div class="py-4">
              <div class="text-sm text-ink-500 italic mb-3">No stages planned yet.</div>
              <div v-if="store.templateForProjectType(project.type)" class="flex items-center gap-2 flex-wrap">
                <button type="button" class="desk-save-btn" @click="seedFromTemplate">
                  + Seed from {{ project.type }} template
                </button>
                <RouterLink :to="{ name: 'stage-planning-new', query: { projectId: project.id } }" class="desk-link text-xs">
                  or plan one manually →
                </RouterLink>
                <div class="basis-full text-[11px] text-ink-500 mt-1">
                  Will seed {{ store.templateForProjectType(project.type).defaultStages.length }} stages —
                  {{ store.templateForProjectType(project.type).defaultStages.map(s => s.stageName).join(' → ') }}.
                </div>
              </div>
              <div v-else class="flex items-center gap-2 flex-wrap">
                <RouterLink :to="{ name: 'stage-planning-new', query: { projectId: project.id } }" class="desk-save-btn">
                  + Plan first stage
                </RouterLink>
                <div class="basis-full text-[11px] text-ink-500 mt-1 italic">
                  No template configured for project type "{{ project.type }}" — plan stages manually.
                </div>
              </div>
            </div>
          </template>
        </DocTypeListView>
      </div>

      <!-- BOQ -->
      <div v-if="tab === 'boq'" class="pt-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs text-ink-500">
            {{ boqs.length }} BOQ revision{{ boqs.length === 1 ? '' : 's' }}
            <template v-if="activeBoq">
              · active: <DeskLink :to="`/boq/${activeBoq.id}`" class="font-mono">{{ activeBoq.id }}</DeskLink>
              ({{ fmtCompactINR(store.boqTotals(activeBoq.id).planned) }} planned · {{ fmtCompactINR(store.boqTotals(activeBoq.id).actual) }} actual)
            </template>
          </span>
          <RouterLink to="/boq" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1 border border-ink-200 bg-white ml-auto" style="border-radius: 2px;">Open BOQ module →</RouterLink>
        </div>
        <DeskList
          v-model="boqSearch"
          :rows="boqsFiltered"
          :columns="boqCols"
          row-key="id"
          search-placeholder="Search BOQ revisions…"
          @row-click="onBoqRowClick"
        >
          <template #cell-id="{ row }">
            <DeskLink :to="`/boq/${row.id}`" @click.stop class="font-mono text-xs">{{ row.id }}</DeskLink>
          </template>
          <template #cell-title="{ row }">
            <span class="text-ink-900 text-xs">{{ row.title }}</span>
          </template>
          <template #cell-revision="{ row }">
            <span class="font-mono text-xs">R{{ row.revision }}</span>
          </template>
          <template #cell-status="{ row }">
            <StatusBadge :status="row.status" />
          </template>
          <template #cell-sourceScoId="{ row }">
            <span class="text-xs font-mono text-ink-500">{{ row.sourceScoId || '—' }}</span>
          </template>
          <template #cell-planned="{ row }">
            <span class="tabular-nums">{{ fmtCompactINR(store.boqTotals(row.id).planned) }}</span>
          </template>
          <template #cell-actual="{ row }">
            <span class="tabular-nums text-ink-700">{{ fmtCompactINR(store.boqTotals(row.id).actual) }}</span>
          </template>
          <template #cell-preparedDate="{ row }">
            <span class="text-xs text-ink-500">{{ fmtDate(row.preparedDate) }}</span>
          </template>
          <template #empty>
            <div class="text-sm text-ink-500">
              No BOQ on this project ·
              <RouterLink to="/boq" class="desk-link">Create one in the BOQ module →</RouterLink>
            </div>
          </template>
        </DeskList>
      </div>

      <!-- SCOs -->
      <div v-if="tab === 'scos'" class="pt-4">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-xs text-ink-500">
            <span class="text-ink-900 font-medium">{{ scos.length }} scope change{{ scos.length === 1 ? '' : 's' }}</span>
          </span>
          <RouterLink to="/sco" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1 border border-ink-200 bg-white ml-auto" style="border-radius: 2px;">Open SCO module →</RouterLink>
        </div>
        <DeskList
          v-model="scoSearch"
          :rows="scosFiltered"
          :columns="scoCols"
          row-key="id"
          search-placeholder="Search scope changes…"
        >
          <template #cell-id="{ row }">
            <DeskLink to="/sco" class="font-mono text-xs">{{ row.id }}</DeskLink>
          </template>
          <template #cell-title="{ row }">
            <span class="text-ink-900">{{ row.title }}</span>
          </template>
          <template #cell-impact="{ row }">
            <span class="tabular-nums" :class="row.impact >= 0 ? 'text-danger-700' : 'text-success-700'">
              {{ row.impact >= 0 ? '+' : '' }}{{ fmtINR(Math.abs(row.impact)) }}
            </span>
          </template>
          <template #cell-status="{ row }">
            <StatusBadge :status="row.status" />
          </template>
          <template #cell-raisedBy="{ row }">
            <UserAvatar :user-id="row.raisedBy" size="xs" />
          </template>
          <template #empty>
            <div class="text-sm text-ink-500">No scope changes on this project.</div>
          </template>
        </DeskList>
      </div>

      <AttachmentsTab
        v-if="tab === 'attachments'"
        :project-id="resolvedProjectId"
        @count-change="loadFileCount(resolvedProjectId)"
      />

      <TeamTab
        v-if="tab === 'team'"
        :project="project"
        :team="projectTeam"
        :team-cols="teamCols"
        :has-candidates="availableTeamCandidates.length > 0"
        @add="openTeamModal"
        @remove="removeTeamMember"
      />

      <ActivityTab
        v-if="tab === 'activity'"
        :project="project"
      />

      <!-- Comments / Attachments / Assignment — stub footer per CLAUDE.md §12.4 Desk convention -->
      <section class="mt-8 pt-4 border-t border-ink-200">
        <div class="flex items-center gap-6 text-xs text-ink-500 flex-wrap">
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('message-circle')" />
            <span>Comments — <span class="font-medium text-ink-700">0</span></span>
            <span class="text-ink-400 italic ml-1">stub</span>
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('paperclip')" />
            <span>Attachments — <span class="font-medium text-ink-700">0</span></span>
            <span class="text-ink-400 italic ml-1">stub</span>
          </div>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-ink-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('users')" />
            <span>Assigned to —</span>
            <UserAvatar :user-id="project.pm" size="xs" />
          </div>
        </div>
      </section>
    </div>

    <ProjectEditModal
      :open="editing"
      :project="project"
      :edit-form="editForm"
      :errors="editErrors"
      :is-subproject="isSubproject"
      :subs-count="subs.length"
      :is-multi-company="store.isMultiCompany"
      @close="cancelEdit"
      @save="saveEdit"
      @clear-error="clearEditError"
    />

    <ProjectTeamMemberModal
      :open="teamModalOpen"
      :project-name="project?.name || ''"
      :available-team-candidates="availableTeamCandidates"
      :team-pick-user-id="teamPickUserId"
      @update:team-pick-user-id="(value) => (teamPickUserId = value)"
      @close="closeTeamModal"
      @confirm="confirmAddMember"
    />

    <!-- Delete confirmation dialog -->
    <ConfirmDialog
      v-model:open="showDeleteConfirm"
      title="Delete project"
      :message="`Delete '${project?.name}' and all its subprojects, work packages, and tasks? This cannot be undone.`"
      confirm-label="Delete"
      :destructive="true"
      :loading="deleteLoading"
      @confirm="confirmDelete"
    />
  </DeskPage>

  <div v-else class="px-6 py-20 text-center">
    <div class="text-ink-400 mb-3">Project not found</div>
    <RouterLink to="/projects" class="desk-link text-sm">Back to projects</RouterLink>
  </div>
</template>
