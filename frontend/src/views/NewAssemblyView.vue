<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { showToast } from '@/utils/appToast'
import { useFormErrors } from '@/composables/useFormErrors'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
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
const store = useDataStore()
const adapter = createDataAdapter(store)

const { selectOptions } = useDoctypeMeta('Assembly')
const categoryOptions = computed(() => selectOptions('category'))

const form = reactive({ assemblyCode: '', assemblyName: '', uom: '', category: '', notes: '' })
const { errors, applyServerErrors, setErrors } = useFormErrors({
  assembly_code: 'assemblyCode',
  assembly_name: 'assemblyName',
  uom: 'uom',
})
const saving = ref(false)

function validate() {
  const e = {}
  if (!form.assemblyCode.trim()) e.assemblyCode = 'Code is required'
  if (!form.assemblyName.trim()) e.assemblyName = 'Name is required'
  if (!form.uom) e.uom = 'Unit is required'
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
    const res = await adapter.create('Assembly', {
      assembly_code: form.assemblyCode.trim(),
      assembly_name: form.assemblyName.trim(),
      uom: form.uom,
      category: form.category,
      notes: form.notes,
    })
    router.push(`/assembly/${res.name}`)
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to create assembly', 'error')
  } finally {
    saving.value = false
  }
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Assembly', to: '/assembly' },
  { label: 'New' },
]
</script>

<template>
  <DeskPage title="New Assembly" subtitle="Rate-analysis recipe priced per unit" :breadcrumbs="breadcrumbs">
    <DeskForm>
      <template #action-bar>
        <DeskActionBar :save-label="saving ? 'Creating…' : 'Create assembly'" :saving="saving" @save="onSave"
          @cancel="onCancel" />
      </template>

      <DeskSection title="Assembly details">
        <DeskField label="Code" required hint="Short stable identifier (e.g. ASM-RCC-M25)."
          :error="errors.assemblyCode">
          <DeskInput v-model="form.assemblyCode" placeholder="ASM-..." />
        </DeskField>
        <DeskField label="Name" required :error="errors.assemblyName">
          <DeskInput v-model="form.assemblyName" />
        </DeskField>
        <DeskField label="Unit (per)" required hint="The per-unit basis — component coefficients mean &quot;how much per one of this unit&quot;." :error="errors.uom">
          <DeskLinkPicker v-model="form.uom" doctype="UOM" label-field="name" value-field="name"
            placeholder="— Select unit —" />
        </DeskField>
        <DeskField label="Category">
          <DeskSelect v-model="form.category">
            <option value="">— Select —</option>
            <option v-for="c in categoryOptions" :key="c">{{ c }}</option>
          </DeskSelect>
        </DeskField>
        <DeskField label="Notes">
          <DeskTextarea v-model="form.notes" :rows="3" />
        </DeskField>
      </DeskSection>
    </DeskForm>
  </DeskPage>
</template>
