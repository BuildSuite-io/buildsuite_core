<script setup>
// Assembly detail — view / edit (modal) / delete + components child-table grid.

import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { useConfirm } from '@/composables/useConfirm'
import { useFormErrors } from '@/composables/useFormErrors'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { useDocTypeList } from '@/composables/useDocTypeList'
import { showToast } from '@/utils/appToast'
import { createDataAdapter } from '@/data/adapters'
import { fmtINR } from '@/utils/format'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'
import DeskSearchableSelect from '@/components/desk/DeskSearchableSelect.vue'
import DeskLink from '@/components/desk/DeskLink.vue'

const props = defineProps({ id: String })
const router = useRouter()
const confirmDialog = useConfirm()
const { errors, applyServerErrors, setErrors } = useFormErrors({
  assembly_name: 'assemblyName',
  uom: 'uom',
})
const adapter = createDataAdapter(useDataStore())

const { selectOptions } = useDoctypeMeta('Assembly')
const categoryOptions = computed(() => selectOptions('category'))

const resource = adapter.read('Assembly', props.id, { fields: ['*'] })
const doc = computed(() => resource?.doc || null)

const breadcrumbs = computed(() => [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Assembly', to: '/assembly' },
  { label: doc.value?.assembly_name || props.id },
])

const cards = computed(() => {
  const d = doc.value
  if (!d) return []
  return [
    { label: 'Code', value: d.assembly_code, cls: 'font-mono' },
    { label: 'Category', value: d.category || '—' },
    { label: 'Unit', value: d.uom },
    { label: 'Rate / unit (live)', value: fmtINR(d.rate_per_unit), cls: 'font-medium tabular-nums' },
  ]
})

const editing = ref(false)
const saving = ref(false)
const form = ref({})

function snapshot() {
  const d = doc.value
  if (!d) return {}
  return {
    assemblyName: d.assembly_name || '',
    category: d.category || '',
    uom: d.uom || '',
    notes: d.notes || '',
  }
}
watch(doc, (v) => { if (v && !editing.value) form.value = snapshot() }, { immediate: true })

