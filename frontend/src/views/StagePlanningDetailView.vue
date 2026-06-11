<script setup>
// Stage Planning detail — adapter-backed. UI follows the prototype detail
// layout (KPI strip, details card, StageTaskPicker for tasks, edit modal).
// Workflow approval / activity log surfaces are omitted until the backend
// DocType carries those fields.

import { ref, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { useSessionStore } from '@/stores/session'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import { createDataAdapter } from '@/data/adapters'

// Mirrors the workflow fixture — drives available actions and edit permission client-side.
const WORKFLOW_ACTIONS = {
  'Draft': [
    { action: 'Submit for Approval', roles: ['Projects User', 'Projects Manager', 'System Manager'], variant: 'primary' },
  ],
  'Pending Approval': [
    { action: 'Approve', roles: ['Projects Manager', 'System Manager'], variant: 'success' },
    { action: 'Reject', roles: ['Projects Manager', 'System Manager'], variant: 'danger' },
  ],
  // Rejected is terminal — Revise is no longer allowed after a rejection.
  // A rejected stage can be edited/deleted but not pushed back into the cycle.
  'Rejected': [],
  'Approved': [
    { action: 'Revise', roles: ['Projects Manager', 'System Manager'], variant: 'warning' },
    { action: 'Cancel', roles: ['Projects Manager', 'System Manager'], variant: 'danger' },
  ],
}

// Roles allowed to edit the document in each workflow state (matches `allow_edit` in fixture).
const STATE_EDIT_ROLES = {
  'Draft': ['Projects User', 'Projects Manager', 'System Manager'],
  'Pending Approval': ['Projects Manager', 'System Manager'],
  'Approved': ['System Manager'],
  'Rejected': ['Projects User', 'Projects Manager', 'System Manager'],
  'Cancelled': ['System Manager'],
}
import StatusBadge from '@/components/StatusBadge.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import StageTaskPicker from '@/components/StageTaskPicker.vue'
import StageDelayReasonModal from '@/components/StageDelayReasonModal.vue'
import { fmtDate } from '@/utils/format'
import { toDateInputValue } from '@/utils/dateInput'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()
const session = useSessionStore()
const adapter = createDataAdapter(store)

const TODAY_ISO = new Date().toISOString().slice(0, 10)

function firstResourceRow(resource) {
  if (resource?.doc) return resource.doc
  const raw = resource?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  if (raw && typeof raw === 'object' && 'value' in raw) return raw.value || null
  return raw || null
}

function resourceRows(resource) {
  const raw = resource?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
}

function mapChildRowsFromBackend(rows) {
  return (rows || []).map((r, idx) => ({
    name: r?.name || '',
    id: r?.name || `row-${idx}`,
    task: r?.task || '',
    plannedStart: r?.planned_start || null,
    plannedEnd: r?.planned_end || null,
    plannedQty: Number(r?.planned_qty ?? 100),
    qtyUnit: r?.qty_unit || '%',
  }))
}

function mapStageRow(row) {
  if (!row) return null
  return {
    id: row.name || '',
    stageName: row.stage_name || '',
    project: row.project || '',
    workflowState: row.workflow_state || 'Draft',
    rejectReason: row.reject_reason || '',
    delayReasonsCount: (row.delay_reasons || []).length,
    plannedStart: row.planned_start || null,
    plannedEnd: row.planned_end || null,
    plannedTaskCount: Number(row.planned_task_count) || 0,
    plannedCompletionPct: Number(row.planned_completion_pct) || 0,
    description: row.description || '',
    dependencies: (row.dependencies || []).map((d) => d.stage).filter(Boolean),
    stagePlanningTasks: mapChildRowsFromBackend(row.stage_planning_tasks),
  }
}

function childRowName(row) {
  if (row?.name) return row.name
  const id = String(row?.id || '')
  if (!id || id.startsWith('SPT-') || id.startsWith('row-')) return ''
  return id
}

function mapChildRowsToBackend(rows) {
  return (rows || [])
    .filter((r) => r && r.task)
    .map((r) => {
      const out = {
        task: r.task,
        planned_start: r.plannedStart || null,
        planned_end: r.plannedEnd || null,
        planned_qty: Number(r.plannedQty ?? 100),
        qty_unit: r.qtyUnit || '%',
      }
      const name = childRowName(r)
      if (name) out.name = name
      return out
    })
}

const stageResource = ref(null)

function loadStageResource() {
  if (!props.id) {
    stageResource.value = null
    return
  }
  stageResource.value = adapter.read('Stage Planning', props.id, {
    fields: [
      'name',
      'stage_name',
      'project',
      'workflow_state',
      'planned_start',
      'planned_end',
      'planned_task_count',
      'planned_completion_pct',
      'description',
      'dependencies',
      'stage_planning_tasks',
      'delay_reasons',
    ],
    cache: `buildsuite-stage-detail:${props.id}`,
    transform(rows) {
      return rows.map(mapStageRow)
    },
  })
}

watch(() => props.id, loadStageResource, { immediate: true })

const stage = computed(() => {
  const backend = firstResourceRow(stageResource.value)
  if (backend) return backend
  const local = store.stagePlanningById(props.id)
  return local || null
})

const projectResource = ref(null)

function loadProjectResource(projectId) {
  if (!projectId) {
    projectResource.value = null
    return
  }
  projectResource.value = adapter.read('Project', projectId, {
    fields: ['name', 'project_name'],
    cache: `buildsuite-stage-detail-project:${projectId}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || '',
        name: row?.project_name || row?.name || '',
      }))
    },
  })
}

watch(() => stage.value?.project, loadProjectResource, { immediate: true })

const project = computed(() => {
  const backend = firstResourceRow(projectResource.value)
  if (backend) return backend
  return stage.value ? store.projectById(stage.value.project) : null
})

const projectStagesResource = ref(null)

function loadProjectStagesResource(projectId) {
  if (!projectId) {
    projectStagesResource.value = null
    return
  }
  projectStagesResource.value = adapter.list('Stage Planning', {
    fields: ['name', 'stage_name', 'project'],
    filters: [['project', '=', projectId]],
    pageLength: 200,
    cache: `buildsuite-stage-detail-siblings:${projectId}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || '',
        stageName: row?.stage_name || row?.name || '',
        project: row?.project || '',
      }))
    },
  })
}

