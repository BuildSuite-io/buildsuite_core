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
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'

const router = useRouter()
const route = useRoute()
const store = useDataStore()
const adapter = createDataAdapter(store)

const projectsResource = adapter.list('Project', {
  fields: ['name', 'project_name'],
  orderBy: 'modified desc',
  pageLength: 500,
})
const wpsResource = adapter.list('Work Package', {
  fields: ['name', 'work_package_name', 'project', 'code'],
  orderBy: 'modified desc',
  pageLength: 500,
})

const form = reactive({
  projectId: route.query.projectId || '',
  workPackageId: route.query.workPackageId || '',
  taskType: '',
  name: '',
  description: '',
  status: 'Open',
  priority: 'Medium',
  assignee: '',
  startDate: new Date().toISOString().slice(0, 10),
  endDate: '',
  estimatedHours: 0,
})
const errors = ref({})
const saving = ref(false)

const projectRows = computed(() => (Array.isArray(projectsResource.data) ? projectsResource.data : []))
const wpRows = computed(() => (Array.isArray(wpsResource.data) ? wpsResource.data : []))
const availableWPs = computed(() => wpRows.value.filter((wp) => wp.project === form.projectId))

watch(() => form.projectId, () => {
  // Reset WP when the parent project changes if the existing WP doesn't belong.
  if (form.workPackageId && !availableWPs.value.find(wp => wp.name === form.workPackageId)) {
    form.workPackageId = ''
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
      work_package: form.workPackageId || null,
      type: form.taskType || null,
      description: form.description,
      status: form.status,
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
      await router.push('/app/tasks')
      return
    }

    await router.push(`/app/tasks/${createdTaskId}`)
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
        <DeskField label="Task Type">
          <DeskLinkPicker
            v-model="form.taskType"
            doctype="Task Type"
            label-field="name"
            value-field="name"
            :search-fields="['name']"
            :page-length="20"
            placeholder="— Select task type —"
          />
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" placeholder="Details about the task, location, scope…" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Hierarchy">
        <DeskField label="Project" required :error="errors.projectId">
          <DeskLinkPicker
            v-model="form.projectId"
            doctype="Project"
            label-field="project_name"
            value-field="name"
            :search-fields="['project_name', 'custom_project_id', 'name']"
            :filters="[['is_group', '=', 1]]"
            :page-length="20"
            placeholder="— Select project —"
          />
        </DeskField>
        <DeskField label="Work Package" hint="Optional · direct project tasks leave blank">
          <DeskLinkPicker
            v-model="form.workPackageId"
            doctype="Work Package"
            label-field="work_package_name"
            value-field="name"
            :search-fields="['work_package_name', 'code', 'name']"
            :filters="form.projectId ? [['project', '=', form.projectId]] : []"
            :page-length="20"
            placeholder="— None · Direct project task —"
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
            <option>Open</option>
            <option>Working</option>
            <option>Pending Review</option>
            <option>Overdue</option>
            <option>Template</option>
            <option>Completed</option>
            <option>Cancelled</option>
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
