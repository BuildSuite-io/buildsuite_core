<script setup>
// Work Package Detail — Desk-styled. View + edit + delete. View mode shows
// the summary strip and a tasks list. Edit mode swaps the detail fields to
// inputs and a save bar appears at the top.

import { ref, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import TaskFormModal from '@/components/TaskFormModal.vue'
import { createDataAdapter } from '@/data/adapters'
import { fmtCompactINR, fmtDate } from '@/utils/format'

const props = defineProps({ id: String })
const store = useDataStore()
const router = useRouter()
const adapter = createDataAdapter(store)

function firstResourceRow(resource) {
  if (resource?.doc) return resource.doc
  const raw = resource?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  if (raw && typeof raw === 'object' && 'value' in raw) return raw.value || null
  return raw || null
}

const workPackageResource = ref(null)

function loadWorkPackageResource() {
  if (!props.id) {
    workPackageResource.value = null
    return
  }
  workPackageResource.value = adapter.read('Work Package', props.id, {
    fields: ['*'],
    cache: `buildsuite-wp-detail:${props.id}`,
    transform(rows) {
      return rows.map(row => ({
        id: row.name || row.id,
        code: row.code || '',
        name: row.work_package_name || row.name || '',
        projectId: row.project || '',
        status: row.status || '',
        budget: Number(row.budget) || 0,
        progress: Number(row.progress) || 0,
        startDate: row.start_date || null,
        endDate: row.end_date || null,
        owner: row.owner_user || '',
        description: row.description || '',
      }))
    }
  })
}

watch(() => props.id, loadWorkPackageResource, { immediate: true })

const wp = computed(() => {
  const backend = firstResourceRow(workPackageResource.value)
  return backend || store.workPackageById(props.id)
})
const project = computed(() => wp.value ? store.projectById(wp.value.projectId) : null)

const tasksResource = ref(null)
function loadTasksResource() {
  if (!wp.value?.id) {
    tasksResource.value = null
    return
  }
  tasksResource.value = adapter.list('Task', {
    filters: [['work_package', '=', wp.value.id]],
    orderBy: 'modified desc',
    pageLength: 300,
    cache: `buildsuite-wp-tasks:${wp.value.id}`,
    transform(rows) {
      return rows.map(row => ({
        id: row.name || row.id,
        name: row.subject || row.task_name || row.name || '',
        projectId: row.project || '',
        status: row.status || 'Open',
        priority: row.priority || 'Medium',
        task_type: row.type || row.task_type || 'Activity',
        assignee: row.owner || '',
        startDate: row.exp_start_date || null,
        endDate: row.exp_end_date || null,
        progress: Number(row.progress) || 0,
      }))
    }
  })
}
watch(() => wp.value?.id, loadTasksResource, { immediate: true })

const tasks = computed(() => {
  const raw = tasksResource.value?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return store.tasksByWorkPackage(props.id)
})

// Edit-mode state. `form` is a working copy that gets reset on cancel so the
// store record isn't mutated mid-edit.
const editing = ref(false)
const saving = ref(false)
const form = ref({})
const { errors, applyServerErrors, setErrors } = useFormErrors({
  work_package_name: 'name',
  end_date:          'endDate',
  start_date:        'startDate',
  owner_user:        'owner',
})

function snapshot() {
  if (!wp.value) return {}
  const data = JSON.parse(JSON.stringify(wp.value))
  // Normalize date field names for the form
  if (data.startDate) data.startDate = data.startDate
  if (data.endDate) data.endDate = data.endDate
  return data
}
watch(wp, (v) => { if (v && !editing.value) form.value = snapshot() }, { immediate: true })

function startEdit() {
  form.value = snapshot()
  setErrors({})
  editing.value = true
}
function cancelEdit() {
  form.value = snapshot()
  setErrors({})
  editing.value = false
}
function validate() {
  const e = {}
  if (!form.value.name) e.name = 'Work package name is required'
  if (form.value.endDate && form.value.startDate && form.value.endDate < form.value.startDate) {
    e.endDate = 'End must be after start'
  }
  setErrors(e)
  return Object.keys(e).length === 0
}
async function saveEdit() {
  if (!validate()) return
  saving.value = true
  try {
    await adapter.update('Work Package', wp.value.id, {
      code: form.value.code || wp.value.code,
      work_package_name: form.value.name,
      description: form.value.description || '',
      status: form.value.status,
      budget: Number(form.value.budget) || 0,
      start_date: form.value.startDate || '',
      end_date: form.value.endDate || '',
      owner_user: form.value.owner,
    })
    workPackageResource.value?.reload?.()
    editing.value = false
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update work package', 'error')
  } finally {
    saving.value = false
  }
}
function onPrimary() { editing.value ? saveEdit() : startEdit() }

async function onDelete() {
  if (!wp.value) return
  const n = tasks.value.length
  const msg = n
    ? `Delete "${wp.value.name}"? This will also delete ${n} task${n === 1 ? '' : 's'} and any progress entries on them.`
    : `Delete "${wp.value.name}"?`
  if (!confirm(msg)) return
  const wpId = wp.value.id
  try {
    await adapter.remove('Work Package', wpId)
    router.push('/work-packages')
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to delete work package', 'error')
  }
}

const taskSearch = ref('')
const tasksFiltered = computed(() => {
  const term = taskSearch.value.trim().toLowerCase()
  if (!term) return tasks.value
  return tasks.value.filter(t => t.name.toLowerCase().includes(term))
})

// Task creation modal — replaces the routing entry to /app/tasks/new.
const taskModalOpen = ref(false)

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Work Package', to: '/work-packages' },
  ]
  if (project.value) out.push({ label: project.value.name, to: `/projects/${project.value.id}` })
  return out
})