watch(() => stage.value?.project, loadProjectStagesResource, { immediate: true })

const projectStages = computed(() => resourceRows(projectStagesResource.value))

const stagesById = computed(() => {
  const map = {}
  for (const s of projectStages.value) map[s.id] = s
  if (stage.value) map[stage.value.id] = stage.value
  return map
})

const siblingStages = computed(() => {
  if (!stage.value) return []
  return projectStages.value.filter((sp) => sp.id !== stage.value.id)
})

const tasksResource = ref(null)

function loadTasksResource(projectId) {
  if (!projectId) {
    tasksResource.value = null
    return
  }
  tasksResource.value = adapter.list('Task', {
    fields: ['name', 'subject', 'status', 'progress'],
    filters: [['project', '=', projectId]],
    pageLength: 500,
    cache: `buildsuite-stage-detail-tasks:${projectId}`,
    transform(rows) {
      return rows.map((row) => ({
        id: row?.name || '',
        name: row?.subject || row?.name || '',
        status: row?.status || 'Open',
        progress: Number(row?.progress) || 0,
      }))
    },
  })
}

watch(() => stage.value?.project, loadTasksResource, { immediate: true })

const tasksById = computed(() => {
  const map = {}
  for (const t of resourceRows(tasksResource.value)) {
    map[t.id] = t
  }
  for (const t of (stage.value?.project ? store.tasksByProject(stage.value.project) : [])) {
    if (!map[t.id]) map[t.id] = t
  }
  return map
})

function taskName(id) { return tasksById.value[id]?.name || id }
function taskStatus(id) { return tasksById.value[id]?.status || '—' }

const editing = ref(false)
const saving = ref(false)
const editForm = ref({})
const showDeleteConfirm = ref(false)
const pickerOpen = ref(false)
const workflowActing = ref(null)
const showRejectModal = ref(false)
const rejectReason = ref('')
const rejectError = ref('')
const reviewGateOpen = ref(false)

