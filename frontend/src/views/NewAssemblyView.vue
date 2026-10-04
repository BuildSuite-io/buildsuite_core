<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { __ } from '@/utils/translate'
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
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'

const router = useRouter()
const store = useDataStore()
const adapter = createDataAdapter(store)
const { canCreate } = usePermissions()

const form = reactive({ assemblyCode: '', assemblyName: '', uom: '', category: '', notes: '' })
const { errors, applyServerErrors, setErrors } = useFormErrors({
  assembly_code: 'assemblyCode',
  assembly_name: 'assemblyName',
  uom: 'uom',
})
const saving = ref(false)

function validate() {
  const e = {}
  if (!form.assemblyCode.trim()) e.assemblyCode = __('Code is required')
  if (!form.assemblyName.trim()) e.assemblyName = __('Name is required')
  if (!form.uom) e.uom = __('Unit is required')
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
    showToast(applyServerErrors(err) ?? __('Failed to create assembly'), 'error')
  } finally {
    saving.value = false
  }
}

const breadcrumbs = [
  { label: __('BuildSuite Core'), to: '/' },
  { label: __('Estimation'), to: '/estimation' },
  { label: __('Assembly'), to: '/assembly' },
  { label: __('New') },
]
</script>

<template>
  <DeskPage :title="__('New Assembly')" :subtitle="__('Rate-analysis recipe priced per unit')" :breadcrumbs="breadcrumbs">
    <div
      v-if="!canCreate('assembly')"
      class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
      style="border-radius: 6px"
    >
      {{ __("You don't have permission to create an assembly.") }}
    </div>
    <DeskForm v-else>
      <template #action-bar>
        <DeskActionBar :save-label="saving ? __('Creating…') : __('Create assembly')" :saving="saving" @save="onSave"
          @cancel="onCancel" />
      </template>

      <DeskSection :title="__('Assembly details')">
        <DeskField :label="__('Code')" required :hint="__('Short stable identifier (e.g. ASM-RCC-M25).')"
          :error="errors.assemblyCode">
          <DeskInput v-model="form.assemblyCode" :placeholder="__('ASM-...')" />
        </DeskField>
        <DeskField :label="__('Name')" required :error="errors.assemblyName">
          <DeskInput v-model="form.assemblyName" />
        </DeskField>
        <DeskField :label="__('Unit (per)')" required :hint="__('The per-unit basis — component coefficients mean &quot;how much per one of this unit&quot;.')" :error="errors.uom">
          <DeskLinkPicker v-model="form.uom" doctype="UOM" label-field="name" value-field="name"
            :placeholder="__('— Select unit —')" />
        </DeskField>
        <DeskField :label="__('Category')">
          <DeskLinkPicker v-model="form.category" doctype="Assembly Category" label-field="name"
            value-field="name" :placeholder="__('— Select category —')" />
        </DeskField>
        <DeskField :label="__('Notes')">
          <DeskTextarea v-model="form.notes" :rows="3" />
        </DeskField>
      </DeskSection>
    </DeskForm>
  </DeskPage>
</template>
