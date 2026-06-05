<script setup>
// Stage Planning — detail/edit. Desk-styled (CLAUDE.md §12.4). Three sections:
// Stage details · Dependencies · Tasks in this stage (child table). NO Stage
// Review aggregation — see §13.3 item 18 + the marker comment near the bottom
// of the template for where that surface will attach in M3+.

import { ref, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtDate } from '@/utils/format'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()

const stage = computed(() => store.stagePlanningById(props.id))
const project = computed(() => stage.value ? store.projectById(stage.value.project) : null)

const editing = ref(false)
const form = ref({})

// Deep clone so cancel reverts cleanly without mutating the store record. The
// child table (stagePlanningTasks) needs the clone too — otherwise inline edits
// would write through immediately.
watch(stage, (s) => { if (s) form.value = JSON.parse(JSON.stringify(s)) }, { immediate: true })

function startEdit() {
  form.value = JSON.parse(JSON.stringify(stage.value))
  editing.value = true
}
function cancelEdit() {
  form.value = JSON.parse(JSON.stringify(stage.value))
  editing.value = false
}
function saveEdit() {
  // Strip blank child rows (no task linked AND no qty) — they're scaffolding the
  // user added but never filled.
  const cleanRows = (form.value.stagePlanningTasks || []).filter(r => r && (r.task || r.plannedQty || r.plannedStart || r.plannedEnd))
  // Project is locked once created — never patch it from the form here.
  store.updateStagePlanning(props.id, {
    stageName:            form.value.stageName,
    plannedStart:         form.value.plannedStart,
    plannedEnd:           form.value.plannedEnd,
    plannedTaskCount:     form.value.plannedTaskCount,
    plannedCompletionPct: form.value.plannedCompletionPct,
    description:          form.value.description,
    dependencies:         form.value.dependencies || [],
    stagePlanningTasks:   cleanRows,
  })
  editing.value = false
}
function onPrimary() { editing.value ? saveEdit() : startEdit() }

// Sibling stages = other stages on the same project, eligible for the
// dependencies multi-select. Excludes the current stage (no self-dependency).
const siblingStages = computed(() => {
  if (!stage.value) return []
  return store.stagePlannings.filter(sp =>
    sp.project === stage.value.project && sp.id !== stage.value.id
  )
})

function toggleDependency(depId) {
  const list = form.value.dependencies || []
  const i = list.indexOf(depId)
  if (i === -1) list.push(depId)
  else list.splice(i, 1)
  form.value.dependencies = list
}

// Child-table operations. In edit mode we mutate the form's local stagePlanningTasks
// array; saveEdit pushes the whole array via updateStagePlanning. In view mode the
// "+ Add row" / Remove buttons aren't shown.
function addChildRow() {
  if (!Array.isArray(form.value.stagePlanningTasks)) form.value.stagePlanningTasks = []
  // Cheap unique-ish id for the new row; the store will issue a proper SPT-… id
  // on save via updateStagePlanning -> ... wait, no — we keep the row's id since
  // bulk update doesn't re-mint. Mint here.
  const id = 'SPT-' + Date.now().toString().slice(-6) + '-' + Math.floor(Math.random() * 1000)
  form.value.stagePlanningTasks.push({
    id, task: null, plannedStart: '', plannedEnd: '', plannedQty: 0, qtyUnit: '',
  })
}
function removeChildRow(rowId) {
  form.value.stagePlanningTasks = (form.value.stagePlanningTasks || []).filter(r => r.id !== rowId)
}

// Project-scoped task list for the child-table Task select. Includes tasks on
// the project AND any of its subprojects so a parent-project stage can plan
// against subproject tasks (the store mirrors this via tasksByProject).
const tasksForProject = computed(() => stage.value ? store.tasksByProject(stage.value.project) : [])
function taskName(id) { return store.taskById(id)?.name || id }
function taskStatus(id) { return store.taskById(id)?.status || '—' }