// Stage Review entry. If the stage is running behind and no delay reason is on
// file yet, require one first (gate); otherwise open the review directly.
function onStageReview() {
  if (!stage.value) return
  if (isStageDelayed.value && (stage.value.delayReasonsCount || 0) === 0) {
    reviewGateOpen.value = true
    return
  }
  router.push(`/stage-plannings/${stage.value.id}/review`)
}
function onGateSaved() {
  if (stage.value) router.push(`/stage-plannings/${stage.value.id}/review`)
}

const userRoles = computed(() => session.access?.roles || [])

const availableActions = computed(() => {
  const state = stage.value?.workflowState || 'Draft'
  return (WORKFLOW_ACTIONS[state] || []).filter(
    (a) => a.roles.some((r) => userRoles.value.includes(r)),
  )
})

const canEdit = computed(() => {
  const state = stage.value?.workflowState || 'Draft'
  const editRoles = STATE_EDIT_ROLES[state] || []
  return editRoles.some((r) => userRoles.value.includes(r))
})

async function applyWorkflowAction(action) {
  if (!stage.value) return
  workflowActing.value = action
  try {
    const body = new URLSearchParams({
      doc: JSON.stringify({ doctype: 'Stage Planning', name: stage.value.id }),
      action,
    })
    const response = await fetch('/api/method/frappe.model.workflow.apply_workflow', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Frappe-CSRF-Token': window.csrf_token || '',
      },
      body: body.toString(),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data?.exception || data?.exc_type || `HTTP ${response.status}`)
    }
    await stageResource.value?.reload?.()
    showToast(`${action} applied`)
  } catch (err) {
    showToast(err.message || `Failed to apply ${action}`, 'error')
  } finally {
    workflowActing.value = null
  }
}

function openRejectModal() {
  rejectReason.value = ''
  rejectError.value = ''
  showRejectModal.value = true
}

async function confirmReject() {
  if (!stage.value) return
  const reason = rejectReason.value.trim()
  if (!reason) {
    rejectError.value = 'Please enter a rejection reason.'
    return
  }
  rejectError.value = ''
  workflowActing.value = 'Reject'
  try {
    const body = new URLSearchParams({ name: stage.value.id, reason })
    const response = await fetch(
      '/api/method/buildsuite_core.buildsuite_core.doctype.stage_planning.stage_planning.reject_stage_planning',
      {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Frappe-CSRF-Token': window.csrf_token || '',
        },
        body: body.toString(),
      },
    )
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data?.exception || data?.exc_type || `HTTP ${response.status}`)
    }
    showRejectModal.value = false
    await stageResource.value?.reload?.()
    showToast('Stage rejected')
  } catch (err) {
    rejectError.value = err.message || 'Failed to reject stage'
  } finally {
    workflowActing.value = null
  }
}

const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
  stage_name: 'stageName',
  planned_start: 'plannedStart',
  planned_end: 'plannedEnd',
  project: 'project',
})

function snapshotStage(s) {
  if (!s) return {}
  const data = JSON.parse(JSON.stringify(s))
  data.plannedStart = toDateInputValue(data.plannedStart)
  data.plannedEnd = toDateInputValue(data.plannedEnd)
  return data
}

watch(stage, (s) => {
  if (s && !editing.value) editForm.value = snapshotStage(s)
}, { immediate: true })

function startEdit() {
  if (!canEdit.value) return
  editForm.value = snapshotStage(stage.value)
  setErrors({})
  editing.value = true
}

function cancelEdit() {
  editForm.value = snapshotStage(stage.value)
  setErrors({})
  editing.value = false
}

function toggleDependency(depId) {
  const list = [...(editForm.value.dependencies || [])]
  const i = list.indexOf(depId)
  if (i === -1) list.push(depId)
  else list.splice(i, 1)
  editForm.value.dependencies = list
}

function validateEdit() {
  const e = {}
  if (!editForm.value.stageName?.trim()) e.stageName = 'Stage name is required'
  if (editForm.value.plannedEnd && editForm.value.plannedStart
    && editForm.value.plannedEnd < editForm.value.plannedStart) {
    e.plannedEnd = 'End must be on or after start'
  }
  setErrors(e)
  return Object.keys(e).length === 0
}