function startEdit() {
  form.value = snapshot()
  setErrors({})
  editing.value = true
}
function cancelEdit() {
  editing.value = false
}
function validate() {
  const e = {}
  if (!form.value.assemblyName?.trim()) e.assemblyName = 'Name is required'
  if (!form.value.uom) e.uom = 'Unit is required'
  setErrors(e)
  return Object.keys(e).length === 0
}
async function saveEdit() {
  if (!validate()) return
  saving.value = true
  try {
    await adapter.update('Assembly', props.id, {
      assembly_name: form.value.assemblyName.trim(),
      category: form.value.category,
      uom: form.value.uom,
      notes: form.value.notes,
    })
    resource?.reload?.()
    editing.value = false
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update assembly', 'error')
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  const ok = await confirmDialog({
    title: 'Delete assembly',
    message: `Delete "${doc.value?.assembly_name}" (${doc.value?.assembly_code})? This cannot be undone.`,
    confirmLabel: 'Delete',
    destructive: true,
  })
  if (!ok) return
  try {
    await adapter.remove('Assembly', props.id)
    router.push('/assembly')
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to delete assembly', 'error')
  }
}

// Components child table. We send only resource + coefficient; the server
// computes rate / amount / rate_per_unit / component_count on save.
const components = computed(() => doc.value?.components || [])
const savingComponents = ref(false)
const addingRow = ref(false)
const newRow = reactive({ resource: '', coefficient: 1, remarks: '' })

// Rate-master options for the picker — grouped by category, rate as a hint.
const rateMastersRes = useDocTypeList('Construction Rate Master', {
  fields: ['name', 'rate_name', 'category', 'current_rate', 'uom'],
  filters: [['disabled', '=', 0]],
  orderBy: 'category asc',
  pageLength: 0,
  cache: 'buildsuite-rate-master-options',
})
const rateMasterOptions = computed(() =>
  (rateMastersRes.data || []).map((r) => ({
    value: r.name,
    label: `${r.name} · ${r.rate_name}`,
    group: r.category,
    hint: `${fmtINR(r.current_rate)} per ${r.uom}`,
  })),
)

// Add-row preview — unit/rate from the picked resource (server recomputes on save).
const newRowResource = computed(() =>
  (rateMastersRes.data || []).find((r) => r.name === newRow.resource) || null,
)
const newRowAmount = computed(() => (Number(newRow.coefficient) || 0) * (newRowResource.value?.current_rate || 0))

// Keep each child `name` so Frappe updates rows in place, not delete + recreate.
function currentRows() {
  return components.value.map((r) => ({
    name: r.name,
    resource: r.resource,
    coefficient: r.coefficient,
    remarks: r.remarks || '',
  }))
}

async function persistComponents(rows) {
  savingComponents.value = true
  try {
    await adapter.update('Assembly', props.id, { components: rows })
    await resource?.reload?.()
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update components', 'error')
  } finally {
    savingComponents.value = false
  }
}

function startAddRow() {
  Object.assign(newRow, { resource: '', coefficient: 1, remarks: '' })
  addingRow.value = true
}
function cancelAddRow() { addingRow.value = false }
async function saveAddRow() {
  if (!newRow.resource || (Number(newRow.coefficient) || 0) < 0) return
  await persistComponents([
    ...currentRows(),
    { resource: newRow.resource, coefficient: Number(newRow.coefficient) || 0, remarks: newRow.remarks },
  ])
  cancelAddRow()
}

function changeCoefficient(index, value) {
  const rows = currentRows()
  if (!rows[index]) return
  rows[index].coefficient = Number(value) || 0
  persistComponents(rows)
}

async function removeComponent(index) {
  const ok = await confirmDialog({
    title: 'Remove component',
    message: 'Remove this component from the assembly?',
    confirmLabel: 'Remove',
    destructive: true,
  })
  if (!ok) return
  const rows = currentRows().filter((_, i) => i !== index)
  persistComponents(rows)
}
</script>

<template>
  <DeskPage v-if="doc" :title="doc.assembly_name" :subtitle="`${doc.assembly_code} · per ${doc.uom}`"
    :breadcrumbs="breadcrumbs" :status="doc.category">
    <template #actions>
      <button type="button" class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
        style="border-radius: 6px;" @click="startEdit">Edit</button>
      <button type="button"
        class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
        style="border-radius: 6px;" @click="onDelete">Delete</button>
    </template>

    <!-- Headline strip — code / category / unit / rate -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
      <div v-for="c in cards" :key="c.label" class="bg-white border border-ink-200 px-3 py-2"
        style="border-radius: 6px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ c.label }}</div>
        <div class="text-sm text-ink-900 mt-0.5" :class="c.cls">{{ c.value }}</div>
      </div>
    </div>

    <!-- Notes -->
    <div v-if="doc.notes" class="mb-4 px-3 py-2 bg-white border border-ink-200" style="border-radius: 6px;">
      <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Notes</div>
      <div class="text-sm text-ink-800 leading-snug whitespace-pre-line">{{ doc.notes }}</div>
    </div>

    <!-- Components child table -->
    <section>
      <div class="flex items-center justify-between mb-2 gap-3">
        <div class="text-xs text-ink-500">
          <span class="text-ink-900 font-medium">{{ components.length }} component{{ components.length === 1 ? '' : 's' }}</span>
          · linked to Rate Master · coefficient × rate
        </div>
        <button v-if="!addingRow" type="button" class="desk-save-btn" :disabled="savingComponents" @click="startAddRow">+ Add Component</button>
      </div>

      <div class="bg-white border border-ink-200" style="border-radius: 8px;">
        <!-- Header strip -->
        <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
          style="grid-template-columns: minmax(260px, 1fr) 110px 60px 110px 110px 60px;">
          <div class="px-3 py-1.5">Resource</div>
          <div class="px-3 py-1.5 text-right whitespace-nowrap">Coefficient</div>
          <div class="px-3 py-1.5">Unit</div>
          <div class="px-3 py-1.5 text-right whitespace-nowrap">Rate</div>
          <div class="px-3 py-1.5 text-right whitespace-nowrap">Amount</div>
          <div class="px-3 py-1.5"></div>
        </div>

        <!-- Existing rows -->
        <div v-for="(row, i) in components" :key="row.name || i"
          class="grid border-b border-ink-100 last:border-b-0 items-center text-sm"
          style="grid-template-columns: minmax(260px, 1fr) 110px 60px 110px 110px 60px;">
          <div class="px-3 py-2">
            <DeskLink :to="`/rate-master`" class="text-xs">{{ row.resource_name || row.resource }}</DeskLink>
            <div v-if="row.remarks" class="text-[11px] text-ink-500 mt-0.5">{{ row.remarks }}</div>
          </div>
          <div class="px-2 py-1">
            <DeskInput :model-value="row.coefficient" type="number" :min="0" :step="0.01"
              :disabled="savingComponents" @change="(e) => changeCoefficient(i, e.target.value)" />
          </div>
          <div class="px-3 py-2 text-xs text-ink-700">{{ row.uom || '—' }}</div>
          <div class="px-3 py-2 text-right text-sm tabular-nums text-ink-700">{{ fmtINR(row.rate) }}</div>
          <div class="px-3 py-2 text-right text-sm font-medium tabular-nums text-ink-900">{{ fmtINR(row.amount) }}</div>
          <div class="px-2 py-1 text-right">
            <button type="button" class="text-ink-400 hover:text-danger-700 text-base leading-none" title="Remove"
              :disabled="savingComponents" @click="removeComponent(i)">×</button>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!components.length && !addingRow" class="px-3 py-4 text-xs text-ink-500">
          No components yet — add one to price this assembly.
        </div>

        <!-- Add row -->
        <div v-if="addingRow" class="grid border-t border-ink-200 items-start text-sm bg-brand-50"
          style="grid-template-columns: minmax(260px, 1fr) 110px 60px 110px 110px 60px;">
          <div class="px-2 py-2">
            <DeskSearchableSelect v-model="newRow.resource" :options="rateMasterOptions"
              placeholder="Pick a rate master…" search-placeholder="Search rate master…" />
            <div class="mt-1">
              <DeskInput v-model="newRow.remarks" placeholder="Remarks (optional)" />
            </div>
          </div>
          <div class="px-2 py-2">
            <DeskInput v-model="newRow.coefficient" type="number" :min="0" :step="0.01" />
          </div>
          <div class="px-3 py-2 text-xs text-ink-700">{{ newRowResource?.uom || '—' }}</div>
          <div class="px-3 py-2 text-right text-sm tabular-nums text-ink-700">
            {{ newRowResource ? fmtINR(newRowResource.current_rate) : '— auto —' }}
          </div>
          <div class="px-3 py-2 text-right text-sm font-medium tabular-nums text-ink-900">
            {{ newRowResource ? fmtINR(newRowAmount) : '— auto —' }}
          </div>
          <div class="px-2 py-2 flex items-center gap-1 justify-end">
            <button type="button" class="desk-save-btn !px-2 !py-1 !text-[11px]" :disabled="savingComponents" @click="saveAddRow">Add</button>
            <button type="button" class="text-ink-400 hover:text-danger-700 text-base leading-none" @click="cancelAddRow">×</button>
          </div>
        </div>

        <!-- Footer total -->
        <div class="grid border-t border-ink-200 bg-ink-50 text-sm"
          style="grid-template-columns: minmax(260px, 1fr) 110px 60px 110px 110px 60px;">
          <div class="px-3 py-2 text-right text-[11px] uppercase tracking-wider text-ink-500 font-medium" style="grid-column: 1 / span 4;">Rate / unit (Assembly)</div>
          <div class="px-3 py-2 text-right font-semibold text-ink-900 tabular-nums">{{ fmtINR(doc.rate_per_unit) }}</div>
          <div></div>
        </div>
      </div>
    </section>

    <!-- Edit modal -->
    <Teleport to="body">
      <div
        v-if="editing"
        class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
        @click.self="cancelEdit"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
          style="border-radius: 12px; max-height: calc(100vh - 3rem);"
          @click.stop
        >
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900">Edit assembly</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ doc.assembly_name }}</p>
            </div>
            <button type="button" class="text-ink-500 hover:text-ink-900 text-lg leading-none" aria-label="Close" @click="cancelEdit">×</button>
          </header>

          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Assembly details">
              <DeskField label="Code" hint="The assembly's identifier — not editable.">
                <span class="text-sm font-mono text-ink-700">{{ doc.assembly_code }}</span>
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
          </div>

          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
            <button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700" style="border-radius: 6px;" :disabled="saving" @click="cancelEdit">Cancel</button>
            <button type="button" class="desk-save-btn" :disabled="saving" @click="saveEdit">{{ saving ? 'Saving…' : 'Save' }}</button>
          </footer>
        </div>
      </div>
    </Teleport>
  </DeskPage>

  <div v-else class="px-3 py-2 text-sm text-ink-500">Loading assembly…</div>
</template>
