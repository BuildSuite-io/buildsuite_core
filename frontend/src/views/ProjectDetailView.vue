<script setup>
// Project Detail — Desk-styled (CLAUDE.md §12.4 destination: Desk in production).
// All computed properties, actions, and store calls are preserved exactly from the
// pre-rebuild version. Only markup and styling change.

import { ref, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { createDataAdapter } from '@/data/adapters'
import { fmtINR, fmtCompactINR, fmtDate } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()
const adapter = createDataAdapter(store)

function firstResourceRow(resource) {
  if (resource?.doc) return resource.doc
  const raw = resource?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  if (raw && typeof raw === 'object' && 'value' in raw) return raw.value || null
  return raw || null
}

/**
 * Compact entity label for console diagnostics: "id (name)".
 */
function entityLabel(id, name) {
  const safeId = id || 'unknown'
  const safeName = name || safeId
  return `${safeId} (${safeName})`
}

/**
 * Builds a single-line text representation of the DocType list query config.
 */
function docTypeListQueryText({ doctype, fields, filters, orderBy, pageLength, start = 0 }) {
  const fieldText = JSON.stringify(fields || ['name'])
  const filterText = JSON.stringify(filters || {})
  return `doctype=${doctype} fields=${fieldText} filters=${filterText} orderBy=${orderBy || ''} start=${start} pageLength=${pageLength ?? ''}`
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
  console.log(
    `[ProjectDetail] Subprojects query | root=${entityLabel(project.value?.id || resolvedProjectId.value, project.value?.name)} | ${docTypeListQueryText({ doctype: 'Project', fields: subprojectFields, filters: subprojectFilters, orderBy: 'modified desc', pageLength: 100 })}`,
  )

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

watch(subs, (rows) => {
  const rootText = entityLabel(project.value?.id || resolvedProjectId.value, project.value?.name)
  const subText = rows.length
    ? rows.map((row) => entityLabel(row.id, row.name)).join(', ')
    : '(none)'
  console.log(`[ProjectDetail] Project scope | root=${rootText} | subprojects=${subText}`)
}, { immediate: true })
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
    'owner_user',
  ]
  const workPackageFilters = {
    project: ['in', workPackageProjectIds.value],
  }
  const workPackageScopeKey = workPackageProjectIds.value.join('|')
  const rootText = entityLabel(project.value?.id || resolvedProjectId.value, project.value?.name)
  const subText = subs.value.length
    ? subs.value.map((row) => entityLabel(row.id, row.name)).join(', ')
    : '(none)'
  console.log(
    `[ProjectDetail] Work Package query | root=${rootText} | subprojects=${subText} | scopeKey=${workPackageScopeKey} | ${docTypeListQueryText({ doctype: 'Work Package', fields: workPackageFields, filters: workPackageFilters, orderBy: 'modified desc', pageLength: 200 })}`,
  )

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
        owner: row?.owner_user || row?.owner || '',
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
  const rootText = entityLabel(project.value?.id || resolvedProjectId.value, project.value?.name)
  const subText = subs.value.length
    ? subs.value.map((row) => entityLabel(row.id, row.name)).join(', ')
    : '(none)'
  console.log(
    `[ProjectDetail] Task query | root=${rootText} | subprojects=${subText} | scopeKey=${taskScopeKey} | ${docTypeListQueryText({ doctype: 'Task', fields: taskFields, filters: taskFilters, orderBy: 'modified desc', pageLength: 300 })}`,
  )

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
const stages = computed(() => store.stagePlanningsByProject(resolvedProjectId.value))
const attachments = computed(() => store.attachmentsByParent('Project', resolvedProjectId.value))
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

const tab = ref('overview')
const editing = ref(false)
const editForm = ref({})

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
function removeTeamMember(userId) {
  if (!userId || userId === project.value?.pm) return
  const m = store.teamMember(userId)
  if (!confirm(`Remove ${m?.name || userId} from this project's team?`)) return
  store.removeProjectTeamMember(resolvedProjectId.value, userId)
}

// Reset to the Overview tab whenever the route navigates to a different
// project record (Vue Router reuses the component instance when only the
// `id` param changes, so the previously-active tab would otherwise persist
// across projects — surfaces a blank panel when clicking into a subproject
// from the parent's Subprojects tab, since Subprojects is filtered out for
// subprojects themselves).
watch(() => props.id, () => {
  tab.value = 'overview'
  editing.value = false
})

function startEdit() {
  editForm.value = { ...project.value }
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
    showToast('Failed to save project', 'error')
    console.error('saveEdit failed:', err)
  }
}
function cancelEdit() {
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
    router.push('/app/projects')
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
  router.push({ path: '/app/projects/new', query: { parentId: resolvedProjectId.value } })
}

function seedFromTemplate() {
  const tpl = store.templateForProjectType(project.value.type)
  if (!tpl) return
  const n = tpl.defaultStages.length
  if (!confirm(`Seed ${n} default stages from the ${project.value.type} template?\n\nThis will create ${n} stages on top of any existing ones — it does not replace or merge.`)) return
  store.seedStagesFromTemplate(resolvedProjectId.value)
}