const taskCols = [
  { key: 'name',     label: 'Task' },
  { key: 'status',   label: 'Status' },
  { key: 'priority', label: 'Priority' },
  { key: 'task_type', label: 'Task Type' },
  { key: 'assignee', label: 'Assignee' },
  { key: 'endDate',  label: 'Due' },
  { key: 'progress', label: 'Progress', align: 'right' },
]

function onTaskRowClick(row) { router.push(`/tasks/${row.id}`) }

// Schedule-based traffic-light color for the summary progress bar.
const today = new Date()
function progressBarColor(w) {
  if (!w || !w.startDate || !w.endDate) return 'bg-ink-300'
  const start = new Date(w.startDate).getTime()
  const end = new Date(w.endDate).getTime()
  const total = end - start
  if (total <= 0) return 'bg-success-500'
  const elapsed = Math.max(0, Math.min(total, today.getTime() - start))
  const expected = (elapsed / total) * 100
  if (expected <= 0) return 'bg-success-500'
  const v = ((expected - w.progress) / expected) * 100
  if (v > 15) return 'bg-danger-500'
  if (v > 5) return 'bg-warning-500'
  return 'bg-success-500'
}
</script>

<template>
  <DeskPage
    v-if="wp"
    :title="wp.name"
    :subtitle="`${wp.code} · ${wp.id}`"
    :breadcrumbs="breadcrumbs"
    :status="wp.status"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          :save-label="editing ? (saving ? 'Saving…' : 'Save') : 'Edit'"
          :show-cancel="editing"
          :saving="saving"
          cancel-label="Cancel"
          @save="onPrimary"
          @cancel="cancelEdit"
        >
          <template #menu>
            <button
              type="button"
              class="text-xs px-2.5 py-1 border border-danger-200 text-danger-700 hover:bg-danger-50"
              style="border-radius: 6px;"
              @click="onDelete"
            >Delete</button>
          </template>
        </DeskActionBar>
      </template>

      <!-- Summary strip — view mode only (becomes Details section when editing) -->
      <div v-if="!editing" class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Budget</div>
          <div class="text-sm text-ink-900 mt-0.5 tabular-nums">{{ fmtCompactINR(wp.budget) }}</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Progress</div>
          <div class="flex items-center gap-2 mt-1">
            <div class="flex-1 h-1 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
              <div class="h-full" :class="progressBarColor(wp)" :style="`width:${wp.progress}%`"></div>
            </div>
            <span class="text-xs text-ink-700 tabular-nums w-8 text-right">{{ wp.progress }}%</span>
          </div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Timeline</div>
          <div class="text-xs text-ink-700 mt-0.5">{{ fmtDate(wp.startDate) }} → {{ fmtDate(wp.endDate) }}</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Owner</div>
          <div class="mt-1"><UserAvatar :user-id="wp.owner" :show-name="true" /></div>
        </div>
      </div>

      <!-- View-mode details -->
      <div v-if="!editing && wp.description" class="mb-4 px-3 py-2 bg-white border border-ink-200" style="border-radius: 6px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Description</div>
        <div class="text-sm text-ink-800 leading-snug whitespace-pre-line">{{ wp.description }}</div>
      </div>

      <!-- Edit-mode form -->
      <div v-if="editing" class="max-w-3xl mx-auto">
        <DeskSection title="Basic information">
          <DeskField label="Project" hint="Locked after create — moving a work package across projects isn't supported.">
            <div class="text-sm text-ink-900 py-1">{{ project?.name || '—' }}</div>
          </DeskField>
          <DeskField label="Work Package name" required :error="errors.name">
            <DeskInput v-model="form.name" />
          </DeskField>
          <DeskField label="Code">
            <DeskInput v-model="form.code" />
          </DeskField>
          <DeskField label="Description">
            <DeskTextarea v-model="form.description" :rows="3" />
          </DeskField>
        </DeskSection>

        <DeskSection title="Schedule & cost">
          <DeskField label="Start date">
            <DeskInput v-model="form.startDate" type="date" />
          </DeskField>
          <DeskField label="Expected end date" :error="errors.endDate">
            <DeskInput v-model="form.endDate" type="date" />
          </DeskField>
          <DeskField label="Budget (₹)">
            <DeskInput v-model="form.budget" type="number" />
          </DeskField>
          <DeskField label="Status">
            <DeskSelect v-model="form.status">
              <option>Planned</option>
              <option>In Progress</option>
              <option>On Hold</option>
              <option>Completed</option>
            </DeskSelect>
          </DeskField>
        </DeskSection>

        <DeskSection title="Ownership">
          <DeskField label="Owner">
            <DeskSelect v-model="form.owner">
              <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }} — {{ m.role }}</option>
            </DeskSelect>
          </DeskField>
        </DeskSection>
      </div>

      <!-- Tasks list — view mode only (hidden while editing the WP itself) -->
      <template v-if="!editing">
        <div class="text-xs text-ink-500 mb-2 mt-4">{{ tasks.length }} task{{ tasks.length === 1 ? '' : 's' }} in this work package</div>
        <DeskList
          v-model="taskSearch"
          :rows="tasksFiltered"
          :columns="taskCols"
          row-key="id"
          search-placeholder="Search tasks…"
          @row-click="onTaskRowClick"
        >
          <template #actions>
            <button type="button" class="desk-save-btn" @click="taskModalOpen = true">+ Add Task</button>
          </template>

          <template #cell-name="{ row }">
            <DeskLink :to="`/tasks/${row.id}`" @click.stop>{{ row.name }}</DeskLink>
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
            <div class="text-sm text-ink-500">No tasks in this work package yet.</div>
          </template>
        </DeskList>
      </template>
    </DeskForm>

    <!-- New Task modal — pre-fills project + work package from this WP. -->
    <TaskFormModal
      v-if="wp"
      v-model:open="taskModalOpen"
      :project-id="wp.projectId"
      :work-package-id="wp.id"
    />
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">Work package not found</div>
</template>
