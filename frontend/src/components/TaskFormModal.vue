<script setup>
// Reusable "+ Add Task" modal. Opens with v-model:open and a pre-filled
// project (+ optional work package). On save calls store.addTask and emits
// `created` with the new record so the parent can react (refresh list,
// route, etc). Pure presentational — no routing.

import { reactive, ref, computed, watch } from 'vue'
import { useDataStore } from '@/stores'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  projectId: { type: String, default: '' },
  workPackageId: { type: String, default: '' },
})
const emit = defineEmits(['update:open', 'created'])

const store = useDataStore()
const errors = ref({})
const saving = ref(false)

const form = reactive({
  projectId: '',
  workPackageId: null,
  task_type: 'Activity',
  activityType: null,
  name: '',
  description: '',
  status: 'Open',
  priority: 'Medium',
  assignee: '',
  startDate: '',
  endDate: '',
})

// Reset the form whenever the modal opens. Pre-fill from props.
watch(() => props.open, (isOpen) => {
  if (!isOpen) return
  form.projectId      = props.projectId || (store.projects[0]?.id || '')
  form.workPackageId  = props.workPackageId || null
  form.task_type      = 'Activity'
  form.activityType   = null
  form.name           = ''
  form.description    = ''
  form.status         = 'Open'
  form.priority       = 'Medium'
  form.assignee       = store.team[1]?.id || store.team[0]?.id || ''
  form.startDate      = new Date().toISOString().slice(0, 10)
  form.endDate        = ''
  errors.value = {}
})

const selectedProject = computed(() => store.projectById(form.projectId))
const availableWPs = computed(() => store.workPackages.filter(wp => wp.projectId === form.projectId))
const availableActivityTypes = computed(() => {
  const pt = selectedProject.value?.type
  return pt ? store.activityTypesForProjectType(pt) : store.activityTypes
})

// Project is locked when the parent supplied it. WP is locked when both
// project + WP are supplied (work-package-scoped entry). When the parent
// supplies only the project (Tasks tab on Project Detail), WP is still
// editable.
const projectLocked = computed(() => !!props.projectId)
const wpLocked = computed(() => !!props.workPackageId)

watch(() => form.projectId, () => {
  if (form.workPackageId && !availableWPs.value.find(wp => wp.id === form.workPackageId)) {
    form.workPackageId = null
  }
  if (form.activityType && !availableActivityTypes.value.find(at => at.id === form.activityType)) {
    form.activityType = null
  }
})

function close() { emit('update:open', false) }

function validate() {
  const e = {}
  if (!form.name.trim()) e.name = 'Task name is required'
  if (!form.projectId)   e.projectId = 'Project is required'
  if (form.endDate && form.startDate && form.endDate < form.startDate) {
    e.endDate = 'End must be after start'
  }
  errors.value = e
  return Object.keys(e).length === 0
}

function save() {
  if (!validate()) return
  saving.value = true
  const task = store.addTask({ ...form })
  saving.value = false
  emit('created', task)
  close()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
      @click.self="close"
    >
      <div
        class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
        style="border-radius: 12px; max-height: calc(100vh - 3rem);"
        @click.stop
      >
        <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-semibold text-ink-900">New task</h2>
            <p v-if="selectedProject" class="text-[11px] text-ink-500 mt-0.5 truncate">
              {{ selectedProject.name }}<template v-if="wpLocked && store.workPackageById(form.workPackageId)"> · {{ store.workPackageById(form.workPackageId).name }}</template>
            </p>
          </div>
          <button
            type="button"
            class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
            aria-label="Close"
            @click="close"
          >×</button>
        </header>

        <div class="p-5 overflow-y-auto flex-1">
          <DeskSection title="Task details">
            <DeskField label="Task name" required :error="errors.name">
              <DeskInput v-model="form.name" placeholder="e.g. Level 5 column casting" />
            </DeskField>
            <DeskField
              label="Task Type"
              required
              hint="Activity = standard work with progress entries; Milestone = checkpoint; Inspection = pass/fail gate."
            >
              <DeskSelect v-model="form.task_type">
                <option value="Activity">Activity</option>
                <option value="Milestone">Milestone</option>
                <option value="Inspection">Inspection</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Description">
              <DeskTextarea v-model="form.description" :rows="3" placeholder="Optional context for this task" />
            </DeskField>
          </DeskSection>

          <DeskSection title="Hierarchy">
            <DeskField label="Project" required :error="errors.projectId" :hint="projectLocked ? 'Pre-selected from where you came in — locked.' : ''">
              <DeskSelect v-model="form.projectId" :disabled="projectLocked">
                <option value="">— Select project —</option>
                <option v-for="p in store.projects" :key="p.id" :value="p.id">{{ p.name }}</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Work Package" :hint="wpLocked ? 'Pre-selected — locked.' : 'Optional — leave blank to attach directly to the project.'">
              <DeskSelect v-model="form.workPackageId" :disabled="wpLocked">
                <option :value="null">— None —</option>
                <option v-for="wp in availableWPs" :key="wp.id" :value="wp.id">{{ wp.name }}</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Activity Type" hint="Optional — provides default labour mix and productivity baseline.">
              <DeskSelect v-model="form.activityType">
                <option :value="null">— None —</option>
                <option v-for="at in availableActivityTypes" :key="at.id" :value="at.id">{{ at.name }}<template v-if="at.category"> · {{ at.category }}</template></option>
              </DeskSelect>
            </DeskField>
          </DeskSection>

          <DeskSection title="Schedule">
            <DeskField label="Start date">
              <DeskInput v-model="form.startDate" type="date" />
            </DeskField>
            <DeskField label="End date" :error="errors.endDate">
              <DeskInput v-model="form.endDate" type="date" />
            </DeskField>
          </DeskSection>

          <DeskSection title="Assignment & status">
            <DeskField label="Assignee">
              <DeskSelect v-model="form.assignee">
                <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }} — {{ m.role }}</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Status">
              <DeskSelect v-model="form.status">
                <option>Open</option>
                <option>In Progress</option>
                <option>Completed</option>
                <option>Cancelled</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Priority">
              <DeskSelect v-model="form.priority">
                <option>Low</option>
                <option>Medium</option>
                <option>High</option>
              </DeskSelect>
            </DeskField>
          </DeskSection>
        </div>

        <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
          <button
            type="button"
            class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
            style="border-radius: 6px;"
            @click="close"
          >Cancel</button>
          <button
            type="button"
            class="desk-save-btn"
            :disabled="saving"
            @click="save"
          >{{ saving ? 'Creating…' : 'Create task' }}</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