async function saveEdit() {
  if (!validateEdit() || !stage.value) return
  saving.value = true
  try {
    await adapter.update('Stage Planning', stage.value.id, {
      stage_name: editForm.value.stageName.trim(),
      planned_start: editForm.value.plannedStart || null,
      planned_end: editForm.value.plannedEnd || null,
      description: editForm.value.description || '',
      dependencies: (editForm.value.dependencies || []).map((dep) => ({ stage: dep })),
    })
    await stageResource.value?.reload?.()
    editing.value = false
    showToast('Stage updated')
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update stage', 'error')
  } finally {
    saving.value = false
  }
}

async function persistChildRows(rows) {
  if (!stage.value) return
  const childRows = mapChildRowsToBackend(rows)
  saving.value = true
  try {
    await adapter.update('Stage Planning', stage.value.id, {
      stage_planning_tasks: childRows,
      planned_task_count: childRows.length,
    })
    await stageResource.value?.reload?.()
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update stage tasks', 'error')
    throw err
  } finally {
    saving.value = false
  }
}

async function onPickerSave(payload) {
  try {
    await persistChildRows(payload?.newChildRows || [])
    showToast('Stage tasks updated')
  } catch {
    // toast already shown
  }
}

async function onPlannedQtyChange(row, value) {
  if (!stage.value || !row) return
  const qty = Math.max(0, Math.min(100, Number(value) || 0))
  const nextRows = (stage.value.stagePlanningTasks || []).map((r) => (
    r.id === row.id ? { ...r, plannedQty: qty, qtyUnit: '%' } : r
  ))
  try {
    await persistChildRows(nextRows)
  } catch {
    // toast already shown
  }
}

function openPicker() { pickerOpen.value = true }

async function confirmDelete() {
  if (!stage.value) return
  try {
    await adapter.remove('Stage Planning', stage.value.id)
    showDeleteConfirm.value = false
    if (project.value) router.push(`/projects/${project.value.id}`)
    else router.push('/stage-plannings')
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to delete stage', 'error')
  }
}

const stageDurationDays = computed(() => {
  const s = stage.value
  if (!s?.plannedStart || !s?.plannedEnd) return null
  const days = Math.ceil((new Date(s.plannedEnd) - new Date(s.plannedStart)) / 86400000) + 1
  return Math.max(0, days)
})

const stageTaskStats = computed(() => {
  const rows = stage.value?.stagePlanningTasks || []
  let completed = 0
  let inProgress = 0
  for (const r of rows) {
    const t = tasksById.value[r.task]
    if (!t) continue
    const progress = Number(t.progress) || 0
    if (progress >= 100) completed++
    else if (progress > 0) inProgress++
  }
  return { total: rows.length, completed, inProgress }
})

const dependencyCount = computed(() => (stage.value?.dependencies || []).length)

// Stage Review gate — is this stage running behind? (a) past planned end with
// unfinished work, or (b) calendar-expected beats actual mean progress by > 15 pts.
const meanActualProgress = computed(() => {
  const rows = stage.value?.stagePlanningTasks || []
  if (!rows.length) return 0
  const sum = rows.reduce((acc, r) => acc + (Number(tasksById.value[r.task]?.progress) || 0), 0)
  return Math.round(sum / rows.length)
})
const expectedProgressNow = computed(() => {
  const s = stage.value
  if (!s?.plannedStart || !s?.plannedEnd) return null
  const total = (new Date(s.plannedEnd) - new Date(s.plannedStart)) / 86400000
  if (total <= 0) return 0
  const elapsed = (new Date(TODAY_ISO) - new Date(s.plannedStart)) / 86400000
  return Math.max(0, Math.min(100, Math.round((elapsed / total) * 100)))
})
const isStageDelayed = computed(() => {
  const s = stage.value
  if (!s) return false
  if (s.plannedEnd && s.plannedEnd < TODAY_ISO && meanActualProgress.value < 100) return true
  if (expectedProgressNow.value !== null && expectedProgressNow.value > 0 && (expectedProgressNow.value - meanActualProgress.value) > 15) return true
  return false
})

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Stage Planning', to: '/stage-plannings' },
  ]
  if (project.value) out.push({ label: project.value.name, to: `/projects/${project.value.id}` })
  return out
})
</script>

