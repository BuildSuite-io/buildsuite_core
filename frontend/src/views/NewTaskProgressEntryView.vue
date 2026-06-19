<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import { usePermissions } from '@/composables/usePermissions'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'

const router = useRouter()
const route = useRoute()
const store = useDataStore()
const { canCreate } = usePermissions()
const adapter = createDataAdapter(store)

const cameFromTaskId = route.query.taskId || null

const form = reactive({
  taskId:          cameFromTaskId || '',
  entryDate:       new Date().toISOString().slice(0, 10),
  progressPct:     0,
  narrative:       '',
  skilledLabour:   0,
  unskilledLabour: 0,
  weather:         '',
  blockerFlag:     false,
  blockerNote:     '',
})
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
  task:                'taskId',
  entry_date:          'entryDate',
  cumulative_progress: 'progressPct',
  blocker_detail:      'blockerNote',
})
const saving = ref(false)

// Load the selected task to show the info banner and pre-fill progress.
const taskResource = ref(null)

function loadTaskResource(taskId) {
  if (!taskId) { taskResource.value = null; return }
  taskResource.value = adapter.read('Task', taskId, {
    fields: ['name', 'subject', 'status', 'progress'],
    transform(rows) {
      return rows.map(row => ({
        id:       row?.name || '',
        name:     row?.subject || row?.name || '',
        status:   row?.status || '',
        progress: Number(row?.progress) || 0,
      }))
    },
  })
}

watch(() => form.taskId, loadTaskResource, { immediate: true })

const selectedTask = computed(() => {
  const raw = taskResource.value?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  return null
})

// The task's current cumulative progress is the monotonic floor — a new entry
// can never go below it.
const progressFloor = computed(() => Number(selectedTask.value?.progress) || 0)

// Default the entry to the task's current cumulative progress whenever the
// selected task resolves or changes. Mirrors TaskDetailView's openProgress().
watch(() => selectedTask.value?.id, () => {
  form.progressPct = progressFloor.value
})

// Live validation — surface the monotonic error the moment the value drops
// below the floor (or out of range), instead of waiting for submit.
watch(() => [form.progressPct, progressFloor.value], () => {
  const raw = form.progressPct
  if (raw === '' || raw === null) { clearError('progressPct'); return }
  const pct = Number(raw)
  if (Number.isNaN(pct) || pct < 0 || pct > 100) {
    errors.value = { ...errors.value, progressPct: 'Progress must be between 0 and 100' }
  } else if (pct < progressFloor.value) {
    errors.value = { ...errors.value, progressPct: `Progress can't go below the current ${progressFloor.value}%. Entries are cumulative.` }
  } else {
    clearError('progressPct')
  }
})

// Clamp to the floor on blur/commit so the field can't be left below the task's
// current progress (paste / typing can bypass the input's min attribute).
function clampProgress() {
  let pct = Number(form.progressPct)
  if (Number.isNaN(pct)) pct = progressFloor.value
  form.progressPct = Math.min(100, Math.max(progressFloor.value, pct))
}

function validate() {
  const e = {}
  if (!form.taskId) e.taskId = 'Task is required'
  const pct = Number(form.progressPct)
  if (Number.isNaN(pct) || pct < 0 || pct > 100) {
    e.progressPct = 'Progress must be between 0 and 100'
  } else if (pct < progressFloor.value) {
    e.progressPct = `Progress can't go below the current ${progressFloor.value}%. Entries are cumulative.`
  }
  if (form.blockerFlag && !form.blockerNote.trim()) {
    e.blockerNote = 'Describe the blocker'
  }
  setErrors(e)
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const created = await adapter.create('Task Progress Entry', {
      task:                form.taskId,
      entry_date:          form.entryDate,
      cumulative_progress: Number(form.progressPct),
      narrative:           form.narrative,
      skilled:             Number(form.skilledLabour) || 0,
      unskilled:           Number(form.unskilledLabour) || 0,
      weather:             form.weather,
      blocker:             form.blockerFlag ? 1 : 0,
      blocker_detail:      form.blockerNote,
    })
    if (cameFromTaskId) {
      router.push(`/tasks/${cameFromTaskId}`)
    } else {
      router.push(`/progress-entries/${created.name || created.id}`)
    }
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to file progress entry', 'error')
  } finally {
    saving.value = false
  }
}
function cancel() { router.back() }

