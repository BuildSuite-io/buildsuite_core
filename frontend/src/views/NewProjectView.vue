<script setup>
// New Project — Desk-styled (CLAUDE.md §12.4). Behavior preserved exactly: same
// validate() rules, same store.addProject call, parentId pre-fill from the route
// query for the "+ Add Subproject" entry point.

import { reactive, ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
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

// §14 — pre-fill company on the form. For a subproject route (?parentId=), the
// company is inherited from the parent and the field is locked. For a top-level
// project, the field defaults to the active company and the user can change it
// when multi-company. Single-company sites never see the field.
const initialParent = route.query.parentId ? store.projectById(route.query.parentId) : null
const initialCompany = initialParent?.company || ''

const form = reactive({
  code: '',
  name: '',
  client: '',
  status: 'Open',
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
  // §13.3 item 19 — Light-template stage seeding. Default ON for top-level
  // projects, OFF for subprojects (parent already owns the timeline).
  seedDefaultStages: !route.query.parentId,
  // Session 39 — import default Work Packages + Tasks from the project type's
  // template. Off by default (more invasive than stages — creates breakdown
  // structure + tasks rather than just timeline rows). Disabled entirely for
  // subprojects since their breakdown lives under the parent.
  seedDefaultWorkPackagesAndTasks: false,
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

const parentProject = computed(() => form.parentId ? store.projectById(form.parentId) : null)

watch(
  () => form.allowSubprojects,
  (allow) => {
    if (allow) {
      form.parentId = null
      return
    }

    // Child projects inherit the parent timeline/breakdown.
    form.seedDefaultStages = false
    form.seedDefaultWorkPackagesAndTasks = false
  },
)

// Template preview — re-derives from the picked Project Type. Resolves via
// the Session 39 projectTypes record's defaultTemplate field, falling back to
// the type name itself (matches the addProject server behaviour).
const projectTypeRecord = computed(() => store.projectTypeByName(form.type))
const templateKey = computed(() => projectTypeRecord.value?.defaultTemplate || form.type)
const template = computed(() => store.templateForProjectType(templateKey.value))
const templateStageNames = computed(() => (template.value?.defaultStages || []).map(s => s.stageName))
const templateWPCount    = computed(() => (template.value?.defaultWorkPackages || []).length)
const templateTaskCount  = computed(() => (template.value?.defaultTasks        || []).length)

// Work Package label for the picked type (Session 36 + 39). Used for the
// import-checkbox copy so "Import Towers + tasks" reads naturally for a
// Residential project, "Import Blocks + tasks" for Commercial, etc.
const wpLabelPlural = computed(() => {
  if (projectTypeRecord.value?.workPackageLabelPlural) return projectTypeRecord.value.workPackageLabelPlural
  if (store.coreSettings?.workPackageLabelPlural)      return store.coreSettings.workPackageLabelPlural
  return 'Work Packages'
})

function validate() {
  const e = {}
  if (!form.name) e.name = 'Project name is required'
  if (!form.code) e.code = 'Project ID is required'
  if (!form.allowSubprojects && !form.parentId) e.parentId = 'Parent Project is required'
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
      parent_project: form.allowSubprojects ? null : form.parentId,
      is_group: form.allowSubprojects ? 1 : 0,
      status: form.status,
      priority: form.priority,
      company: form.company,
      expected_start_date: form.startDate,
      expected_end_date: form.endDate,
      customer: form.client,
      project_type: form.type,
      estimated_costing: Number(form.budget),
      owner: form.pm,
      notes: form.description,
      seedDefaultStages: form.seedDefaultStages,
      seedDefaultWorkPackagesAndTasks: form.seedDefaultWorkPackagesAndTasks,
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
    <DeskForm>
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
          <DeskInput v-model="form.name" placeholder="e.g. Bangalore Tech Park Phase 2" />
        </DeskField>
        <DeskField label="Project ID" required :error="errors.code" hint="Short unique identifier — used as a code in lists and URLs.">
          <DeskInput v-model="form.code" placeholder="e.g. BTP-P2" />
        </DeskField>
        <!-- Session 40: Client is now a Link field onto the Customer master
             (ERPNext-native Customer DocType). The stored value is the
             customer's `name` so existing project records (whose client was
             plain text) still resolve. -->
        <DeskField label="Client" :error="errors.client">
          <DeskLinkPicker
            v-model="form.client"
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
          <!-- Template preview (§13.3 item 19). Shows the default stages /
               work packages / tasks that the template will seed on create.
               Updates reactively as the user changes the Project Type. -->
          <div v-if="template" class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-700 space-y-1.5" style="border-radius: 6px;">
            <div class="flex items-center justify-between gap-2 flex-wrap">
              <div>
                Template seeds <span class="font-medium text-ink-900">{{ template.defaultStages.length }} default stages</span>:
                <span class="text-ink-600">{{ templateStageNames.join(' → ') }}</span>
              </div>
              <label class="inline-flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
                <input type="checkbox" v-model="form.seedDefaultStages" class="accent-brand-600" />
                <span class="text-ink-700">Seed default stages</span>
              </label>
            </div>
            <!-- Session 39: WP + tasks import. Disabled / hidden for subprojects
                 since their WP / task breakdown lives under the parent. -->
            <div v-if="!parentProject && templateWPCount > 0" class="flex items-center justify-between gap-2 flex-wrap pt-1.5 border-t border-ink-100">
              <div>
                <span class="font-medium text-ink-900">{{ templateWPCount }} {{ wpLabelPlural.toLowerCase() }}</span>
                + <span class="font-medium text-ink-900">{{ templateTaskCount }} tasks</span> from this template can also be imported.
              </div>
              <label class="inline-flex items-center gap-1.5 cursor-pointer whitespace-nowrap">
                <input type="checkbox" v-model="form.seedDefaultWorkPackagesAndTasks" class="accent-brand-600" />
                <span class="text-ink-700">Import {{ wpLabelPlural.toLowerCase() }} + tasks</span>
              </label>
            </div>
            <div v-if="parentProject" class="text-[10px] text-ink-500 italic">
              Subproject — stage / breakdown defaults are off; the parent project owns the timeline and {{ wpLabelPlural.toLowerCase() }}.
            </div>
          </div>
          <div v-else class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-500 italic" style="border-radius: 6px;">
            No template configured for <span class="font-medium text-ink-700">{{ form.type }}</span>. You'll plan stages manually after create — or pick a different type whose record points at a template.
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
        <DeskField
          v-if="!form.allowSubprojects"
          label="Parent Project"
          :error="errors.parentId"
          hint="Pick the group project this project should roll up under."
        >
          <DeskLinkPicker
            v-model="form.parentId"
            doctype="Project"
            placeholder="Select parent project"
            label-field="project_name"
            value-field="name"
            :search-fields="['project_name', 'custom_project_id', 'name']"
            :filters="[['is_group', '=', 1]]"
            order-by="modified desc"
            :page-length="20"
          />
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
            <option>Open</option>
            <option>Working</option>
            <option>Completed</option>
            <option>On Hold</option>
            <option>Cancelled</option>
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