// ===== Attachments (§13.3 items 13 + 26) =====
// Production uses Frappe's File DocType with persistent storage. In the
// prototype, file bytes are held as browser blob URLs created via
// URL.createObjectURL on upload. **Blob URLs are SESSION-ONLY** — they're lost
// on tab close because the binary lives in the renderer process, not in
// localStorage. The store metadata persists, but clicking a row after a tab
// close will hit a stale URL. This is the documented and expected behavior
// for the prototype.
const fileInput = ref(null)
function openFilePicker() { fileInput.value?.click() }
function onFilesPicked(e) {
  const files = Array.from(e.target.files || [])
  for (const f of files) {
    const url = URL.createObjectURL(f)
    store.addAttachment({
      parentDoctype: 'Project',
      parentId: resolvedProjectId.value,
      fileName: f.name,
      mime: f.type || 'application/octet-stream',
      size: f.size,
      url,
    })
  }
  // Reset so picking the same file twice in a row still fires the change event.
  if (e.target) e.target.value = ''
}
function openAttachment(att) {
  if (!att.url) {
    alert('Seed sample — no actual file attached. Upload a real file to test the open-in-new-tab flow.')
    return
  }
  window.open(att.url, '_blank', 'noopener')
}
function deleteAttachment(att) {
  if (!confirm(`Delete "${att.fileName}"?`)) return
  store.deleteAttachment(att.id)
}
function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
  return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + ' ' + units[i]
}
function fileIcon(mime) {
  if (!mime) return 'file'
  if (mime.startsWith('image/')) return 'image'
  if (mime === 'application/pdf') return 'file-text'
  if (mime.includes('acad') || mime.includes('dwg')) return 'estimation'
  if (mime.includes('word') || mime.includes('document')) return 'file-text'
  if (mime.includes('sheet') || mime.includes('excel')) return 'chart-line'
  if (mime.includes('zip') || mime.includes('compress')) return 'archive'
  return 'file'
}

// Cost roll-up by work package (unchanged from pre-rebuild)
const wpProgress = computed(() => {
  const items = workPackages.value
  if (!items.length) return 0
  return Math.round(items.reduce((a, w) => a + w.progress, 0) / items.length)
})

const taskStats = computed(() => {
  const all = tasks.value
  return {
    total: all.length,
    completed: all.filter(t => t.status === 'Completed').length,
    inProgress: all.filter(t => t.status === 'In Progress').length,
    open: all.filter(t => t.status === 'Open').length,
  }
})

// Visual-only stage status derivation. Same logic as StagePlanningsView; kept
// inline here to avoid an extra import for one helper. NO Stage Review aggregation.
const TODAY_STR = new Date().toISOString().slice(0, 10)
function stageStatus(s) {
  if (!s.plannedStart && !s.plannedEnd) return 'Not Started'
  if (s.plannedStart && TODAY_STR < s.plannedStart) return 'Not Started'
  if (s.plannedEnd   && TODAY_STR > s.plannedEnd)   return 'Complete'
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

// Project-context reports. Same destinations as the Site Execution workspace's
// report tiles — the stub views aren't project-scoped today, but the routing
// is in place so the slugs match.
const projectReports = computed(() => ([
  { slug: 'project-status-summary',  icon: 'chart-line', label: 'Status summary',          desc: 'Status, progress and schedule variance.' },
  { slug: 'stage-vs-actual',         icon: 'calendar',   label: 'Stage plan vs actual',    desc: 'Planned vs completed task counts per stage.' },
  { slug: 'task-completion-by-week', icon: 'chart-line', label: 'Task completion by week', desc: 'Weekly completion burn for this project.' },
  { slug: 'pending-progress-entries',icon: 'file-text',  label: 'Pending progress',        desc: 'Tasks silent for 3+ days.' },
  { slug: 'labour-deployed',         icon: 'workforce',  label: 'Labour deployed',         desc: 'Skilled + unskilled labour by task / week.' },
]))

const tabs = computed(() => {
  // Each tab carries a count when it corresponds to a list of child records.
  // Counts render as " (N)" appended to the label. Overview / Activity have
  // no count.
  const all = [
    { id: 'overview',       label: 'Overview',       count: null },
    { id: 'subprojects',    label: 'Subprojects',    count: subs.value.length },
    { id: 'work-packages',  label: 'Work Packages',  count: workPackages.value.length },
    { id: 'tasks',          label: 'Tasks',          count: tasks.value.length },
    { id: 'stage-planning', label: 'Stage Planning', count: stages.value.length },
    { id: 'boq',            label: 'BOQ',            count: boqs.value.length },
    { id: 'scos',           label: 'Scope Changes',  count: scos.value.length },
    { id: 'attachments',    label: 'Attachments',    count: attachments.value.length },
    { id: 'team',           label: 'Team',           count: projectTeam.value.length },
    { id: 'activity',       label: 'Activity',       count: null },
  ]
  return subprojectsEnabled.value ? all : all.filter(t => t.id !== 'subprojects')
})

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Project', to: '/app/projects' },
  ]
  if (parent.value) out.push({ label: parent.value.name, to: `/app/projects/${parent.value.id}` })
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

// Per-search state for the inner lists (kept simple — each list filters its own
// view via its own search ref). Hooked up to DeskList's v-model.
const subSearch = ref('')
const wpSearch = ref('')
const wpProjectFilter = ref('')
const taskSearch = ref('')
const taskProjectFilter = ref('')
const scoSearch = ref('')
const boqSearch = ref('')

const wpProjectFilterOptions = computed(() => {
  const root = project.value
    ? [{ id: project.value.id, name: project.value.name || project.value.id }]
    : []
  const children = subs.value.map((p) => ({
    id: p.id,
    name: p.name || p.id,
  }))
  return [...root, ...children]
})

