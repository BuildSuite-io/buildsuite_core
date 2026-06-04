<script setup>
// New Task — Desk-styled (CLAUDE.md §12.4). Project→WorkPackage cascade is preserved
// exactly: the watch on form.projectId clears the workPackageId when the new project
// doesn't include the previously-selected WP. Validate / save behavior unchanged.

import { reactive, ref, computed, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import { createDataAdapter } from '@/data/adapters'
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

const projectsResource = adapter.list('Project')
const wpsResource = adapter.list('Work Package')

const form = reactive({
  projectId: route.query.projectId || (projectsResource.data[0]?.name || ''),
  workPackageId: route.query.workPackageId || null,
  task_type: 'Activity',     // proposal §M2 Select — Activity / Milestone / Inspection
  activityType: null,        // optional Link to Activity Type master (renamed from taskType in S31)
  name: '',
  description: '',
  status: 'Open',
  priority: 'Medium',
  assignee: store.team[1]?.id || '',
  startDate: new Date().toISOString().slice(0, 10),
  endDate: '',
  estimatedHours: 0,
})
const errors = ref({})
const saving = ref(false)

const availableWPs = computed(() => wpsResource.data.filter(wp => wp.project === form.projectId))

// Activity Types filtered by the selected project's type (per §13.3 item 16 — the
// Project Type → Activity Type mapping). Falls back to all activity types if no
// project is selected. We deliberately don't pre-fill any other fields when an
// activity type is picked — the user opted into that conservative scope.
const selectedProject = computed(() => projectsResource.data.find(p => p.name === form.projectId))
const availableActivityTypes = computed(() => {
  const pt = selectedProject.value?.project_type
  return pt ? store.activityTypesForProjectType(pt) : store.activityTypes
})

watch(() => form.projectId, () => {
  // Reset WP when the parent project changes if the existing WP doesn't belong.
  if (form.workPackageId && !availableWPs.value.find(wp => wp.name === form.workPackageId)) {
    form.workPackageId = null
  }
  // Same for activity type — if the picked type isn't applicable to the new project type, clear it.
  if (form.activityType && !availableActivityTypes.value.find(at => at.id === form.activityType)) {
    form.activityType = null
  }
})

function validate() {
  const e = {}
  if (!form.name) e.name = 'Task name is required'
  if (!form.projectId) e.projectId = 'Project is required'
  if (form.endDate && form.startDate && form.endDate < form.startDate) e.endDate = 'End must be after start'
  errors.value = e
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const res = await adapter.create('Task', {
      subject: form.name,
      project: form.projectId,
      work_package: form.workPackageId,
      task_type: form.task_type,
      description: form.description,
      status: form.status,
      priority: form.priority,
      exp_start_date: form.startDate,
      exp_end_date: form.endDate,
      owner: form.assignee, // Map to owner for the adapter/Frappe consistency
      activity_type: form.activityType,
    })
    await router.push(`/app/tasks/${res.name}`)
    await nextTick()
    showToast('Task created')
  } catch (err) {
    showToast('Failed to create task', 'error')
    console.error('Failed to create task:', err)
  } finally {
    saving.value = false
  }
}
function cancel() { router.back() }

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Task', to: '/app/tasks' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage
    title="New Task"
    subtitle="Create a task and assign it to a project or work package"
    :breadcrumbs="breadcrumbs"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          save-label="Create task"
          @save="save"
          @cancel="cancel"
        />
      </template>

      <!-- Narrow centered column so the form doesn't feel sprawling. Save bar
           above stays full-width (matches Frappe Desk's form layout). -->
      <div class="max-w-3xl mx-auto">
      <DeskSection title="Task details" :cols="1">
        <DeskField label="Task name" required :error="errors.name">
          <DeskInput v-model="form.name" placeholder="e.g. Block A — Level 6 column casting" />
        </DeskField>
        <!-- Task Type per proposal §M2 — drives the task's workflow.
             Activity = standard work with progress entries (default).
             Milestone = checkpoint, no qty progress (status-only).
             Inspection = pass/fail gate (QC workflow). -->
        <DeskField
          label="Task Type"
          required
          hint="Activity = standard work with progress entries; Milestone = checkpoint with no qty progress; Inspection = pass/fail gate."
        >
          <DeskSelect v-model="form.task_type">
            <option value="Activity">Activity</option>
            <option value="Milestone">Milestone</option>
            <option value="Inspection">Inspection</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" placeholder="Details about the task, location, scope…" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Hierarchy">
        <DeskField label="Project" required :error="errors.projectId">
          <DeskSelect v-model="form.projectId">
            <option value="">— Select project —</option>
            <option v-for="p in projectsResource.data" :key="p.name" :value="p.name">{{ p.project_name }}</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Work Package" hint="Optional · direct project tasks leave blank">
          <DeskSelect v-model="form.workPackageId">
            <option :value="null">— None · Direct project task —</option>
            <option v-for="wp in availableWPs" :key="wp.name" :value="wp.name">{{ wp.package_name }}</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Activity Type" hint="Activity Type provides default labour mix and productivity baseline for this task.">
          <DeskSelect v-model="form.activityType">
            <option :value="null">— None —</option>
            <option v-for="at in availableActivityTypes" :key="at.id" :value="at.id">{{ at.name }} · {{ at.category }}</option>
          </DeskSelect>
        </DeskField>
      </DeskSection>

      <DeskSection title="Schedule" :cols="3">
        <DeskField label="Start date">
          <DeskInput v-model="form.startDate" type="date" />
        </DeskField>
        <DeskField label="Due date" :error="errors.endDate">
          <DeskInput v-model="form.endDate" type="date" />
        </DeskField>
        <DeskField label="Estimated hours">
          <DeskInput v-model="form.estimatedHours" type="number" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Assignment" :cols="3">
        <DeskField label="Assignee">
          <DeskSelect v-model="form.assignee">
            <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }}</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Status">
          <DeskSelect v-model="form.status">
            <option>Open</option>
            <option>In Progress</option>
            <option>Completed</option>
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
    </DeskForm>
  </DeskPage>
</template>
