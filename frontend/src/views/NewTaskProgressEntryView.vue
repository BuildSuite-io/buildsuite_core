<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import { showToast } from '@/utils/appToast'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'

const router = useRouter()
const route = useRoute()
const store = useDataStore()
const adapter = createDataAdapter(store)

const tasksResource = adapter.list('Task', {
  fields: ['name', 'subject', 'status', 'progress'],
  orderBy: 'modified desc',
  transform(rows) {
    return rows.map(row => ({
      id:       row?.name || '',
      name:     row?.subject || row?.name || '',
      status:   row?.status || '',
      progress: Number(row?.progress) || 0,
    }))
  },
})

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
const errors = ref({})
const saving = ref(false)

const selectedTask = computed(() =>
  form.taskId ? tasksResource.data.find(t => t.id === form.taskId) || null : null
)

// Pre-fill progress from current task progress when a task is first selected
watch(selectedTask, (t) => {
  if (t && form.progressPct === 0) {
    form.progressPct = t.progress || 0
  }
})

// Auto-select first non-completed task when no taskId was supplied via query
watch(() => tasksResource.data, (tasks) => {
  if (!form.taskId && tasks.length && !cameFromTaskId) {
    form.taskId = tasks.find(t => t.status !== 'Completed')?.id || tasks[0]?.id || ''
  }
}, { immediate: true })

function validate() {
  const e = {}
  if (!form.taskId) e.taskId = 'Task is required'
  const pct = Number(form.progressPct)
  if (Number.isNaN(pct) || pct < 0 || pct > 100) {
    e.progressPct = 'Progress must be between 0 and 100'
  }
  if (form.blockerFlag && !form.blockerNote.trim()) {
    e.blockerNote = 'Describe the blocker'
  }
  errors.value = e
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const created = await adapter.create('Task Update', {
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
      router.push(`/app/tasks/${cameFromTaskId}`)
    } else {
      router.push(`/app/progress-entries/${created.name || created.id}`)
    }
  } catch (err) {
    showToast('Failed to file progress entry', 'error')
    console.error('Failed to create progress entry', err)
  } finally {
    saving.value = false
  }
}
function cancel() { router.back() }

const WEATHER_OPTIONS = ['Clear', 'Rainy', 'Hot', 'Cold', 'Storm']

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Task Progress Entry', to: '/app/progress-entries' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage
    title="New Progress Entry"
    subtitle="File today's progress against a task — labour, weather, blockers"
    :breadcrumbs="breadcrumbs"
  >
    <DeskForm>
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
            <DeskSelect v-model="form.taskId">
              <option value="">— Select task —</option>
              <option v-for="t in tasksResource.data" :key="t.id" :value="t.id">
                {{ t.name }} · {{ t.status }} · {{ t.progress }}%
              </option>
            </DeskSelect>
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
          <DeskField label="Cumulative progress (%)" required hint="The NEW cumulative % after this entry — not a delta. 0–100." :error="errors.progressPct">
            <DeskInput v-model="form.progressPct" type="number" min="0" max="100" step="1" />
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