const taskProjectFilterOptions = computed(() => {
  const root = project.value
    ? [{ id: project.value.id, name: project.value.name || project.value.id }]
    : []
  const children = subs.value.map((p) => ({
    id: p.id,
    name: p.name || p.id,
  }))
  return [...root, ...children]
})

const taskProjectNameById = computed(() => {
  const map = new Map()
  for (const p of taskProjectFilterOptions.value) {
    map.set(p.id, p.name)
  }
  return map
})

// Utility used by inner list filters: when a parent project is selected,
// include records owned by that parent and all currently loaded subprojects.
function expandProjectFilterIds(selectedProjectId) {
  if (!selectedProjectId) return []
  const ids = [selectedProjectId]
  if (selectedProjectId === project.value?.id) {
    ids.push(...subs.value.map((p) => p.id).filter(Boolean))
  }
  return Array.from(new Set(ids))
}

const subsFiltered = computed(() => {
  const term = subSearch.value.trim().toLowerCase()
  if (!term) return subs.value
  return subs.value.filter(s => s.name.toLowerCase().includes(term) || s.code.toLowerCase().includes(term))
})
const wpFiltered = computed(() => {
  const term = wpSearch.value.trim().toLowerCase()
  const allowedProjectIds = new Set(expandProjectFilterIds(wpProjectFilter.value))
  return workPackages.value.filter((w) => {
    if (wpProjectFilter.value && !allowedProjectIds.has(w.projectId)) return false
    if (!term) return true
    return w.name.toLowerCase().includes(term) || (w.code || '').toLowerCase().includes(term)
  })
})
const tasksFiltered = computed(() => {
  const term = taskSearch.value.trim().toLowerCase()
  const allowedProjectIds = new Set(expandProjectFilterIds(taskProjectFilter.value))
  return tasks.value.filter((t) => {
    if (taskProjectFilter.value && !allowedProjectIds.has(t.projectId)) return false
    if (!term) return true
    return t.name.toLowerCase().includes(term)
  })
})
const scosFiltered = computed(() => {
  const term = scoSearch.value.trim().toLowerCase()
  if (!term) return scos.value
  return scos.value.filter(s => s.title.toLowerCase().includes(term) || s.id.toLowerCase().includes(term))
})
const boqsFiltered = computed(() => {
  const term = boqSearch.value.trim().toLowerCase()
  if (!term) return boqs.value
  return boqs.value.filter(b => b.title.toLowerCase().includes(term) || b.id.toLowerCase().includes(term))
})

// Column defs for the inner lists.
const subCols = [
  { key: 'code',     label: 'ID' },
  { key: 'name',     label: 'Name' },
  { key: 'status',   label: 'Status' },
  { key: 'budget',   label: 'Budget',   align: 'right' },
  { key: 'progress', label: 'Progress', align: 'right' },
  { key: 'pm',       label: 'PM' },
]
const wpCols = [
  { key: 'code',     label: 'Code' },
  { key: 'name',     label: 'Name' },
  { key: 'status',   label: 'Status' },
  { key: 'budget',   label: 'Budget',   align: 'right' },
  { key: 'progress', label: 'Progress', align: 'right' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'owner',    label: 'Owner' },
]
const taskCols = [
  { key: 'name',     label: 'Task' },
  { key: 'project',  label: 'Project' },
  { key: 'status',   label: 'Status' },
  { key: 'priority', label: 'Priority' },
  // proposal §M2 — task_type Select (Activity / Milestone / Inspection)
  { key: 'task_type', label: 'Task Type' },
  { key: 'assignee', label: 'Assignee' },
  { key: 'endDate',  label: 'Due' },
  { key: 'progress', label: 'Progress', align: 'right' },
]
const boqCols = [
  { key: 'id',           label: 'ID' },
  { key: 'title',        label: 'Title' },
  { key: 'revision',     label: 'Rev.', align: 'center' },
  { key: 'status',       label: 'Status' },
  { key: 'sourceScoId',  label: 'Source SCO' },
  { key: 'planned',      label: 'Planned',  align: 'right' },
  { key: 'actual',       label: 'Actual',   align: 'right' },
  { key: 'preparedDate', label: 'Prepared' },
]
const scoCols = [
  { key: 'id',       label: 'ID' },
  { key: 'title',    label: 'Title' },
  { key: 'impact',   label: 'Impact', align: 'right' },
  { key: 'status',   label: 'Status' },
  { key: 'raisedBy', label: 'Raised by' },
]
const teamCols = [
  { key: 'member', label: 'Member' },
  { key: 'role',   label: 'Role' },
  { key: 'flag',   label: '' },
]

