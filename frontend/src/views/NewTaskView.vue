<script setup>
// New Task — Desk-styled (CLAUDE.md §12.4). Project→WorkPackage cascade is preserved
// exactly: the watch on form.projectId clears the workPackageId when the new project
// doesn't include the previously-selected WP. Validate / save behavior unchanged.

import { reactive, ref, computed, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import { usePermissions } from '@/composables/usePermissions'
import { createDataAdapter } from '@/data/adapters'
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

const form = reactive({
  projectId: route.query.projectId || '',
  workPackageId: route.query.workPackageId || '',
  taskType: 'Activity',
  name: '',
  description: '',
  status: 'Yet To Start',
  priority: 'Medium',
  assignee: '',
  startDate: new Date().toISOString().slice(0, 10),
  endDate: '',
  estimatedHours: 0,
})
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
  subject:        'name',
  project:        'projectId',
  exp_start_date: 'startDate',
  exp_end_date:   'endDate',
  work_package:   'workPackageId',
  owner:          'assignee',
})
const saving = ref(false)

const lockedProject = computed(() => !!route.query.projectId)
const lockedWP = computed(() => !!route.query.workPackageId)

watch(() => form.projectId, (newVal, oldVal) => {
  if (lockedWP.value) return
  if (newVal !== oldVal) form.workPackageId = ''
})

function validate() {
  const e = {}
  if (!form.name) e.name = 'Task name is required'
  if (!form.projectId) e.projectId = 'Project is required'
  if (form.endDate && form.startDate && form.endDate < form.startDate) e.endDate = 'End must be after start'
  setErrors(e)
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const res = await adapter.create('Task', {
      subject: form.name,
      project: form.projectId,
      work_package: form.workPackageId || null,
      task_type: form.taskType || 'Activity',
      description: form.description,
      task_status: form.status,
      priority: form.priority,
      exp_start_date: form.startDate,
      exp_end_date: form.endDate,
      expected_time: Number(form.estimatedHours) || 0,
      owner: form.assignee, // Map to owner for the adapter/Frappe consistency
    })

    const createdTaskId =
      res?.name ||
      res?.id ||
      res?.message?.name ||
      res?.message?.id ||
      res?.data?.name ||
      res?.data?.id ||
      ''

    if (!createdTaskId) {
      showToast('Task created, but could not resolve its ID for navigation', 'error')
      await router.push('/tasks')
      return
    }

    await router.push(`/tasks/${createdTaskId}`)
    await nextTick()
    showToast('Task created')
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to create task', 'error')
  } finally {
    saving.value = false
  }
}
function cancel() { router.back() }

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Task', to: '/tasks' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage
    title="New Task"
    subtitle="Create a task and assign it to a project or work package"
    :breadcrumbs="breadcrumbs"
  >
    <div v-if="!canCreate('task')" class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700" style="border-radius: 6px;">
      You don't have permission to create a task.
    </div>
    <DeskForm v-else>
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
          <DeskInput v-model="form.name" data-test="field-task-name" placeholder="e.g. Block A — Level 6 column casting" />
        </DeskField>
        <DeskField label="Task Type" hint="Drives workflow + Gantt rendering. Milestone = zero-duration.">
          <DeskSelect v-model="form.taskType">
            <option>Activity</option>
            <option>Milestone</option>
            <option>Inspection</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" placeholder="Details about the task, location, scope…" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Hierarchy">
        <DeskField label="Project" required :error="errors.projectId" :hint="lockedProject ? 'Pre-selected — locked.' : ''">
          <DeskLinkPicker
            v-model="form.projectId"
            data-test="pick-project"
            doctype="Project"
            label-field="project_name"
            value-field="name"
            :search-fields="['project_name', 'custom_project_id', 'name']"
            :filters="[['is_group', '=', 1]]"
            :page-length="20"
            placeholder="— Select project —"
            :disabled="lockedProject"
            :error="errors.projectId"
            @change="clearError('projectId')"
          />
        </DeskField>
        <DeskField label="Work Package" :hint="lockedWP ? 'Pre-selected — locked.' : 'Optional · direct project tasks leave blank'">
          <DeskLinkPicker
            v-model="form.workPackageId"
            data-test="pick-wp"
            doctype="Work Package"
            label-field="work_package_name"
            value-field="name"
            :search-fields="['work_package_name', 'code', 'name']"
            :filters="lockedWP ? [] : (form.projectId ? [['project', '=', form.projectId]] : [])"
            :page-length="20"
            placeholder="— None · Direct project task —"
            :disabled="lockedWP"
            :error="errors.workPackageId"
            @change="clearError('workPackageId')"
          />
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
          <DeskLinkPicker
            v-model="form.assignee"
            doctype="User"
            label-field="full_name"
            value-field="name"
            :search-fields="['full_name', 'name', 'email']"
            :page-length="20"
            placeholder="— Select assignee —"
          />
        </DeskField>
        <DeskField label="Status">
          <DeskSelect v-model="form.status">
            <option>Yet To Start</option>
            <option>In Progress</option>
            <option>In Delay</option>
            <option>Completed</option>
            <option>Blocked</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Priority">
          <DeskSelect v-model="form.priority">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
            <option>Urgent</option>
          </DeskSelect>
        </DeskField>
      </DeskSection>
      </div>
    </DeskForm>
  </DeskPage>
</template>
