<script setup>
// New Project — Desk-styled (CLAUDE.md §12.4). Behavior preserved exactly: same
// validate() rules, same store.addProject call, parentId pre-fill from the route
// query for the "+ Add Subproject" entry point.

import { reactive, ref, computed, watch } from 'vue'
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

function firstResourceRow(resource) {
  if (resource?.doc) return resource.doc
  const raw = resource?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  if (raw && typeof raw === 'object' && 'value' in raw) return raw.value || null
  return raw || null
}

// §14 — pre-fill company on the form. For a subproject route (?parentId=), the
// company is inherited from the parent and the field is locked. For a top-level
// project, the field defaults to the active company and the user can change it
// when multi-company. Single-company sites never see the field.
//
// The local Pinia store is empty in remote mode, so resolve the parent from the
// backend; a watcher below copies its company onto the form once it loads.
const parentId = route.query.parentId || null
const parentResource = parentId
  ? adapter.read('Project', parentId, {
      nameField: 'name',
      fields: ['name', 'project_name', 'company'],
      cache: `buildsuite-new-project-parent:${parentId}`,
      transform: (rows) => rows.map((r) => ({
        id: r?.name,
        name: r?.project_name || r?.name || '',
        company: r?.company || '',
      })),
    })
  : null
const fetchedParent = computed(() => firstResourceRow(parentResource))
const initialCompany = (parentId ? store.projectById(parentId)?.company : '') || ''

const form = reactive({
  code: '',
  name: '',
  client: '',
  status: 'New',
  priority: 'Medium',
  type: '',
  company: initialCompany,
  startDate: new Date().toISOString().slice(0, 10),
  endDate: '',
  budget: '',
  pm: '',
  location: '',
  description: '',
  parentId: route.query.parentId || null,
  // Group project by default. Turning this off makes the project a child
  // record under a selected parent (is_group = 0).
  allowSubprojects: !route.query.parentId,
  // Seed stages from the matching BuildSuite Project Template on create.
  // Default ON for top-level projects, OFF for subprojects.
  seedDefaultStages: !route.query.parentId,
  // Import project-level tasks from the template. Off by default; disabled
  // entirely for subprojects since the parent owns the breakdown.
  seedDefaultTasks: false,
})
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
  project_name:        'name',
  custom_project_id:   'code',
  company:             'company',
  customer:            'client',
  project_type:        'type',
  expected_end_date:   'endDate',
  expected_start_date: 'startDate',
  owner:               'pm',
})
const saving = ref(false)

const parentProject = computed(() =>
  fetchedParent.value || (form.parentId ? store.projectById(form.parentId) : null)
)

// Inherit the parent's company onto the form once it resolves from the backend.
// The field is locked for subprojects, so this is the value that gets submitted.
watch(
  () => fetchedParent.value?.company,
  (company) => {
    if (company) form.company = company
  },
  { immediate: true }
)

// The "Allow subprojects" toggle only controls is_group on a top-level project —
// it no longer touches parentId (subprojects come solely from the ?parentId=
// route) nor template seeding (the user controls that via the preview checkbox).

// Template preview — fetches the matching BuildSuite Project Template for the
// selected Project Type. Since Stage Plan Template is autonamed by stage_name,
// each stage_plans row's `stage_plan` field value IS the stage name.
const templateLoading = ref(false)
const bsTemplate = ref(null)

const templateStageNames = computed(() =>
  (bsTemplate.value?.stage_plans || []).map(row => row.stage_plan)
)
const templateTaskCount = computed(() =>
  (bsTemplate.value?.project_task || []).length
)

