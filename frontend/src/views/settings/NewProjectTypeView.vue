<script setup>
// Project Type Settings — create form. Session 39 (exploratory). Admin/BSA only.

import { reactive, ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { PROJECT_TYPE_TEMPLATES } from '@/data/projectTypeTemplates'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'

const router = useRouter()
const store = useDataStore()

const form = reactive({
  name: '',
  workPackageLabel: '',
  workPackageLabelPlural: '',
  defaultTemplate: '',
  enabled: true,
  sort_order: '',
})
const errors = ref({})
const saving = ref(false)

const templateOptions = computed(() => Object.keys(PROJECT_TYPE_TEMPLATES))

function validate() {
  const e = {}
  if (!form.name.trim()) e.name = 'Name is required'
  // Defend against duplicate names — the join key onto project.type is `name`.
  if (form.name.trim() && store.projectTypes.find(pt => pt.name.toLowerCase() === form.name.trim().toLowerCase())) {
    e.name = `A project type named "${form.name.trim()}" already exists.`
  }
  errors.value = e
  return Object.keys(e).length === 0
}

function save() {
  if (!validate()) return
  saving.value = true
  const record = store.addProjectType({
    name: form.name.trim(),
    workPackageLabel: form.workPackageLabel.trim(),
    workPackageLabelPlural: form.workPackageLabelPlural.trim(),
    defaultTemplate: form.defaultTemplate,
    enabled: form.enabled,
    sort_order: form.sort_order,
  })
  saving.value = false
  router.push(`/app/settings/project-types/${record.id}`)
}
function cancel() { router.back() }

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/app/settings' },
  { label: 'Project Types', to: '/app/settings/project-types' },
  { label: 'New' },
]

onMounted(() => {
  if (!store.isAdmin) router.replace('/app/settings')
})
</script>

<template>
  <DeskPage title="New Project Type" :breadcrumbs="breadcrumbs">
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          :save-label="saving ? 'Creating…' : 'Create project type'"
          :saving="saving"
          @save="save"
          @cancel="cancel"
        />
      </template>

      <div class="max-w-3xl mx-auto">
      <DeskSection title="Basic">
        <DeskField label="Project Type name" required :error="errors.name" hint="e.g. Commercial, Residential, Infrastructure, EPC, Interiors.">
          <DeskInput v-model="form.name" placeholder="e.g. EPC" />
        </DeskField>
        <DeskField label="Sort order" hint="Position in the new-project type dropdown.">
          <DeskInput v-model="form.sort_order" type="number" placeholder="auto-appended" />
        </DeskField>
        <DeskField label="Enabled">
          <label class="flex items-center gap-2 py-1 text-sm cursor-pointer">
            <input type="checkbox" v-model="form.enabled" class="accent-brand-600" />
            <span>{{ form.enabled ? 'Enabled — appears in the new-project dropdown' : 'Disabled — hidden from the new-project dropdown' }}</span>
          </label>
        </DeskField>
      </DeskSection>

      <DeskSection title="Work Package label">
        <DeskField label="Singular" hint='e.g. "Block", "Tower", "Villa Type", "Chainage Segment", "Package". Leave empty to use the site default.'>
          <DeskInput v-model="form.workPackageLabel" placeholder="Work Package" />
        </DeskField>
        <DeskField label="Plural">
          <DeskInput v-model="form.workPackageLabelPlural" placeholder="Work Packages" />
        </DeskField>
      </DeskSection>

      <DeskSection title="Default template">
        <DeskField label="Template" hint="Seeds default stages, work packages and tasks on new projects of this type. Leave empty to create empty projects.">
          <DeskSelect v-model="form.defaultTemplate">
            <option value="">— No template —</option>
            <option v-for="t in templateOptions" :key="t">{{ t }}</option>
          </DeskSelect>
        </DeskField>
      </DeskSection>
      </div>
    </DeskForm>
  </DeskPage>
</template>
