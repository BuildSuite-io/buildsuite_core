<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
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
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'

const router = useRouter()
const store = useDataStore()
const adapter = createDataAdapter(store)

const form = reactive({ templateCode: '', templateName: '', projectType: '', description: '' })
const { errors, applyServerErrors, setErrors } = useFormErrors({
  template_code: 'templateCode',
  template_name: 'templateName',
})
const saving = ref(false)

function validate() {
  const e = {}
  if (!form.templateCode.trim()) e.templateCode = 'Code is required'
  if (!form.templateName.trim()) e.templateName = 'Name is required'
  setErrors(e)
  return Object.keys(e).length === 0
}

function onCancel() {
  router.back()
}

async function onSave() {
  if (!validate()) return
  saving.value = true
  try {
    const res = await adapter.create('Estimate Template', {
      template_code: form.templateCode.trim(),
      template_name: form.templateName.trim(),
      project_type: form.projectType || null,
      description: form.description,
    })
    router.push(`/estimate-template/${res.name}`)
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to create estimate template', 'error')
  } finally {
    saving.value = false
  }
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Estimate Template', to: '/estimate-template' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage title="New Estimate Template" subtitle="A reusable BOQ skeleton — add rows after creating"
    :breadcrumbs="breadcrumbs">
    <DeskForm>
      <template #action-bar>
        <DeskActionBar :save-label="saving ? 'Creating…' : 'Create template'" :saving="saving" @save="onSave"
          @cancel="onCancel" />
      </template>

      <DeskSection title="Template details">
        <DeskField label="Code" required hint="Short stable identifier (e.g. ET-RES-TOWER)."
          :error="errors.templateCode">
          <DeskInput v-model="form.templateCode" placeholder="ET-..." />
        </DeskField>
        <DeskField label="Name" required :error="errors.templateName">
          <DeskInput v-model="form.templateName" />
        </DeskField>
        <DeskField label="Project Type" hint="Used to suggest this template for matching project types.">
          <DeskLinkPicker v-model="form.projectType" doctype="Project Type" label-field="name" value-field="name"
            placeholder="— Any project type —" />
        </DeskField>
        <DeskField label="Description">
          <DeskTextarea v-model="form.description" :rows="3" />
        </DeskField>
      </DeskSection>
    </DeskForm>
  </DeskPage>
</template>