const WEATHER_OPTIONS = ['Clear', 'Rainy', 'Hot', 'Cold', 'Storm']

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Task Progress Entry', to: '/progress-entries' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage
    title="New Progress Entry"
    subtitle="File today's progress against a task — labour, weather, blockers"
    :breadcrumbs="breadcrumbs"
  >
    <div v-if="!canCreate('taskProgressEntry')" class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700" style="border-radius: 6px;">
      You don't have permission to file a progress entry.
    </div>
    <DeskForm v-else>
      <template #action-bar>
        <DeskActionBar
          :save-label="saving ? 'Filing…' : 'File entry'"
          :saving="saving"
          @save="save"
          @cancel="cancel"
        />
      </template>

      <div class="max-w-3xl mx-auto">
        <DeskSection title="Task &amp; date" :cols="2">
          <DeskField label="Task" required :error="errors.taskId">
            <DeskLinkPicker
              v-model="form.taskId"
              doctype="Task"
              label-field="subject"
              value-field="name"
              :search-fields="['subject', 'name']"
              :page-length="20"
              placeholder="— Select task —"
            />
          </DeskField>
          <DeskField label="Entry date">
            <DeskInput v-model="form.entryDate" type="date" />
          </DeskField>
          <div v-if="selectedTask" class="md:col-span-2 text-xs text-ink-500 bg-ink-50 border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            Selected task <strong class="text-ink-800">{{ selectedTask.name }}</strong> is currently at
            <strong class="text-ink-800 tabular-nums">{{ selectedTask.progress }}% · {{ selectedTask.status }}</strong>.
            The Cumulative progress % you enter below will become the task's new state on save.
          </div>
        </DeskSection>

        <DeskSection title="Progress" :cols="2">
          <DeskField label="Cumulative progress (%)" required :hint="`The NEW cumulative % after this entry — not a delta. Can't go below the current ${progressFloor}%.`" :error="errors.progressPct">
            <DeskInput v-model="form.progressPct" type="number" :min="progressFloor" max="100" step="1" @change="clampProgress" @blur="clampProgress" />
          </DeskField>
          <div class="md:col-span-2">
            <DeskField label="Narrative" hint="What was completed today? Any context worth recording?">
              <DeskTextarea v-model="form.narrative" :rows="3" placeholder="e.g. Bays 3-4 complete; 285 of 380 m² done. Cube test taken." />
            </DeskField>
          </div>
        </DeskSection>

        <DeskSection title="Labour deployed today" :cols="2">
          <DeskField label="Skilled labour" hint="Count of skilled workers on site today">
            <DeskInput v-model="form.skilledLabour" type="number" />
          </DeskField>
          <DeskField label="Unskilled labour" hint="Count of unskilled workers / helpers">
            <DeskInput v-model="form.unskilledLabour" type="number" />
          </DeskField>
        </DeskSection>

        <DeskSection title="Site conditions" :cols="2">
          <DeskField label="Weather" hint="Optional · only if it's worth recording">
            <DeskSelect v-model="form.weather">
              <option value="">— No record —</option>
              <option v-for="w in WEATHER_OPTIONS" :key="w" :value="w">{{ w }}</option>
            </DeskSelect>
          </DeskField>
          <DeskField label="Blocker">
            <label class="flex items-center gap-2 py-1 text-sm text-ink-700 cursor-pointer">
              <input v-model="form.blockerFlag" type="checkbox" class="h-3.5 w-3.5" />
              Flag a blocker on this entry
            </label>
          </DeskField>
          <div v-if="form.blockerFlag" class="md:col-span-2">
            <DeskField label="Blocker detail" required hint="What blocked progress today?" :error="errors.blockerNote">
              <DeskTextarea v-model="form.blockerNote" :rows="2" placeholder="e.g. Afternoon shower delayed final bay by 2 hours" />
            </DeskField>
          </div>
        </DeskSection>
      </div>
    </DeskForm>
  </DeskPage>
</template>