async function loadTemplateForType(projectType) {
  bsTemplate.value = null
  if (!projectType) return
  templateLoading.value = true
  try {
    const listRes = await fetch(
      '/api/method/frappe.client.get_list?' + new URLSearchParams({
        doctype: 'BuildSuite Project Template',
        fields: JSON.stringify(['name']),
        filters: JSON.stringify([['project_type', '=', projectType]]),
        limit_page_length: 1,
      }),
      { credentials: 'include', headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' } }
    )
    const listData = await listRes.json()
    const rows = listData?.message || []
    if (!rows.length) return

    const docRes = await fetch(
      '/api/method/frappe.client.get?' + new URLSearchParams({
        doctype: 'BuildSuite Project Template',
        name: rows[0].name,
      }),
      { credentials: 'include', headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' } }
    )
    const docData = await docRes.json()
    bsTemplate.value = docData?.message || null
  } catch (err) {
    console.warn('[NewProjectView] Failed to load template for type', projectType, err)
  } finally {
    templateLoading.value = false
  }
}

watch(() => form.type, (type) => loadTemplateForType(type))

function validate() {
  const e = {}
  if (!form.name) e.name = 'Project name is required'
  if (!form.code) e.code = 'Project ID is required'
  // Company is mandatory on Project (§14). The field only renders on multi-company
  // sites; enforce it here so the user gets an inline error instead of a backend
  // 417 on insert.
  if (store.isMultiCompany && !form.company) e.company = 'Company is required'
  if (form.endDate && form.startDate && form.endDate < form.startDate) e.endDate = 'End must be after start'
  setErrors(e)
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const res = await adapter.create('Project', {
      project_name: form.name,
      custom_project_id: form.code,
      // parent_project only ever comes from the ?parentId= route (the "+ Add
      // Subproject" entry on a parent). A subproject is always a leaf (is_group=0);
      // a top-level project is a group iff "Allow subprojects" is on.
      parent_project: form.parentId || null,
      is_group: form.parentId ? 0 : (form.allowSubprojects ? 1 : 0),
      project_status: form.status,
      priority: form.priority,
      company: form.company,
      expected_start_date: form.startDate,
      expected_end_date: form.endDate,
      customer: form.client,
      project_type: form.type,
      estimated_costing: Number(form.budget),
      owner: form.pm,
      notes: form.description,
      custom_seed_default_stages: form.seedDefaultStages ? 1 : 0,
      custom_seed_default_tasks: form.seedDefaultTasks ? 1 : 0,
    })
    showToast('Project created')
    router.push(`/projects/${res.name}`)
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to create project', 'error')
  } finally {
    saving.value = false
  }
}
function cancel() { router.back() }

const subtitle = computed(() =>
  parentProject.value
    ? `Subproject under ${parentProject.value.name}`
    : 'Top-level project'
)

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Project', to: '/projects' },
  ]
  if (parentProject.value) out.push({ label: parentProject.value.name, to: `/projects/${parentProject.value.id}` })
  out.push({ label: 'New' })
  return out
})
</script>