function onSubRowClick(row) { router.push(`/app/projects/${row.id}`) }
function onWpRowClick(row) { router.push(`/app/work-packages/${row.id}`) }
function onTaskRowClick(row) { router.push(`/app/tasks/${row.id}`) }
function onBoqRowClick(row) { router.push(`/app/boq/${row.id}`) }
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
        type="button"
        class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
        style="border-radius: 6px;"
        @click="startEdit"
      >Edit</button>
      <button
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
          class="px-3 py-2 text-xs font-medium whitespace-nowrap"
          :style="tab === t.id ? 'color:#16A34A; border-bottom: 2px solid #16A34A; margin-bottom: -1px;' : 'color: #475569; border-bottom: 2px solid transparent; margin-bottom: -1px;'"
          @click="tab = t.id"
        >{{ t.label }}<span v-if="t.count !== null" class="ml-1 text-ink-400 tabular-nums">({{ t.count }})</span></button>
      </div>

      <!-- ===== Tab content ===== -->

      <!-- Overview — view mode -->
      <div v-if="tab === 'overview'" class="pt-5">

        <!-- Summary strip — moved into Overview so it fills the page first.
             Slightly more generous than the old above-tabs version. -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          <!-- Client -->
          <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('building-2')" />
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Client</div>
            </div>
            <div class="text-sm text-ink-900 font-medium mt-1.5 truncate">{{ project.client || '—' }}</div>
          </div>

          <!-- Actual vs Planned -->
          <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('wallet')" />
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Actual vs Planned</div>
            </div>
            <div class="flex items-baseline gap-1 mt-1.5 tabular-nums">
              <span class="text-base font-semibold text-ink-900">{{ fmtCompactINR(actualCost) }}</span>
              <span class="text-xs text-ink-400">/ {{ fmtCompactINR(plannedCost) }}</span>
            </div>
            <div class="text-[11px] mt-1 tabular-nums" :class="deviationColor(costDeviationPct)">
              <span class="font-medium">{{ costDeviation > 0 ? '+' : '' }}{{ fmtCompactINR(Math.abs(costDeviation)) }}</span>
              <span class="ml-0.5">({{ costDeviationPct > 0 ? '+' : '' }}{{ costDeviationPct.toFixed(1) }}%)</span>
              <span class="text-ink-400 ml-0.5">{{ costDeviationPct > 0 ? 'over' : 'under' }}</span>
            </div>
          </div>

          <!-- Progress + delayed -->
          <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('chart-line')" />
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Progress</div>
            </div>
            <div class="flex items-center gap-2 mt-1.5">
              <div class="flex-1 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 999px;">
                <div class="h-full" :class="progressBarColor(project)" :style="`width:${project.progress}%`"></div>
              </div>
              <span class="text-sm text-ink-900 font-semibold tabular-nums">{{ project.progress }}%</span>
            </div>
            <div v-if="delayedDays > 0" class="text-[11px] text-danger-700 font-medium mt-1">
              Delayed by {{ delayedDays }}d
            </div>
            <div v-else-if="project.progress >= 100" class="text-[11px] text-success-700 font-medium mt-1">
              Completed
            </div>
            <div v-else class="text-[11px] text-success-700 font-medium mt-1">
              On track
            </div>
          </div>

          <!-- Timeline -->
          <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('calendar')" />
              <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Timeline</div>
            </div>
            <div class="text-xs text-ink-900 font-medium mt-1.5 tabular-nums">
              {{ fmtDate(project.startDate) }} → {{ fmtDate(project.endDate) }}
            </div>
            <div v-if="scheduleSummary" class="text-[11px] text-ink-500 mt-1 tabular-nums">
              {{ scheduleSummary.totalDays }}d total · {{ scheduleSummary.remainingDays }}d remaining
            </div>
          </div>
        </div>

        <!-- Two-column main / sidebar layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

          <!-- Main column (span 2) -->
          <div class="lg:col-span-2 space-y-4">

            <!-- About this project — gradient accent header + body -->
            <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
              <header class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2">
                <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('clipboard-list')" />
                <h3 class="text-sm font-semibold text-ink-900">About this project</h3>
              </header>
              <div class="p-5">
                <p class="text-sm text-ink-800 leading-relaxed whitespace-pre-wrap">{{ project.description || 'No description provided yet.' }}</p>
              </div>
            </section>

            <!-- Reports — project-context reports -->
            <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
              <header class="px-5 py-3 bg-gradient-to-r from-info-50 to-white border-b border-ink-100 flex items-center gap-2">
                <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('chart-line')" />
                <h3 class="text-sm font-semibold text-ink-900">Reports</h3>
              </header>
              <div class="p-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <RouterLink
                    v-for="rt in projectReports"
                    :key="rt.slug"
                    :to="`/app/reports/${rt.slug}`"
                    class="bg-white border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 p-3 transition-colors group block"
                    style="border-radius: 8px;"
                  >
                    <div class="flex items-start gap-2.5">
                      <svg class="w-5 h-5 text-ink-600 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath(rt.icon)" />
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-1.5 flex-wrap">
                          <div class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors">{{ rt.label }}</div>
                          <span class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider" style="border-radius: 2px;">Report</span>
                        </div>
                        <div class="text-[11px] text-ink-500 mt-0.5 leading-snug">{{ rt.desc }}</div>
                      </div>
                    </div>
                  </RouterLink>
                </div>
              </div>
            </section>
          </div>

          <!-- Sidebar (span 1) -->
          <div class="space-y-4">

            <!-- Project Manager card -->
            <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
              <header class="px-4 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2">
                <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('hr')" />
                <h3 class="text-sm font-semibold text-ink-900">Project Manager</h3>
              </header>
              <div class="p-4 flex items-center gap-3">
                <UserAvatar :user-id="project.pm" size="md" />
                <div class="min-w-0 flex-1">
                  <div class="text-sm font-semibold text-ink-900 truncate">{{ store.teamMember(project.pm)?.name || '—' }}</div>
                  <div class="text-[11px] text-ink-500 truncate">{{ store.teamMember(project.pm)?.role || '' }}</div>
                </div>
              </div>
            </section>

            <!-- Project metadata card -->
            <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
              <header class="px-4 py-3 bg-gradient-to-r from-ink-50 to-white border-b border-ink-100 flex items-center gap-2">
                <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('tag')" />
                <h3 class="text-sm font-semibold text-ink-900">Project details</h3>
                <button
                  type="button"
                  class="ml-auto text-[11px] text-brand-700 hover:text-brand-800 font-medium"
                  @click="startEdit"
                >Edit</button>
              </header>
              <dl class="divide-y divide-ink-100">
                <div class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Status</dt>
                  <dd><StatusBadge :status="project.status" /></dd>
                </div>
                <div class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Priority</dt>
                  <dd><StatusBadge :status="project.priority" /></dd>
                </div>
                <div class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Type</dt>
                  <dd class="text-ink-800">{{ project.type || '—' }}</dd>
                </div>
                <div v-if="store.isMultiCompany && project.company" class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Company</dt>
                  <dd class="flex items-center gap-1.5 text-ink-800 min-w-0">
                    <span
                      v-if="store.companyById(project.company)"
                      :class="store.companyById(project.company).color"
                      class="w-2 h-2 flex-shrink-0"
                      style="border-radius: 999px;"
                    ></span>
                    <span class="truncate">{{ store.companyById(project.company)?.shortName || project.company }}</span>
                  </dd>
                </div>
                <div class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Location</dt>
                  <dd class="text-ink-800 truncate ml-2">{{ project.location || '—' }}</dd>
                </div>
                <div class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Project ID</dt>
                  <dd class="text-ink-800 font-mono">{{ project.code }}</dd>
                </div>
                <div class="flex items-center justify-between px-4 py-2.5 text-xs">
                  <dt class="text-ink-500 font-medium">Created</dt>
                  <dd class="text-ink-700 tabular-nums">{{ fmtDate(project.createdAt) }}</dd>
                </div>
              </dl>
            </section>

          </div>
        </div>
      </div>

      <!-- Subprojects — hidden when this record is itself a subproject -->
      <div v-if="tab === 'subprojects' && subprojectsEnabled" class="pt-4">
        <DeskList
          v-model="subSearch"
          :rows="subsFiltered"
          :columns="subCols"
          row-key="id"
          search-placeholder="Search subprojects…"
          @row-click="onSubRowClick"
        >
          <template #actions>
            <button type="button" class="desk-save-btn" @click="addSubproject">+ New Subproject</button>
          </template>
          <template #cell-code="{ row }">
            <DeskLink :to="`/app/projects/${row.id}`" @click.stop class="font-mono text-xs">{{ row.code }}</DeskLink>
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
        <div class="text-xs text-ink-500 mb-2">
          {{ workPackages.length }} package{{ workPackages.length === 1 ? '' : 's' }} · avg progress
          <span class="text-ink-900 font-medium">{{ wpProgress }}%</span>
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
          <template #actions>
            <RouterLink
              :to="{ name: 'wp-new', query: { projectId: project.id } }"
              class="desk-save-btn"
            >+ Add Work Package</RouterLink>
          </template>
          <template #cell-code="{ row }">
            <DeskLink :to="`/app/work-packages/${row.id}`" @click.stop class="font-mono text-xs">{{ row.code }}</DeskLink>
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
        <div class="text-xs text-ink-500 mb-2">
          <span class="text-ink-900 font-medium">{{ taskStats.total }} tasks</span>
          · {{ taskStats.completed }} completed · {{ taskStats.inProgress }} in progress · {{ taskStats.open }} open
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
          <template #actions>
            <RouterLink
              :to="{ name: 'task-new', query: { projectId: project.id } }"
              class="desk-save-btn"
            >+ Add Task</RouterLink>
          </template>
          <template #cell-name="{ row }">
            <DeskLink :to="`/app/tasks/${row.id}`" @click.stop class="text-ink-900 hover:text-ink-900">{{ row.name }}</DeskLink>
          </template>
          <template #cell-project="{ row }">
            <DeskLink
              v-if="row.projectId"
              :to="`/app/projects/${row.projectId}`"
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

      <!-- Stage Planning — stages-as-structure list. Inside-the-table action
           button matches the DeskList chrome convention. -->
      <div v-if="tab === 'stage-planning'" class="pt-4">
        <div v-if="stages.length" class="bg-white border border-ink-200" style="border-radius: 8px;">
          <!-- Filter / action bar (matches DeskList) -->
          <div class="border-b border-ink-200 px-3 py-2 flex items-center gap-2 flex-wrap">
            <div class="text-xs text-ink-500">
              <span class="text-ink-900 font-medium">{{ stages.length }} {{ stages.length === 1 ? 'stage' : 'stages' }}</span>
              · ordered by planned start
            </div>
            <div class="ml-auto">
              <RouterLink :to="{ name: 'stage-planning-new', query: { projectId: project.id } }" class="desk-save-btn">+ Add Stage</RouterLink>
            </div>
          </div>
          <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
               style="grid-template-columns: minmax(220px, 1.4fr) 110px 110px 90px 110px 70px;">
            <div class="px-3 py-1.5">Stage</div>
            <div class="px-3 py-1.5">Planned Start</div>
            <div class="px-3 py-1.5">Planned End</div>
            <div class="px-3 py-1.5 text-right">Tasks</div>
            <div class="px-3 py-1.5">Status</div>
            <div class="px-3 py-1.5"></div>
          </div>
          <div
            v-for="s in stages"
            :key="s.id"
            class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 items-center text-sm cursor-pointer"
            style="grid-template-columns: minmax(220px, 1.4fr) 110px 110px 90px 110px 70px;"
            @click="router.push(`/app/stage-plannings/${s.id}`)"
          >
            <div class="px-3 py-2">
              <DeskLink :to="`/app/stage-plannings/${s.id}`" @click.stop class="font-medium">{{ s.stageName }}</DeskLink>
              <div v-if="s.description" class="text-[11px] text-ink-500 truncate">{{ s.description }}</div>
            </div>
            <div class="px-3 py-2 text-xs text-ink-700">{{ fmtDate(s.plannedStart) || '—' }}</div>
            <div class="px-3 py-2 text-xs text-ink-700">{{ fmtDate(s.plannedEnd) || '—' }}</div>
            <div class="px-3 py-2 text-right text-xs text-ink-700 tabular-nums">
              {{ (s.stagePlanningTasks || []).length }} / {{ s.plannedTaskCount || 0 }}
            </div>
            <div class="px-3 py-2">
              <span
                class="text-[10px] px-1.5 py-0.5 font-medium"
                style="border-radius: 2px;"
                :class="stageStatusClass(stageStatus(s))"
              >{{ stageStatus(s) }}</span>
            </div>
            <div class="px-3 py-2 text-right">
              <DeskLink :to="`/app/stage-plannings/${s.id}`" @click.stop class="text-xs">Open →</DeskLink>
            </div>
          </div>
        </div>
        <div v-else class="py-6">
          <div class="text-sm text-ink-500 italic mb-3">No stages planned yet.</div>
          <!-- §13.3 item 19 — Project Type template seed button. Only shows when a
               template exists for the project's type. Useful for projects created
               before the engine landed, or where the user unchecked "Seed default
               stages" on the create form and now wants to backfill. -->
          <div v-if="store.templateForProjectType(project.type)" class="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              class="desk-save-btn"
              @click="seedFromTemplate"
            >+ Seed from {{ project.type }} template</button>
            <RouterLink :to="{ name: 'stage-planning-new', query: { projectId: project.id } }" class="desk-link text-xs">
              or plan one manually →
            </RouterLink>
            <div class="basis-full text-[11px] text-ink-500 mt-1">
              Will seed {{ store.templateForProjectType(project.type).defaultStages.length }} stages — {{ store.templateForProjectType(project.type).defaultStages.map(s => s.stageName).join(' → ') }}.
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
      </div>

      <!-- BOQ -->
      <div v-if="tab === 'boq'" class="pt-4">
        <div class="text-xs text-ink-500 mb-2">
          {{ boqs.length }} BOQ revision{{ boqs.length === 1 ? '' : 's' }}
          <template v-if="activeBoq">
            · active: <DeskLink :to="`/app/boq/${activeBoq.id}`" class="font-mono">{{ activeBoq.id }}</DeskLink>
            ({{ fmtCompactINR(store.boqTotals(activeBoq.id).planned) }} planned · {{ fmtCompactINR(store.boqTotals(activeBoq.id).actual) }} actual)
          </template>
        </div>
        <DeskList
          v-model="boqSearch"
          :rows="boqsFiltered"
          :columns="boqCols"
          row-key="id"
          search-placeholder="Search BOQ revisions…"
          @row-click="onBoqRowClick"
        >
          <template #actions>
            <RouterLink to="/app/boq" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1 border border-ink-200 bg-white" style="border-radius: 2px;">Open BOQ module →</RouterLink>
          </template>
          <template #cell-id="{ row }">
            <DeskLink :to="`/app/boq/${row.id}`" @click.stop class="font-mono text-xs">{{ row.id }}</DeskLink>
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
              <RouterLink to="/app/boq" class="desk-link">Create one in the BOQ module →</RouterLink>
            </div>
          </template>
        </DeskList>
      </div>

      <!-- SCOs -->
      <div v-if="tab === 'scos'" class="pt-4">
        <DeskList
          v-model="scoSearch"
          :rows="scosFiltered"
          :columns="scoCols"
          row-key="id"
          search-placeholder="Search scope changes…"
        >
          <template #actions>
            <RouterLink to="/app/sco" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1 border border-ink-200 bg-white" style="border-radius: 2px;">Open SCO module →</RouterLink>
          </template>
          <template #cell-id="{ row }">
            <DeskLink to="/app/sco" class="font-mono text-xs">{{ row.id }}</DeskLink>
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

      <!-- Attachments — §13.3 items 13 + 26. Mirror of Frappe's native sidebar
           pattern: file rows + uploader avatar + delete + a single "+ Upload"
           CTA at the top right. NO inline preview, no folder structure — flat
           list, by design. Blob URLs are SESSION-ONLY (lost on tab close). -->
      <div v-if="tab === 'attachments'" class="pt-4">
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="onFilesPicked"
        />
        <div v-if="attachments.length" class="bg-white border border-ink-200" style="border-radius: 8px;">
          <!-- Filter / action bar -->
          <div class="border-b border-ink-200 px-3 py-2 flex items-center gap-2 flex-wrap">
            <div class="text-xs text-ink-500">
              <span class="text-ink-900 font-medium">{{ attachments.length }} {{ attachments.length === 1 ? 'file' : 'files' }}</span>
              · drawings, contracts, sanctioned plans, site documents
            </div>
            <div class="ml-auto">
              <button type="button" class="desk-save-btn" @click="openFilePicker">+ Upload</button>
            </div>
          </div>
          <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
               style="grid-template-columns: 28px minmax(220px, 2fr) 80px 110px 130px 32px;">
            <div></div>
            <div class="px-3 py-1.5">File</div>
            <div class="px-3 py-1.5 text-right">Size</div>
            <div class="px-3 py-1.5">Uploaded</div>
            <div class="px-3 py-1.5">By</div>
            <div></div>
          </div>
          <div
            v-for="att in attachments"
            :key="att.id"
            class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 items-center text-sm"
            style="grid-template-columns: 28px minmax(220px, 2fr) 80px 110px 130px 32px;"
          >
            <div class="px-2 py-2 text-center">
              <svg class="w-4 h-4 text-ink-500 mx-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath(fileIcon(att.mime))" />
            </div>
            <div class="px-3 py-2">
              <button
                type="button"
                class="text-left text-sm text-ink-900 hover:underline truncate w-full"
                :title="att.fileName"
                @click="openAttachment(att)"
              >{{ att.fileName }}</button>
              <div v-if="!att.url" class="text-[10px] text-ink-400 italic mt-0.5">metadata only</div>
            </div>
            <div class="px-3 py-2 text-right text-xs text-ink-600 tabular-nums">{{ formatFileSize(att.size) }}</div>
            <div class="px-3 py-2 text-xs text-ink-600">{{ fmtDate(att.uploadedAt) }}</div>
            <div class="px-3 py-2">
              <UserAvatar :user-id="att.uploadedBy" :show-name="true" size="xs" />
            </div>
            <div class="px-1 py-2 flex justify-center">
              <button
                type="button"
                class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-ink-50 text-danger-700"
                style="border-radius: 2px;"
                :title="`Delete ${att.fileName}`"
                @click="deleteAttachment(att)"
              >✕</button>
            </div>
          </div>
        </div>
        <div v-else class="py-8 text-center">
          <div class="text-sm text-ink-500 mb-2">No attachments yet.</div>
          <div class="text-xs text-ink-400 italic mb-4">Drawings, contracts, and site documents go here.</div>
          <button type="button" class="desk-save-btn" @click="openFilePicker">+ Upload first file</button>
        </div>
      </div>

      <!-- Team — project-scoped. PM is always shown first and cannot be
           removed (change PM via the Edit project modal). Other members are
           added / removed via the action button + the modal below. -->
      <div v-if="tab === 'team'" class="pt-4">
        <DeskList
          :rows="projectTeam"
          :columns="teamCols"
          row-key="id"
          :show-add-filter="false"
          :show-sort="false"
          :show-columns="false"
          :paginated="false"
        >
          <template #actions>
            <button
              type="button"
              class="desk-save-btn"
              :disabled="!availableTeamCandidates.length"
              @click="openTeamModal"
            >+ Add Member</button>
          </template>
          <template #cell-member="{ row }">
            <div class="flex items-center gap-2">
              <div :class="[row.color, 'w-6 h-6 rounded-full text-white flex items-center justify-center font-medium text-[10px]']">{{ row.initials }}</div>
              <span class="text-ink-900 text-sm">{{ row.name }}</span>
            </div>
          </template>
          <template #cell-role="{ row }">
            <span class="text-ink-700 text-sm">{{ row.role }}</span>
          </template>
          <template #cell-flag="{ row }">
            <div class="flex items-center justify-end gap-2">
              <span
                v-if="row.id === project.pm"
                class="text-[10px] font-medium px-1.5 py-0.5 bg-brand-50 text-brand-700"
                style="border-radius: 9999px;"
              >Project Manager</span>
              <button
                v-else
                type="button"
                class="text-xs px-2 py-0.5 border border-ink-200 bg-white hover:bg-danger-50 hover:border-danger-200 text-ink-500 hover:text-danger-700"
                style="border-radius: 6px;"
                :title="`Remove ${row.name} from this project`"
                @click.stop="removeTeamMember(row.id)"
              >Remove</button>
            </div>
          </template>
          <template #empty>
            <div class="text-sm text-ink-500">
              No team members yet.
              <button v-if="availableTeamCandidates.length" type="button" class="desk-link" @click="openTeamModal">Add the first one →</button>
            </div>
          </template>
        </DeskList>
      </div>

      <!-- Activity -->
      <div v-if="tab === 'activity'" class="pt-4">
        <div class="bg-white border border-ink-200 p-4" style="border-radius: 2px;">
          <div class="flex gap-3 text-sm">
            <UserAvatar :user-id="store.user?.id || 'USR-001'" size="sm" />
            <div>
              <div class="text-ink-700">Project created</div>
              <div class="text-xs text-ink-400 mt-0.5">{{ fmtDate(project.createdAt) }}</div>
            </div>
          </div>
        </div>
      </div>

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

    <!-- ===== Edit modal — opens via the title-row Edit button OR the
         Edit link inside the Overview's Project details card. The card is
         a flex column with header + footer pinned (flex-shrink-0) and the
         body as the only scrollable region. ===== -->
    <Teleport to="body">
      <div
        v-if="editing"
        class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
        @click.self="cancelEdit"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
          style="border-radius: 12px; max-height: calc(100vh - 3rem);"
          @click.stop
        >
          <!-- Modal header (pinned) -->
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900">Edit project</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ project.name }}</p>
            </div>
            <button
              type="button"
              class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
              aria-label="Close"
              @click="cancelEdit"
            >×</button>
          </header>

          <!-- Modal body — the only scrolling region -->
          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Basic information">
              <DeskField label="Project name" required>
                <DeskInput v-model="editForm.name" />
              </DeskField>
              <DeskField label="Client">
                <DeskLinkPicker
                  v-model="editForm.client"
                  doctype="Customer"
                  placeholder="Select customer"
                  label-field="customer_name"
                  value-field="name"
                  :search-fields="['customer_name', 'name']"
                  order-by="modified desc"
                  :page-length="20"
                />
              </DeskField>
              <DeskField label="Type">
                <DeskLinkPicker
                  v-model="editForm.type"
                  doctype="Project Type"
                  placeholder="Select project type"
                  label-field="name"
                  value-field="name"
                  :search-fields="['name']"
                  order-by="modified desc"
                  :page-length="20"
                />
              </DeskField>
              <DeskField
                v-if="store.isMultiCompany"
                label="Company"
                hint="Legal entity this project belongs to."
              >
                <DeskLinkPicker
                  v-model="editForm.company"
                  doctype="Company"
                  placeholder="Select company"
                  label-field="name"
                  value-field="name"
                  :search-fields="['name', 'abbr']"
                  order-by="modified desc"
                  :page-length="20"
                />
              </DeskField>
              <DeskField label="Location">
                <DeskInput v-model="editForm.location" />
              </DeskField>
              <DeskField label="Note">
                <DeskTextarea v-model="editForm.description" :rows="3" />
              </DeskField>
              <DeskField
                v-if="!isSubproject"
                label="Subprojects"
                :hint="subs.length > 0
                  ? `Locked on - this project has ${subs.length} subproject${subs.length === 1 ? '' : 's'}. Delete or move them out before turning this off.`
                  : 'Turn on to break this project into subprojects (e.g. Block A / Block B / Tower 1).'
                "
              >
                <label class="inline-flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    v-model="editForm.isGroup"
                    :disabled="subs.length > 0"
                    class="accent-brand-600 disabled:cursor-not-allowed"
                  />
                  <span class="text-sm text-ink-700">Allow subprojects under this project</span>
                </label>
              </DeskField>
            </DeskSection>

            <DeskSection title="Schedule & cost">
              <DeskField label="Start date">
                <DeskInput v-model="editForm.startDate" type="date" />
              </DeskField>
              <DeskField label="End date">
                <DeskInput v-model="editForm.endDate" type="date" />
              </DeskField>
              <DeskField label="Budget" hint="In INR">
                <DeskInput v-model="editForm.budget" type="number" />
              </DeskField>
              <DeskField label="Progress" hint="0–100">
                <DeskInput v-model="editForm.progress" type="number" />
              </DeskField>
            </DeskSection>

            <DeskSection title="Team & status">
              <DeskField label="Project Manager">
                <DeskLinkPicker
                  v-model="editForm.pm"
                  doctype="Employee"
                  placeholder="Select project manager"
                  label-field="employee_name"
                  value-field="name"
                  :search-fields="['employee_name', 'name', 'company_email', 'user_id']"
                  order-by="modified desc"
                  :page-length="20"
                />
              </DeskField>
              <DeskField label="Status">
                <DeskSelect v-model="editForm.status">
                  <option>Open</option>
                  <option>Working</option>
                  <option>On Hold</option>
                  <option>Completed</option>
                  <option>Cancelled</option>
                </DeskSelect>
              </DeskField>
              <DeskField label="Priority">
                <DeskSelect v-model="editForm.priority">
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                </DeskSelect>
              </DeskField>
            </DeskSection>
          </div>

          <!-- Modal footer (pinned) -->
          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
            <button
              type="button"
              class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
              style="border-radius: 6px;"
              @click="cancelEdit"
            >Cancel</button>
            <button
              type="button"
              class="desk-save-btn"
              @click="saveEdit"
            >Save</button>
          </footer>
        </div>
      </div>
    </Teleport>

    <!-- Add Team Member modal -->
    <Teleport to="body">
      <div
        v-if="teamModalOpen"
        class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
        @click.self="closeTeamModal"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-md shadow-fp-lg flex flex-col"
          style="border-radius: 12px;"
          @click.stop
        >
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900">Add team member</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ project.name }}</p>
            </div>
            <button
              type="button"
              class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
              aria-label="Close"
              @click="closeTeamModal"
            >×</button>
          </header>
          <div class="p-5">
            <div v-if="availableTeamCandidates.length">
              <DeskField label="User" hint="Pick from users not already on this project.">
                <DeskSelect v-model="teamPickUserId">
                  <option v-for="m in availableTeamCandidates" :key="m.id" :value="m.id">{{ m.name }} — {{ m.role }}</option>
                </DeskSelect>
              </DeskField>
            </div>
            <div v-else class="text-sm text-ink-500 italic">
              Every user is already on this project.
            </div>
          </div>
          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
            <button
              type="button"
              class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
              style="border-radius: 6px;"
              @click="closeTeamModal"
            >Cancel</button>
            <button
              type="button"
              class="desk-save-btn"
              :disabled="!teamPickUserId"
              @click="confirmAddMember"
            >Add member</button>
          </footer>
        </div>
      </div>
    </Teleport>

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
    <RouterLink to="/app/projects" class="desk-link text-sm">Back to projects</RouterLink>
  </div>
</template>