function deleteStage() {
  if (!confirm(`Delete stage "${stage.value.stageName}"?\n\nDependencies in other stages pointing at this one will be cleaned up automatically.`)) return
  store.deleteStagePlanning(props.id)
  if (project.value) router.push(`/projects/${project.value.id}`)
  else router.push('/stage-plannings')
}

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
    :breadcrumbs="breadcrumbs"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          :save-label="editing ? 'Save' : 'Edit'"
          :show-cancel="editing"
          cancel-label="Cancel"
          @save="onPrimary"
          @cancel="cancelEdit"
        >
          <template #left>
            <span class="text-[11px] text-ink-500">
              {{ (stage.stagePlanningTasks || []).length }} of {{ stage.plannedTaskCount || 0 }} planned tasks
            </span>
          </template>
          <template #menu>
            <button
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px; color: #B91C1C;"
              @click="deleteStage"
            >Delete</button>
          </template>
        </DeskActionBar>
      </template>

      <!-- Stage details -->
      <DeskSection title="Stage details" v-if="!editing">
        <DeskField label="Stage name">
          <div class="text-sm text-ink-900 py-1">{{ stage.stageName }}</div>
        </DeskField>
        <DeskField label="Project">
          <div class="text-sm py-1">
            <DeskLink v-if="project" :to="`/projects/${project.id}`">{{ project.name }}</DeskLink>
            <span v-else class="text-ink-500">{{ stage.project }}</span>
          </div>
        </DeskField>
        <DeskField label="Planned start">
          <div class="text-sm text-ink-900 py-1">{{ fmtDate(stage.plannedStart) || '—' }}</div>
        </DeskField>
        <DeskField label="Planned end">
          <div class="text-sm text-ink-900 py-1">{{ fmtDate(stage.plannedEnd) || '—' }}</div>
        </DeskField>
        <DeskField label="Planned task count">
          <div class="text-sm text-ink-900 py-1 tabular-nums">{{ stage.plannedTaskCount || 0 }}</div>
        </DeskField>
        <DeskField label="Planned completion %">
          <div class="text-sm text-ink-900 py-1 tabular-nums">{{ stage.plannedCompletionPct || 0 }}%</div>
        </DeskField>
        <DeskField label="Description">
          <div class="text-sm text-ink-700 py-1 whitespace-pre-line">{{ stage.description || '—' }}</div>
        </DeskField>
      </DeskSection>
      <DeskSection title="Stage details" v-else>
        <DeskField label="Stage name" required>
          <DeskInput v-model="form.stageName" />
        </DeskField>
        <DeskField label="Project" hint="Locked after create — move tasks instead of reparenting a stage.">
          <DeskInput :model-value="project ? project.name : form.project" disabled />
        </DeskField>
        <DeskField label="Planned start">
          <DeskInput v-model="form.plannedStart" type="date" />
        </DeskField>
        <DeskField label="Planned end">
          <DeskInput v-model="form.plannedEnd" type="date" />
        </DeskField>
        <DeskField label="Planned task count" hint="Headline planned count — child rows are the breakdown.">
          <DeskInput v-model="form.plannedTaskCount" type="number" min="0" />
        </DeskField>
        <DeskField label="Planned completion %">
          <DeskInput v-model="form.plannedCompletionPct" type="number" min="0" max="100" />
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" />
        </DeskField>
      </DeskSection>

      <!-- Dependencies -->
      <DeskSection title="Dependencies">
        <div class="md:col-span-2">
          <div v-if="!editing">
            <div v-if="(stage.dependencies || []).length" class="flex flex-wrap gap-1.5">
              <DeskLink
                v-for="depId in stage.dependencies"
                :key="depId"
                :to="`/stage-plannings/${depId}`"
                class="text-[11px] px-2 py-0.5 bg-brand-50 text-brand-700 font-medium hover:no-underline"
                style="border-radius: 2px;"
              >{{ store.stagePlanningById(depId)?.stageName || depId }}</DeskLink>
            </div>
            <div v-else class="text-xs text-ink-400 italic">No dependencies · this stage can start independently.</div>
          </div>
          <div v-else>
            <div v-if="siblingStages.length" class="flex flex-wrap gap-2">
              <label
                v-for="sib in siblingStages"
                :key="sib.id"
                class="inline-flex items-center gap-1.5 text-xs text-ink-800 cursor-pointer px-2 py-1 border border-ink-200 hover:bg-ink-50"
                style="border-radius: 2px;"
              >
                <input
                  type="checkbox"
                  :checked="(form.dependencies || []).includes(sib.id)"
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
        </div>
      </DeskSection>

      <!-- Tasks in this stage (child table). Visual standard mirrors the BOQ item
           rows inside BOQ detail: tight grid header strip + alternating row stripes
           + brand-50 hover, all edit controls inline. -->
      <DeskSection title="Tasks in this stage">
        <div class="md:col-span-2">
          <div v-if="!editing">
            <div v-if="(stage.stagePlanningTasks || []).length" class="border border-ink-200" style="border-radius: 2px;">
              <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium" style="grid-template-columns: minmax(220px, 1fr) 110px 110px 90px 60px 90px;">
                <div class="px-3 py-1.5">Task</div>
                <div class="px-3 py-1.5">Planned Start</div>
                <div class="px-3 py-1.5">Planned End</div>
                <div class="px-3 py-1.5 text-right">Planned Qty</div>
                <div class="px-3 py-1.5">Unit</div>
                <div class="px-3 py-1.5">Status</div>
              </div>
              <div
                v-for="row in stage.stagePlanningTasks"
                :key="row.id"
                class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 text-sm text-ink-800"
                style="grid-template-columns: minmax(220px, 1fr) 110px 110px 90px 60px 90px;"
              >
                <div class="px-3 py-1.5">
                  <DeskLink v-if="row.task" :to="`/tasks/${row.task}`">{{ taskName(row.task) }}</DeskLink>
                  <span v-else class="text-ink-400 italic">No task linked</span>
                </div>
                <div class="px-3 py-1.5 text-xs text-ink-700">{{ fmtDate(row.plannedStart) || '—' }}</div>
                <div class="px-3 py-1.5 text-xs text-ink-700">{{ fmtDate(row.plannedEnd) || '—' }}</div>
                <div class="px-3 py-1.5 text-right tabular-nums">{{ row.plannedQty || 0 }}</div>
                <div class="px-3 py-1.5 text-xs text-ink-500">{{ row.qtyUnit || '—' }}</div>
                <div class="px-3 py-1.5">
                  <StatusBadge v-if="row.task" :status="taskStatus(row.task)" size="xs" />
                  <span v-else class="text-[10px] text-ink-400">—</span>
                </div>
              </div>
            </div>
            <div v-else class="text-xs text-ink-400 italic">
              No task rows yet · click Edit and "+ Add row" to start planning.
            </div>
          </div>
          <div v-else>
            <div v-if="(form.stagePlanningTasks || []).length" class="border border-ink-200" style="border-radius: 2px;">
              <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium" style="grid-template-columns: minmax(220px, 1fr) 110px 110px 90px 70px 32px;">
                <div class="px-2 py-1.5">Task</div>
                <div class="px-2 py-1.5">Planned Start</div>
                <div class="px-2 py-1.5">Planned End</div>
                <div class="px-2 py-1.5 text-right">Planned Qty</div>
                <div class="px-2 py-1.5">Unit</div>
                <div></div>
              </div>
              <div
                v-for="row in form.stagePlanningTasks"
                :key="row.id"
                class="grid desk-row-stripe border-b border-ink-100 last:border-b-0 items-center"
                style="grid-template-columns: minmax(220px, 1fr) 110px 110px 90px 70px 32px;"
              >
                <div class="px-2 py-1">
                  <DeskSelect v-model="row.task" class="!text-xs">
                    <option :value="null">— Select task —</option>
                    <option v-for="t in tasksForProject" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </DeskSelect>
                </div>
                <div class="px-2 py-1">
                  <DeskInput v-model="row.plannedStart" type="date" class="!text-xs" />
                </div>
                <div class="px-2 py-1">
                  <DeskInput v-model="row.plannedEnd" type="date" class="!text-xs" />
                </div>
                <div class="px-2 py-1">
                  <DeskInput v-model.number="row.plannedQty" type="number" min="0" step="0.1" class="!text-xs text-right" />
                </div>
                <div class="px-2 py-1">
                  <DeskInput v-model="row.qtyUnit" placeholder="m³" class="!text-xs" />
                </div>
                <div class="px-1 py-1 flex justify-center">
                  <button
                    type="button"
                    class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-ink-50"
                    style="border-radius: 2px; color: #B91C1C;"
                    @click="removeChildRow(row.id)"
                    title="Remove row"
                  >✕</button>
                </div>
              </div>
            </div>
            <div v-else class="text-[11px] text-ink-500 italic mb-2">
              No task rows yet · add one to start planning.
            </div>
            <button
              type="button"
              class="mt-2 text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px;"
              @click="addChildRow"
            >+ Add row</button>
          </div>
        </div>
      </DeskSection>

      <!-- Stage Review marker — DELIBERATE STUB. Per §13.3 item 18, Stage Review
           is deferred to M3+ (needs Labour + Procurement + GL data). This is
           where the rollup scorecard (planned-vs-actual labour, cost, schedule)
           will attach. Do NOT build it in M1. -->
      <section class="mt-8 pt-4 border-t border-ink-200">
        <div class="text-xs text-ink-400 italic">
          Stage Review — deferred to M3+. The aggregate scorecard (planned-vs-actual labour, cost, schedule) attaches here once Labour, Procurement, and GL data land.
        </div>
      </section>
    </DeskForm>
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">
    Stage not found ·
    <RouterLink to="/stage-plannings" class="desk-link">Back to list →</RouterLink>
  </div>
</template>