<template>
  <DeskPage title="New Project" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <div v-if="!canCreate('project')" class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700" style="border-radius: 6px;">
      You don't have permission to create a project.
    </div>
    <DeskForm v-else>
      <template #action-bar>
        <DeskActionBar
          :save-label="saving ? 'Creating…' : 'Create project'"
          :saving="saving"
          @save="save"
          @cancel="cancel"
        />
      </template>

      <!-- Narrow centered column so the form doesn't feel sprawling. Save bar
           above stays full-width (matches Frappe Desk's form layout). Same
           pattern as NewTaskView and NewTaskProgressEntryView. -->
      <div class="max-w-3xl mx-auto">
      <DeskSection title="Basic information">
        <DeskField label="Project name" required :error="errors.name">
          <DeskInput v-model="form.name" data-test="field-name" placeholder="e.g. Bangalore Tech Park Phase 2" />
        </DeskField>
        <DeskField label="Project ID" required :error="errors.code" hint="Short unique identifier — used as a code in lists and URLs.">
          <DeskInput v-model="form.code" data-test="field-code" placeholder="e.g. BTP-P2" />
        </DeskField>
        <!-- Session 40: Client is now a Link field onto the Customer master
             (ERPNext-native Customer DocType). The stored value is the
             customer's `name` so existing project records (whose client was
             plain text) still resolve. -->
        <DeskField label="Client" :error="errors.client">
          <DeskLinkPicker
            v-model="form.client"
            data-test="pick-customer"
            doctype="Customer"
            placeholder="Select customer"
            label-field="customer_name"
            value-field="name"
            :search-fields="['customer_name', 'name']"
            order-by="modified desc"
            :page-length="20"
            :error="errors.client"
            @change="clearError('client')"
          />
        </DeskField>
        <DeskField label="Project type" :error="errors.type">
          <DeskLinkPicker
            v-model="form.type"
            data-test="pick-project-type"
            doctype="Project Type"
            placeholder="Select project type"
            label-field="name"
            value-field="name"
            :search-fields="['name']"
            order-by="modified desc"
            :page-length="20"
            :error="errors.type"
            @change="clearError('type')"
          />
          <!-- Template preview: fetched from BuildSuite Project Template where
               project_type matches the selected type. Reacts as type changes. -->
          <div v-if="templateLoading" class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-500 italic" style="border-radius: 6px;">
            Loading template…
          </div>
          <div v-else-if="bsTemplate" class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-700 space-y-1.5" style="border-radius: 6px;">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <div>
                Template seeds <span class="font-medium text-ink-900">{{ templateStageNames.length }} default stages</span>:
                <span class="text-ink-600">{{ templateStageNames.join(' → ') }}</span>
              </div>
              <label class="inline-flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
                <input type="checkbox" v-model="form.seedDefaultStages" class="accent-brand-600" />
                <span class="text-ink-700">Seed default stages</span>
              </label>
            </div>
            <div v-if="!parentProject && templateTaskCount > 0" class="flex items-center justify-between gap-2 flex-wrap pt-1.5 border-t border-ink-100">
              <div>
                <span class="font-medium text-ink-900">{{ templateTaskCount }} tasks</span> from this template can also be imported.
              </div>
              <label class="inline-flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
                <input type="checkbox" v-model="form.seedDefaultTasks" class="accent-brand-600" />
                <span class="text-ink-700">Import default tasks</span>
              </label>
            </div>
            <div v-if="parentProject" class="text-[10px] text-ink-500 italic">
              Subproject — stage and task defaults are off; the parent project owns the timeline.
            </div>
          </div>
          <div v-else-if="form.type" class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-500 italic" style="border-radius: 6px;">
            No template configured for <span class="font-medium text-ink-700">{{ form.type }}</span>. You'll plan stages manually after create.
          </div>
        </DeskField>
        <!-- §14 — Company. Hidden on single-company sites. For subprojects the
             company is inherited from the parent and the field is disabled. -->
        <DeskField
          v-if="store.isMultiCompany"
          label="Company"
          required
          :error="errors.company"
          :hint="errors.company ? '' : (parentProject ? 'Inherited from parent project — locked.' : 'Legal entity this project belongs to. Drives downstream accounting, GST and banking segregation.')"
        >
          <DeskLinkPicker
            v-model="form.company"
            doctype="Company"
            data-test="pick-company"
            placeholder="Select company"
            label-field="name"
            value-field="name"
            :search-fields="['name', 'abbr']"
            order-by="modified desc"
            :page-length="20"
            :disabled="!!parentProject"
            :error="errors.company"
            @change="clearError('company')"
          />
        </DeskField>
        <DeskField label="Location">
          <DeskInput v-model="form.location" placeholder="Site address" />
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" placeholder="Brief description of project scope" />
        </DeskField>
        <DeskField
          v-if="!route.query.parentId"
          label="Subprojects"
          hint="Turn on to break this project into subprojects (e.g. Block A / Block B / Tower 1)."
        >
          <label class="inline-flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              v-model="form.allowSubprojects"
              class="accent-brand-600"
            />
            <span class="text-sm text-ink-700">Allow subprojects under this project</span>
          </label>
        </DeskField>
      </DeskSection>

      <DeskSection title="Schedule &amp; cost">
        <DeskField label="Start date">
          <DeskInput v-model="form.startDate" type="date" />
        </DeskField>
        <DeskField label="Expected end date" :error="errors.endDate">
          <DeskInput v-model="form.endDate" type="date" />
        </DeskField>
        <DeskField label="Project budget (₹)">
          <DeskInput v-model="form.budget" type="number" placeholder="0" />
        </DeskField>
        <DeskField label="Priority">
          <DeskSelect v-model="form.priority">
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
          </DeskSelect>
        </DeskField>
      </DeskSection>

      <DeskSection title="Team &amp; status">
        <DeskField label="Project Manager">
          <DeskLinkPicker
            v-model="form.pm"
            doctype="Employee"
            placeholder="Select project manager"
            label-field="employee_name"
            value-field="name"
            :search-fields="['employee_name', 'name', 'company_email', 'user_id']"
            order-by="modified desc"
            :page-length="20"
          />
        </DeskField>
        <DeskField label="Initial status">
          <DeskSelect v-model="form.status">
            <option>New</option>
            <option>Ongoing</option>
            <option>Delayed</option>
            <option>Completed</option>
          </DeskSelect>
        </DeskField>
      </DeskSection>

      <!-- Hierarchy section removed (Session 38). New projects created from the
           main Projects list are always top-level. Subprojects are created via
           the "+ Add Subproject" entry inside Project Detail, which passes
           ?parentId= on the route — form.parentId picks that up from the route
           query during init and the subproject path still works. -->
      </div>
    </DeskForm>
  </DeskPage>
</template>