<template>
  <DeskPage
    v-if="stage"
    :title="stage.stageName"
    :subtitle="`${stage.id} · ${project ? project.name : stage.project}`"
    :status="stage.workflowState"
    :breadcrumbs="breadcrumbs"
  >
    <template #actions>
      <!-- Stage Review — available in every state; gates on a delay reason if behind -->
      <button
        type="button"
        class="text-xs px-2.5 py-1 border border-brand-200 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium dark:bg-brand-950/30 dark:border-brand-800 dark:text-brand-300 dark:hover:bg-brand-950/50"
        style="border-radius: 6px;"
        @click="onStageReview"
      >Stage Review</button>

      <!-- Workflow action buttons -->
      <template v-for="wf in availableActions" :key="wf.action">
        <button
          v-if="wf.variant === 'primary'"
          type="button"
          class="desk-save-btn"
          :disabled="!!workflowActing"
          @click="applyWorkflowAction(wf.action)"
        >{{ workflowActing === wf.action ? `${wf.action}…` : wf.action }}</button>
        <button
          v-else-if="wf.variant === 'success'"
          type="button"
          class="text-xs px-2.5 py-1 bg-success-600 hover:bg-success-700 text-white font-medium"
          style="border-radius: 6px;"
          :disabled="!!workflowActing"
          @click="applyWorkflowAction(wf.action)"
        >{{ workflowActing === wf.action ? `${wf.action}…` : wf.action }}</button>
        <button
          v-else-if="wf.variant === 'warning'"
          type="button"
          class="text-xs px-2.5 py-1 border border-warning-300 bg-white hover:bg-warning-50 text-warning-700 dark:bg-ink-800 dark:border-ink-700 dark:hover:bg-ink-700"
          style="border-radius: 6px;"
          :disabled="!!workflowActing"
          @click="applyWorkflowAction(wf.action)"
        >{{ workflowActing === wf.action ? `${wf.action}…` : wf.action }}</button>
        <button
          v-else-if="wf.variant === 'danger'"
          type="button"
          class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700 dark:bg-ink-800 dark:border-ink-700 dark:hover:bg-ink-700"
          style="border-radius: 6px;"
          :disabled="!!workflowActing"
          @click="wf.action === 'Reject' ? openRejectModal() : applyWorkflowAction(wf.action)"
        >{{ workflowActing === wf.action ? `${wf.action}…` : wf.action }}</button>
      </template>

      <!-- Edit only shown when the current state permits editing for this user's roles -->
      <button
        v-if="canEdit"
        type="button"
        class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:hover:bg-ink-700"
        style="border-radius: 6px;"
        @click="startEdit"
      >Edit</button>

      <button
        type="button"
        class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700 dark:bg-ink-800 dark:border-ink-700 dark:hover:bg-ink-700"
        style="border-radius: 6px;"
        @click="showDeleteConfirm = true"
      >Delete</button>
    </template>

    <!-- Rejected banner -->
    <div
      v-if="stage.workflowState === 'Rejected'"
      class="mb-5 px-4 py-3 border border-danger-200 bg-danger-50 dark:bg-ink-800 dark:border-danger-700"
      style="border-radius: 8px;"
    >
      <div class="text-[11px] uppercase tracking-wider font-semibold text-danger-700 mb-1">
        Stage rejected
      </div>
      <div v-if="stage.rejectReason" class="text-sm text-ink-800 dark:text-[#D4D4D4] whitespace-pre-line">
        {{ stage.rejectReason }}
      </div>
      <div v-else class="text-sm text-ink-500 italic">No reason recorded.</div>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium flex items-center gap-1.5">
          <svg class="w-3 h-3 text-ink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('calendar')" />
          Window
        </div>
        <div class="text-sm font-semibold text-ink-900 mt-1.5 dark:text-[#F5F5F5]">{{ fmtDate(stage.plannedStart) || '—' }}</div>
        <div class="text-[11px] text-ink-500 mt-0.5">to {{ fmtDate(stage.plannedEnd) || '—' }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium flex items-center gap-1.5">
          <svg class="w-3 h-3 text-ink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('chart-line')" />
          Duration
        </div>
        <div class="text-lg font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">
          {{ stageDurationDays !== null ? stageDurationDays : '—' }}
          <span v-if="stageDurationDays !== null" class="text-xs text-ink-500 font-normal">day{{ stageDurationDays === 1 ? '' : 's' }}</span>
        </div>
      </div>
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium flex items-center gap-1.5">
          <svg class="w-3 h-3 text-ink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('clipboard-list')" />
          Tasks
        </div>
        <div class="text-lg font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">{{ stageTaskStats.total }}</div>
        <div class="text-[11px] text-ink-500 mt-0.5">
          <span class="text-success-700 font-medium">{{ stageTaskStats.completed }}</span> done ·
          <span class="text-info-700 font-medium">{{ stageTaskStats.inProgress }}</span> in progress
        </div>
      </div>
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium flex items-center gap-1.5">
          <svg class="w-3 h-3 text-ink-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('refresh-ccw')" />
          Dependencies
        </div>
        <div class="text-lg font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">{{ dependencyCount }}</div>
        <div class="text-[11px] text-ink-500 mt-0.5">
          {{ dependencyCount === 0 ? 'starts independently' : (dependencyCount === 1 ? 'stage must complete first' : 'stages must complete first') }}
        </div>
      </div>
    </div>

    <!-- Stage details card -->
    <section class="bg-white border border-ink-200 overflow-hidden mb-5 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 12px;">
      <header class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2 dark:from-brand-950/30 dark:to-[#242424] dark:border-ink-700">
        <svg class="w-4 h-4 text-brand-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('info')" />
        <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">Stage details</h2>
      </header>
      <div class="p-5 space-y-4">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Project</div>
          <div class="text-sm mt-1">
            <DeskLink v-if="project" :to="`/projects/${project.id}`">{{ project.name }}</DeskLink>
            <span v-else class="text-ink-500">{{ stage.project }}</span>
          </div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Description</div>
          <div class="text-sm text-ink-700 mt-1 whitespace-pre-line dark:text-ink-300">{{ stage.description || '—' }}</div>
        </div>
      </div>
    </section>

    <!-- Dependencies -->
    <DeskSection title="Dependencies">
      <div class="md:col-span-2">
        <div v-if="(stage.dependencies || []).length" class="flex flex-wrap gap-1.5">
          <DeskLink
            v-for="depId in stage.dependencies"
            :key="depId"
            :to="`/stage-plannings/${depId}`"
            class="text-[11px] px-2 py-0.5 bg-brand-50 text-brand-700 font-medium hover:no-underline dark:bg-brand-950/30 dark:text-brand-300"
            style="border-radius: 9999px;"
          >{{ stagesById[depId]?.stageName || depId }}</DeskLink>
        </div>
        <div v-else class="text-xs text-ink-400 italic">No dependencies · this stage can start independently.</div>
      </div>
    </DeskSection>

    <!-- Tasks in this stage -->
    <section class="mb-6">
      <div class="flex items-center justify-between mb-2">
        <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Tasks in this stage</div>
        <div class="flex items-center gap-3">
          <span class="text-[11px] text-ink-500 tabular-nums">
            {{ (stage.stagePlanningTasks || []).length }} task{{ (stage.stagePlanningTasks || []).length === 1 ? '' : 's' }}
          </span>
          <button
            type="button"
            class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
            style="border-radius: 6px;"
            :disabled="saving"
            @click="openPicker"
          >Add/Remove Tasks</button>
        </div>
      </div>
      <div class="md:col-span-2">
        <div v-if="(stage.stagePlanningTasks || []).length" class="border border-ink-200 dark:border-ink-700" style="border-radius: 6px;">
          <div
            class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium dark:bg-ink-800 dark:border-ink-700"
            style="grid-template-columns: minmax(220px, 1fr) 110px 110px 110px 110px;"
          >
            <div class="px-3 py-1.5">Task</div>
            <div class="px-3 py-1.5">Planned Start</div>
            <div class="px-3 py-1.5">Planned End</div>
            <div class="px-3 py-1.5 text-right">Planned Qty (%)</div>
            <div class="px-3 py-1.5">Status</div>
          </div>
          <div
            v-for="row in stage.stagePlanningTasks"
            :key="row.id"
            class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 text-sm text-ink-800 items-center dark:border-ink-800 dark:hover:bg-brand-950/20"
            style="grid-template-columns: minmax(220px, 1fr) 110px 110px 110px 110px;"
          >
            <div class="px-3 py-1.5">
              <RouterLink
                v-if="row.task"
                :to="`/tasks/${row.task}`"
                class="text-ink-900 font-medium hover:underline dark:text-[#F5F5F5]"
              >{{ taskName(row.task) }}</RouterLink>
              <span v-else class="text-ink-400 italic">No task linked</span>
            </div>
            <div class="px-3 py-1.5 text-xs text-ink-700 dark:text-ink-300">{{ fmtDate(row.plannedStart) || '—' }}</div>
            <div class="px-3 py-1.5 text-xs text-ink-700 dark:text-ink-300">{{ fmtDate(row.plannedEnd) || '—' }}</div>
            <div class="px-2 py-1">
              <div class="flex items-center gap-1 justify-end">
                <DeskInput
                  :model-value="row.plannedQty ?? 100"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  class="!text-xs !text-right !py-1"
                  :disabled="saving"
                  @update:model-value="onPlannedQtyChange(row, $event)"
                />
                <span class="text-[11px] text-ink-500">%</span>
              </div>
            </div>
            <div class="px-3 py-1.5 whitespace-nowrap">
              <StatusBadge v-if="row.task" :status="taskStatus(row.task)" size="xs" />
              <span v-else class="text-[10px] text-ink-400">—</span>
            </div>
          </div>
        </div>
        <div v-else class="text-xs text-ink-400 italic">
          No task rows yet · click "Add/Remove Tasks" above to pick tasks for this stage.
        </div>
      </div>
    </section>

    <!-- Edit modal -->
    <Teleport to="body">
      <div
        v-if="editing"
        class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
        @click.self="cancelEdit"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-3xl shadow-fp-lg flex flex-col dark:bg-[#242424] dark:border-ink-700"
          style="border-radius: 12px; max-height: calc(100vh - 3rem);"
          @click.stop
        >
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white dark:bg-[#242424] dark:border-ink-700" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">Edit stage</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">
                {{ stage.stageName }}<template v-if="project"> · {{ project.name }}</template>
              </p>
            </div>
            <button
              type="button"
              class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3 dark:text-ink-400 dark:hover:text-ink-200"
              aria-label="Close"
              @click="cancelEdit"
            >×</button>
          </header>

          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Stage details">
              <DeskField label="Stage name" required :error="errors.stageName">
                <DeskInput v-model="editForm.stageName" @input="clearError('stageName')" />
              </DeskField>
              <DeskField label="Project" hint="Locked after create — move tasks instead of reparenting a stage.">
                <DeskInput :model-value="project ? project.name : editForm.project" disabled />
              </DeskField>
              <DeskField label="Planned start">
                <DeskInput v-model="editForm.plannedStart" type="date" />
              </DeskField>
              <DeskField label="Planned end" :error="errors.plannedEnd">
                <DeskInput v-model="editForm.plannedEnd" type="date" @input="clearError('plannedEnd')" />
              </DeskField>
              <DeskField label="Description">
                <DeskTextarea v-model="editForm.description" :rows="3" />
              </DeskField>
            </DeskSection>

            <DeskSection title="Dependencies">
              <div class="md:col-span-2">
                <div v-if="siblingStages.length" class="flex flex-wrap gap-2">
                  <label
                    v-for="sib in siblingStages"
                    :key="sib.id"
                    class="inline-flex items-center gap-1.5 text-xs text-ink-800 cursor-pointer px-2 py-1 border border-ink-200 hover:bg-ink-50 dark:border-ink-700 dark:hover:bg-ink-800"
                    style="border-radius: 6px;"
                  >
                    <input
                      type="checkbox"
                      :checked="(editForm.dependencies || []).includes(sib.id)"
                      class="accent-brand-600"
                      @change="toggleDependency(sib.id)"
                    />
                    <span class="font-mono text-[10px] text-ink-500">{{ sib.id }}</span>
                    <span>{{ sib.stageName }}</span>
                  </label>
                </div>
                <div v-else class="text-xs text-ink-400 italic">
                  No other stages on this project yet · add one to create a dependency.
                </div>
                <div class="text-[11px] text-ink-500 mt-1.5">
                  Pick the stages that must complete before this one can start.
                </div>
              </div>
            </DeskSection>

            <DeskSection title="Tasks">
              <div class="md:col-span-2 text-xs text-ink-500">
                {{ (stage.stagePlanningTasks || []).length }} task{{ (stage.stagePlanningTasks || []).length === 1 ? '' : 's' }} linked
                · manage via the <span class="font-medium text-ink-700 dark:text-ink-300">Add/Remove Tasks</span> button on the page.
              </div>
            </DeskSection>
          </div>

          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white dark:bg-[#242424] dark:border-ink-700" style="border-radius: 0 0 12px 12px;">
            <button
              type="button"
              class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
              style="border-radius: 6px;"
              :disabled="saving"
              @click="cancelEdit"
            >Cancel</button>
            <button
              type="button"
              class="desk-save-btn"
              :disabled="saving"
              @click="saveEdit"
            >{{ saving ? 'Saving…' : 'Save' }}</button>
          </footer>
        </div>
      </div>
    </Teleport>

    <StageTaskPicker
      v-model:open="pickerOpen"
      :project-id="stage.project"
      :stage-name="stage.stageName"
      :planned-start="stage.plannedStart || ''"
      :planned-end="stage.plannedEnd || ''"
      :initial-selected-task-ids="(stage.stagePlanningTasks || []).map((r) => r.task).filter(Boolean)"
      :existing-task-rows="stage.stagePlanningTasks || []"
      mode="modal"
      @save="onPickerSave"
    />

    <!-- Stage Review delay gate -->
    <StageDelayReasonModal
      v-model:open="reviewGateOpen"
      :stage-id="stage.id"
      :stage-name="stage.stageName"
      :is-gate="true"
      @saved="onGateSaved"
    />

    <!-- Reject modal -->
    <Teleport to="body">
      <div
        v-if="showRejectModal"
        class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
        @click.self="showRejectModal = false"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-lg shadow-fp-lg flex flex-col dark:bg-[#242424] dark:border-ink-700"
          style="border-radius: 12px;"
          @click.stop
        >
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 dark:border-ink-700" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">Reject stage</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ stage.stageName }}</p>
            </div>
            <button
              type="button"
              class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3 dark:text-ink-400 dark:hover:text-ink-200"
              aria-label="Close"
              @click="showRejectModal = false"
            >×</button>
          </header>

          <div class="p-5">
            <DeskField label="Rejection reason" required :error="rejectError">
              <DeskTextarea
                v-model="rejectReason"
                :rows="4"
                placeholder="Explain why this stage is being rejected…"
                @input="rejectError = ''"
              />
            </DeskField>
            <p class="text-[11px] text-ink-500 mt-1.5">
              This reason is recorded on the stage. Rejection is final — the stage cannot be revised afterwards.
            </p>
          </div>

          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 dark:border-ink-700" style="border-radius: 0 0 12px 12px;">
            <button
              type="button"
              class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
              style="border-radius: 6px;"
              :disabled="workflowActing === 'Reject'"
              @click="showRejectModal = false"
            >Cancel</button>
            <button
              type="button"
              class="text-xs px-3 py-1.5 bg-danger-600 hover:bg-danger-700 text-white font-medium"
              style="border-radius: 6px;"
              :disabled="workflowActing === 'Reject'"
              @click="confirmReject"
            >{{ workflowActing === 'Reject' ? 'Rejecting…' : 'Reject stage' }}</button>
          </footer>
        </div>
      </div>
    </Teleport>

    <ConfirmDialog
      v-model:open="showDeleteConfirm"
      title="Delete stage"
      :message="`Delete &quot;${stage.stageName}&quot;? Dependencies in other stages pointing at this one will be cleaned up automatically.`"
      confirm-label="Delete"
      :destructive="true"
      @confirm="confirmDelete"
    />
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">
    Stage not found ·
    <RouterLink to="/stage-plannings" class="desk-link">Back to list →</RouterLink>
  </div>
</template>
