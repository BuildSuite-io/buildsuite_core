<script setup>
// Stage Review — per-stage meeting dashboard. Vue-styled composite (like the
// Project Dashboard), rendered inside DeskShell. Adapter-backed; reads the
// stage (+ its task rows and delay log), the linked tasks' live progress, and
// Task Progress Entries inside the stage window for the labour rollup.
//
// Materials (planned vs actual) and the activity feed from the prototype are
// intentionally omitted: BOQ doctypes don't exist yet (Milestone 2) and there
// is no backend stage-activity log.

import { ref, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import StatusBadge from '@/components/StatusBadge.vue'
import FrappeUserBadge from '@/components/FrappeUserBadge.vue'
import StageDelayReasonModal from '@/components/StageDelayReasonModal.vue'
import { fmtDate } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()
const adapter = createDataAdapter(store)

const TODAY = new Date().toISOString().slice(0, 10)

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

function mapStageRow(row) {
  if (!row) return null
  return {
    id: row.name || '',
    stageName: row.stage_name || '',
    project: row.project || '',
    workflowState: row.workflow_state || 'Draft',
    plannedStart: row.planned_start || null,
    plannedEnd: row.planned_end || null,
    stagePlanningTasks: (row.stage_planning_tasks || []).map((r, idx) => ({
      id: r?.name || `row-${idx}`,
      task: r?.task || '',
      plannedStart: r?.planned_start || null,
      plannedEnd: r?.planned_end || null,
      plannedQty: Number(r?.planned_qty ?? 100),
    })),
    delayReasons: (row.delay_reasons || []).map((r) => ({
      id: r?.name || '',
      reason: r?.reason || '',
      responsibleParty: r?.responsible_party || '',
      daysDelayed: (r?.days_delayed === null || r?.days_delayed === undefined || r?.days_delayed === '') ? null : Number(r.days_delayed),
      note: r?.note || '',
      loggedBy: r?.logged_by || '',
      loggedOn: r?.logged_on || '',
    })),
  }
}

// ----- Stage -----
const stageResource = ref(null)
function loadStage() {
  if (!props.id) { stageResource.value = null; return }
  stageResource.value = adapter.read('Stage Planning', props.id, {
    fields: [
      'name', 'stage_name', 'project', 'workflow_state',
      'planned_start', 'planned_end', 'stage_planning_tasks', 'delay_reasons',
    ],
    cache: `buildsuite-stage-review:${props.id}`,
    transform(rows) { return rows.map(mapStageRow) },
  })
}
watch(() => props.id, loadStage, { immediate: true })
const stage = computed(() => firstResourceRow(stageResource.value))

// ----- Project -----
const projectResource = ref(null)
watch(() => stage.value?.project, (projectId) => {
  if (!projectId) { projectResource.value = null; return }
  projectResource.value = adapter.read('Project', projectId, {
    fields: ['name', 'project_name'],
    cache: `buildsuite-stage-review-project:${projectId}`,
    transform(rows) { return rows.map((r) => ({ id: r?.name || '', name: r?.project_name || r?.name || '' })) },
  })
}, { immediate: true })
const project = computed(() => firstResourceRow(projectResource.value))

// ----- Tasks (live progress/status) -----
const tasksResource = ref(null)
watch(() => stage.value?.project, (projectId) => {
  if (!projectId) { tasksResource.value = null; return }
  tasksResource.value = adapter.list('Task', {
    fields: ['name', 'subject', 'status', 'progress'],
    filters: [['project', '=', projectId]],
    pageLength: 500,
    cache: `buildsuite-stage-review-tasks:${projectId}`,
    transform(rows) {
      return rows.map((r) => ({
        id: r?.name || '',
        name: r?.subject || r?.name || '',
        status: r?.status || 'Yet To Start',
        progress: Number(r?.progress) || 0,
      }))
    },
  })
}, { immediate: true })
const tasksById = computed(() => {
  const map = {}
  for (const t of resourceRows(tasksResource.value)) map[t.id] = t
  return map
})

// ----- Task Progress Entries (labour, within window) -----
const stageTaskIds = computed(() => (stage.value?.stagePlanningTasks || []).map((r) => r.task).filter(Boolean))
const progressEntriesResource = ref(null)
watch(() => stageTaskIds.value.join(','), (joined) => {
  const ids = joined ? joined.split(',') : []
  if (!ids.length) { progressEntriesResource.value = null; return }
  progressEntriesResource.value = adapter.list('Task Progress Entry', {
    fields: ['task', 'entry_date', 'skilled', 'unskilled'],
    filters: [['task', 'in', ids]],
    pageLength: 1000,
    cache: `buildsuite-stage-review-tpe:${props.id}`,
    transform(rows) {
      return rows.map((r) => ({
        task: r?.task || '',
        entryDate: r?.entry_date || '',
        skilled: Number(r?.skilled) || 0,
        unskilled: Number(r?.unskilled) || 0,
      }))
    },
  })
}, { immediate: true })

// ============================================================
// COMPUTEDS
// ============================================================
const rows = computed(() => stage.value?.stagePlanningTasks || [])
const taskRecords = computed(() => rows.value.map((r) => ({ row: r, task: tasksById.value[r.task] || null })))
const taskCount = computed(() => rows.value.length)
const completedTaskCount = computed(() => taskRecords.value.filter((tr) => tr.task && tr.task.progress >= 100).length)
const inProgressTaskCount = computed(() => taskRecords.value.filter((tr) => tr.task && tr.task.progress > 0 && tr.task.progress < 100).length)

const meanActualProgress = computed(() => {
  if (!rows.value.length) return 0
  const sum = taskRecords.value.reduce((acc, tr) => acc + (tr.task ? tr.task.progress : 0), 0)
  return Math.round(sum / rows.value.length)
})
const meanPlannedProgress = computed(() => {
  if (!rows.value.length) return 0
  const sum = rows.value.reduce((acc, r) => acc + (r.plannedQty ?? 100), 0)
  return Math.round(sum / rows.value.length)
})
function rowPlannedActualVariance(tr) {
  const planned = tr.row.plannedQty ?? 100
  const actual = tr.task ? tr.task.progress : 0
  return actual - planned
}
const expectedProgress = computed(() => {
  const s = stage.value
  if (!s?.plannedStart || !s?.plannedEnd) return null
  const total = (new Date(s.plannedEnd) - new Date(s.plannedStart)) / 86400000
  if (total <= 0) return 0
  const elapsed = (new Date(TODAY) - new Date(s.plannedStart)) / 86400000
  return Math.max(0, Math.min(100, Math.round((elapsed / total) * 100)))
})
const plannedVsActualPts = computed(() => meanActualProgress.value - meanPlannedProgress.value)
const daysOverrun = computed(() => {
  const s = stage.value
  if (!s?.plannedEnd || s.plannedEnd >= TODAY) return 0
  return Math.ceil((new Date(TODAY) - new Date(s.plannedEnd)) / 86400000)
})

// isStageDelayed (frontend-derived): (a) calendar overrun with unfinished work,
// or (b) calendar-expected beats actual by > 15 pts inside the window.
const isDelayed = computed(() => {
  const s = stage.value
  if (!s) return false
  if (s.plannedEnd && s.plannedEnd < TODAY && meanActualProgress.value < 100) return true
  if (expectedProgress.value !== null && expectedProgress.value > 0 && (expectedProgress.value - meanActualProgress.value) > 15) return true
  return false
})

// Labour from progress entries inside the stage window.
const labourTotals = computed(() => {
  const s = stage.value
  const start = s?.plannedStart || ''
  const end = s?.plannedEnd || ''
  let skilled = 0, unskilled = 0, entries = 0
  for (const e of resourceRows(progressEntriesResource.value)) {
    if (start && e.entryDate < start) continue
    if (end && e.entryDate > end) continue
    skilled += e.skilled
    unskilled += e.unskilled
    entries++
  }
  return { skilled, unskilled, total: skilled + unskilled, entries }
})

// Delay reasons (latest first).
const delayReasons = computed(() => (stage.value?.delayReasons || []).slice().reverse())
const delayDaysSummary = computed(() => {
  let total = 0, pending = 0
  for (const d of delayReasons.value) {
    if (d.daysDelayed === null || d.daysDelayed === undefined) pending++
    else total += Number(d.daysDelayed) || 0
  }
  return { total, pending, count: delayReasons.value.length }
})
function partyPill(party) {
  switch (party) {
    case 'Own': return 'bg-brand-50 text-brand-700'
    case 'Subcontractor': return 'bg-info-50 text-info-700'
    case 'Client': return 'bg-warning-50 text-warning-700'
    case 'External': return 'bg-ink-100 text-ink-700'
    case 'Consultant': return 'bg-success-50 text-success-700'
    default: return 'bg-ink-100 text-ink-600'
  }
}

// ----- Delay modal -----
const delayModalOpen = ref(false)
function openDelayModal() { delayModalOpen.value = true }
function onDelaySaved() { stageResource.value?.reload?.() }

function goBack() {
  if (stage.value) router.push(`/stage-plannings/${stage.value.id}`)
  else router.push('/stage-plannings')
}
</script>

<template>
  <div v-if="stage" class="px-6 py-6 max-w-6xl mx-auto">
    <!-- Breadcrumb -->
    <nav class="text-xs text-ink-500 mb-3 flex items-center gap-1.5 flex-wrap">
      <RouterLink to="/" class="hover:text-ink-700">BuildSuite Core</RouterLink>
      <span>›</span>
      <RouterLink to="/stage-plannings" class="hover:text-ink-700">Stage Planning</RouterLink>
      <span>›</span>
      <RouterLink v-if="project" :to="`/projects/${project.id}`" class="hover:text-ink-700">{{ project.name }}</RouterLink>
      <span v-if="project">›</span>
      <RouterLink :to="`/stage-plannings/${stage.id}`" class="hover:text-ink-700">{{ stage.stageName }}</RouterLink>
      <span>›</span>
      <span class="text-ink-700 dark:text-ink-300">Review</span>
    </nav>

    <!-- Header -->
    <div class="flex items-start justify-between gap-4 mb-6">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <h1 class="text-2xl font-semibold text-ink-900 truncate dark:text-[#F5F5F5]">{{ stage.stageName }}</h1>
          <StatusBadge :status="stage.workflowState" />
          <span v-if="isDelayed" class="text-[11px] px-2 py-0.5 rounded-full bg-danger-50 text-danger-700 font-medium">Delayed</span>
        </div>
        <p class="text-xs text-ink-500 mt-1">
          Stage Review · {{ project?.name || stage.project }}
          <template v-if="stage.plannedStart && stage.plannedEnd"> · {{ fmtDate(stage.plannedStart) }} → {{ fmtDate(stage.plannedEnd) }}</template>
        </p>
      </div>
      <button
        type="button"
        class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 flex-shrink-0 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
        style="border-radius: 6px;"
        @click="goBack"
      >← Back to stage</button>
    </div>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Tasks</div>
        <div class="text-2xl font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">{{ taskCount }}</div>
        <div class="text-[11px] text-ink-500 mt-0.5">{{ completedTaskCount }} done · {{ inProgressTaskCount }} in progress</div>
      </div>
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Task progress</div>
        <div class="flex items-baseline gap-2 mt-1">
          <span class="text-2xl font-semibold text-ink-900 tabular-nums dark:text-[#F5F5F5]">{{ meanActualProgress }}%</span>
          <span class="text-sm text-ink-500 tabular-nums">/ {{ meanPlannedProgress }}% planned</span>
        </div>
        <div class="text-[11px] mt-0.5 flex items-center gap-1 flex-wrap">
          <span v-if="plannedVsActualPts !== 0" :class="plannedVsActualPts > 0 ? 'text-success-700' : 'text-danger-700'" class="font-medium">{{ plannedVsActualPts > 0 ? '+' : '' }}{{ plannedVsActualPts }} pts vs plan</span>
          <span v-else class="text-ink-500">on plan</span>
          <span v-if="expectedProgress !== null" class="text-ink-400">· expected {{ expectedProgress }}% by calendar</span>
        </div>
      </div>
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Labour deployed</div>
        <div class="text-2xl font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">{{ labourTotals.total }}</div>
        <div class="text-[11px] text-ink-500 mt-0.5">{{ labourTotals.skilled }} skilled · {{ labourTotals.unskilled }} unskilled</div>
      </div>
      <div class="bg-white border border-ink-200 px-4 py-3 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 8px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Schedule</div>
        <div v-if="daysOverrun > 0" class="text-2xl font-semibold text-danger-700 mt-1 tabular-nums">{{ daysOverrun }}d over</div>
        <div v-else-if="expectedProgress !== null && expectedProgress < 100" class="text-2xl font-semibold text-success-700 mt-1">On window</div>
        <div v-else class="text-2xl font-semibold text-ink-900 mt-1 dark:text-[#F5F5F5]">Ended</div>
        <div v-if="stage.plannedEnd" class="text-[11px] text-ink-500 mt-0.5">Planned end {{ fmtDate(stage.plannedEnd) }}</div>
      </div>
    </div>

    <!-- Task progress (full width) -->
    <section class="bg-white border border-ink-200 overflow-hidden mb-6 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 12px;">
      <header class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2 dark:from-brand-950/30 dark:to-[#242424] dark:border-ink-700">
        <svg class="w-4 h-4 text-brand-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('clipboard-list')" />
        <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">Task progress</h2>
        <span class="text-[10px] text-ink-500 ml-3 flex items-center gap-2">
          <span class="flex items-center gap-1"><span class="inline-block w-3 h-1.5 bg-info-500" style="border-radius: 1px;"></span>actual</span>
          <span class="flex items-center gap-1"><span class="inline-block w-[2px] h-2.5 stage-progress-tick"></span>planned</span>
        </span>
        <span class="text-[11px] text-ink-500 ml-auto">{{ taskCount }} task{{ taskCount === 1 ? '' : 's' }} in stage</span>
      </header>

      <div
        v-if="rows.length"
        class="px-5 py-2 bg-ink-50 border-b border-ink-100 grid items-center gap-4 text-[10px] uppercase tracking-wider text-ink-500 font-medium dark:bg-ink-800 dark:border-ink-700"
        style="grid-template-columns: minmax(280px, 1fr) 200px 130px 80px 110px;"
      >
        <div>Task</div>
        <div>Progress (actual / planned)</div>
        <div class="text-right">% vs plan</div>
        <div class="text-center">Variance</div>
        <div>Status</div>
      </div>

      <div v-if="rows.length" class="divide-y divide-ink-100 dark:divide-ink-700">
        <div
          v-for="tr in taskRecords"
          :key="tr.row.id"
          class="px-5 py-3 grid items-center gap-4"
          style="grid-template-columns: minmax(280px, 1fr) 200px 130px 80px 110px;"
        >
          <div class="min-w-0">
            <RouterLink v-if="tr.task" :to="`/tasks/${tr.row.task}`" class="text-sm text-ink-900 font-medium hover:underline truncate block dark:text-[#F5F5F5]">{{ tr.task.name }}</RouterLink>
            <span v-else class="text-sm text-ink-400 italic">No task linked</span>
            <div v-if="tr.task" class="text-[11px] text-ink-500 mt-0.5 truncate">{{ fmtDate(tr.row.plannedStart) || '—' }} → {{ fmtDate(tr.row.plannedEnd) || '—' }}</div>
          </div>

          <div class="relative w-full h-2 bg-ink-100 overflow-hidden dark:bg-ink-700" style="border-radius: 2px;">
            <div
              class="absolute inset-y-0 left-0"
              :class="(tr.task?.progress || 0) >= 100 ? 'bg-success-500' : (tr.task?.progress || 0) > 0 ? 'bg-info-500' : 'bg-ink-300'"
              :style="`width:${tr.task?.progress || 0}%`"
            ></div>
            <div
              v-if="tr.task"
              class="absolute inset-y-0 w-[2px] stage-progress-tick"
              :style="`left:calc(${tr.row.plannedQty ?? 100}% - 1px)`"
              :title="`Planned: ${tr.row.plannedQty ?? 100}%`"
            ></div>
          </div>

          <div class="text-xs tabular-nums text-right whitespace-nowrap" :title="`Actual ${tr.task?.progress || 0}% · Planned ${tr.row.plannedQty ?? 100}%`">
            <span class="text-ink-900 font-medium dark:text-[#F5F5F5]">{{ tr.task?.progress || 0 }}%</span><span class="text-ink-400"> / {{ tr.row.plannedQty ?? 100 }}%</span>
          </div>

          <div class="flex justify-center">
            <span
              v-if="tr.task && rowPlannedActualVariance(tr) !== 0"
              :class="rowPlannedActualVariance(tr) >= 0 ? 'bg-success-50 text-success-700' : 'bg-danger-50 text-danger-700'"
              class="text-[10px] px-1.5 py-0.5 rounded-full font-medium tabular-nums whitespace-nowrap"
            >{{ rowPlannedActualVariance(tr) > 0 ? '+' : '' }}{{ rowPlannedActualVariance(tr) }} pts</span>
            <span v-else class="text-[10px] text-ink-400">—</span>
          </div>

          <div>
            <StatusBadge v-if="tr.task" :status="tr.task.status" size="xs" />
            <span v-else class="text-[10px] text-ink-400">—</span>
          </div>
        </div>
      </div>
      <div v-else class="px-5 py-8 text-center text-sm text-ink-400 italic">No tasks linked to this stage yet.</div>
    </section>

    <!-- Delay reasons (full width) -->
    <section class="bg-white border border-ink-200 overflow-hidden mb-6 dark:bg-[#242424] dark:border-ink-700" style="border-radius: 12px;">
      <header class="px-5 py-3 bg-gradient-to-r from-warning-50 to-white border-b border-ink-100 flex items-center gap-2 dark:from-warning-950/30 dark:to-[#242424] dark:border-ink-700">
        <svg class="w-4 h-4 text-warning-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('refresh-ccw')" />
        <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">Delay reasons</h2>
        <span v-if="delayReasons.length" class="text-[11px] text-ink-500 ml-3">
          <span class="font-semibold text-ink-900 tabular-nums dark:text-[#F5F5F5]">{{ delayDaysSummary.total }}</span>
          day{{ delayDaysSummary.total === 1 ? '' : 's' }} total
          <span v-if="delayDaysSummary.pending > 0" class="text-ink-400">· {{ delayDaysSummary.pending }} TBD</span>
        </span>
        <button
          type="button"
          class="ml-auto text-[11px] px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
          style="border-radius: 6px;"
          @click="openDelayModal"
        >+ Add</button>
      </header>

      <div
        v-if="delayReasons.length"
        class="px-5 py-2 bg-ink-50 border-b border-ink-100 grid items-center gap-4 text-[10px] uppercase tracking-wider text-ink-500 font-medium dark:bg-ink-800 dark:border-ink-700"
        style="grid-template-columns: 32px minmax(240px, 1fr) 130px 80px minmax(160px, 1.2fr) 150px;"
      >
        <div class="text-right">#</div>
        <div>Reason</div>
        <div>Responsible</div>
        <div class="text-center">Days</div>
        <div>Notes</div>
        <div>Logged</div>
      </div>

      <div v-if="delayReasons.length" class="divide-y divide-ink-100 dark:divide-ink-700">
        <div
          v-for="(d, i) in delayReasons"
          :key="d.id || i"
          class="px-5 py-3 grid items-start gap-4 text-sm"
          style="grid-template-columns: 32px minmax(240px, 1fr) 130px 80px minmax(160px, 1.2fr) 150px;"
        >
          <div class="text-right text-ink-400 tabular-nums">{{ delayReasons.length - i }}</div>
          <div class="text-ink-900 font-medium dark:text-[#F5F5F5]">{{ d.reason }}</div>
          <div>
            <span v-if="d.responsibleParty" class="text-[10px] px-1.5 py-0.5 rounded-full font-medium" :class="partyPill(d.responsibleParty)">{{ d.responsibleParty }}</span>
            <span v-else class="text-[10px] text-ink-400">—</span>
          </div>
          <div class="text-center">
            <span v-if="d.daysDelayed !== null" class="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-danger-50 text-danger-700 tabular-nums">{{ d.daysDelayed }}d</span>
            <span v-else class="text-[10px] text-ink-400 italic">TBD</span>
          </div>
          <div class="text-xs text-ink-600 whitespace-pre-line leading-snug dark:text-ink-300">{{ d.note || '—' }}</div>
          <div class="text-[11px] text-ink-500">
            <FrappeUserBadge v-if="d.loggedBy" :user-id="d.loggedBy" />
            <div class="mt-0.5">{{ fmtDate(d.loggedOn) || '—' }}</div>
          </div>
        </div>
      </div>
      <div v-else class="px-5 py-8 text-center text-sm text-ink-400 italic">
        No delay reasons logged. Use <span class="font-medium">+ Add</span> to record one.
      </div>
    </section>

    <!-- Labour movement -->
    <section class="bg-white border border-ink-200 overflow-hidden dark:bg-[#242424] dark:border-ink-700" style="border-radius: 12px;">
      <header class="px-5 py-3 bg-gradient-to-r from-success-50 to-white border-b border-ink-100 flex items-center gap-2 dark:from-success-950/30 dark:to-[#242424] dark:border-ink-700">
        <svg class="w-4 h-4 text-success-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('hard-hat')" />
        <h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">Labour movement</h2>
        <span class="text-[11px] text-ink-500 ml-auto">{{ labourTotals.entries }} progress {{ labourTotals.entries === 1 ? 'entry' : 'entries' }} in window</span>
      </header>
      <div class="p-5 grid grid-cols-3 gap-4">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Skilled</div>
          <div class="text-xl font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">{{ labourTotals.skilled }}</div>
          <div class="text-[11px] text-ink-500 mt-0.5">man-days</div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Unskilled</div>
          <div class="text-xl font-semibold text-ink-900 mt-1 tabular-nums dark:text-[#F5F5F5]">{{ labourTotals.unskilled }}</div>
          <div class="text-[11px] text-ink-500 mt-0.5">man-days</div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total</div>
          <div class="text-xl font-semibold text-brand-700 mt-1 tabular-nums">{{ labourTotals.total }}</div>
          <div class="text-[11px] text-ink-500 mt-0.5">man-days deployed</div>
        </div>
      </div>
    </section>

    <StageDelayReasonModal
      v-model:open="delayModalOpen"
      :stage-id="stage.id"
      :stage-name="stage.stageName"
      :is-gate="false"
      @saved="onDelaySaved"
    />
  </div>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">
    Stage not found ·
    <RouterLink to="/stage-plannings" class="desk-link">Back to list →</RouterLink>
  </div>
</template>
