<script setup>
// Estimate Template detail — view / edit (modal) / delete + grouped rows grid.
// Rows point at an Assembly OR a Rate Master resource (pooled picker); the
// server derives uom + description and computes rate/amount/row_count/estimated_total.
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { useConfirm } from '@/composables/useConfirm'
import { useFormErrors } from '@/composables/useFormErrors'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { useDocTypeList } from '@/composables/useDocTypeList'
import { showToast } from '@/utils/appToast'
import { createDataAdapter } from '@/data/adapters'
import { fmtINR, fmtDate } from '@/utils/format'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'
import DeskSearchableSelect from '@/components/desk/DeskSearchableSelect.vue'

const GRID_COLS = 'minmax(200px, 1.2fr) 60px 90px 110px 120px 150px 130px 44px'

const props = defineProps({ id: String })
const router = useRouter()
const confirmDialog = useConfirm()
const { errors, applyServerErrors, setErrors } = useFormErrors({
  template_name: 'templateName',
})
const adapter = createDataAdapter(useDataStore())

const { selectOptions } = useDoctypeMeta('Estimate Template Row')
const costHeadOptions = computed(() => selectOptions('cost_head'))

const resource = adapter.read('Estimate Template', props.id, { fields: ['*'] })
const doc = computed(() => resource?.doc || null)

const breadcrumbs = computed(() => [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Estimate Template', to: '/estimate-template' },
  { label: doc.value?.template_name || props.id },
])

const assembliesRes = useDocTypeList('Assembly', {
  fields: ['name', 'assembly_name', 'category', 'rate_per_unit', 'uom'],
  filters: [['disabled', '=', 0]],
  orderBy: 'assembly_name asc',
  pageLength: 0,
  cache: 'buildsuite-assembly-options',
})
const rateMastersRes = useDocTypeList('Construction Rate Master', {
  fields: ['name', 'rate_name', 'category', 'current_rate', 'uom'],
  filters: [['disabled', '=', 0]],
  orderBy: 'category asc',
  pageLength: 0,
  cache: 'buildsuite-rate-master-options',
})

const assemblyMap = computed(() =>
  Object.fromEntries((assembliesRes.data || []).map((a) => [a.name, a])),
)
const rateMap = computed(() =>
  Object.fromEntries((rateMastersRes.data || []).map((r) => [r.name, r])),
)

// Prefix-encoded value: A:<assembly> / R:<rate master> — decoded in sourceToFields().
const sourceOptions = computed(() => {
  const out = []
  for (const a of assembliesRes.data || []) {
    out.push({
      value: `A:${a.name}`,
      label: `${a.name} · ${a.assembly_name}`,
      group: 'Assembly',
      hint: `${fmtINR(a.rate_per_unit)} per ${a.uom}`,
    })
  }
  for (const r of rateMastersRes.data || []) {
    out.push({
      value: `R:${r.name}`,
      label: `${r.name} · ${r.rate_name}`,
      group: r.category,
      hint: `${fmtINR(r.current_rate)} per ${r.uom}`,
    })
  }
  return out
})

const rawRows = computed(() => doc.value?.rows || [])

function decorate(row) {
  let unit = row.uom || ''
  let liveRate = 0
  let sourceLabel = ''
  let sourceKind = ''
  if (row.line_type === 'Assembly') {
    const a = assemblyMap.value[row.assembly]
    sourceKind = 'Assembly'
    if (a) { unit = unit || a.uom; liveRate = a.rate_per_unit || 0; sourceLabel = a.assembly_name }
  } else if (row.line_type === 'Resource') {
    const r = rateMap.value[row.resource]
    sourceKind = 'Rate Master'
    if (r) { unit = unit || r.uom; liveRate = r.current_rate || 0; sourceLabel = r.rate_name }
  }
  const qty = Number(row.placeholder_qty) || 0
  // Prefer the stored (server-computed) rate/amount; fall back to a live resolve
  // from the linked record (e.g. before the first save).
  const rate = (Number(row.rate) || 0) || liveRate
  const amount = (Number(row.amount) || 0) || qty * rate
  return {
    ...row,
    unit,
    rate,
    qty,
    amount,
    sourceLabel: sourceLabel || row.description || row.assembly || row.resource || '—',
    sourceKind,
  }
}

const previewRows = computed(() => rawRows.value.map(decorate))
const estimatedTotal = computed(() => previewRows.value.reduce((sum, r) => sum + r.amount, 0))

const groupedRows = computed(() => {
  const groups = new Map()
  for (const row of previewRows.value) {
    const key = (row.group_name || '').trim() || '__ungrouped__'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(row)
  }
  return Array.from(groups.entries()).map(([key, rows]) => ({
    key,
    name: key === '__ungrouped__' ? 'Ungrouped' : key,
    rows,
    count: rows.length,
    subtotal: rows.reduce((acc, r) => acc + r.amount, 0),
  }))
})

const groupOptions = computed(() => {
  const seen = new Set()
  for (const r of rawRows.value) {
    const g = (r.group_name || '').trim()
    if (g) seen.add(g)
  }
  return Array.from(seen).sort()
})

const cards = computed(() => {
  const d = doc.value
  if (!d) return []
  return [
    { label: 'Project Type', value: d.project_type || 'Any' },
    { label: 'Rows', value: rawRows.value.length, cls: 'tabular-nums' },
    { label: 'Estimated total', value: fmtINR(estimatedTotal.value), cls: 'tabular-nums font-semibold' },
    { label: 'Updated', value: fmtDate(d.modified), cls: 'text-xs' },
  ]
})

const editing = ref(false)
const saving = ref(false)
const form = ref({})
function snapshot() {
  const d = doc.value
  if (!d) return {}
  return {
    templateName: d.template_name || '',
    projectType: d.project_type || '',
    enabled: !!d.enabled,
    description: d.description || '',
  }
}
watch(doc, (v) => { if (v && !editing.value) form.value = snapshot() }, { immediate: true })

function startEdit() {
  form.value = snapshot()
  setErrors({})
  editing.value = true
}
function cancelEdit() { editing.value = false }
function validate() {
  const e = {}
  if (!form.value.templateName?.trim()) e.templateName = 'Name is required'
  setErrors(e)
  return Object.keys(e).length === 0
}
async function saveEdit() {
  if (!validate()) return
  saving.value = true
  try {
    await adapter.update('Estimate Template', props.id, {
      template_name: form.value.templateName.trim(),
      project_type: form.value.projectType || null,
      enabled: form.value.enabled ? 1 : 0,
      description: form.value.description,
    })
    resource?.reload?.()
    editing.value = false
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update template', 'error')
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  const ok = await confirmDialog({
    title: 'Delete estimate template',
    message: `Delete "${doc.value?.template_name}" (${doc.value?.template_code})? This cannot be undone.`,
    confirmLabel: 'Delete',
    destructive: true,
  })
  if (!ok) return
  try {
    await adapter.remove('Estimate Template', props.id)
    router.push('/estimate-template')
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to delete template', 'error')
  }
}

const savingRows = ref(false)
// addingRow: '' = none; a group key = add into that group; '__new__' = new group.
const addingRow = ref('')
const newRow = reactive({ source: '', group_name: '', placeholder_qty: 1, cost_head: '', description: '' })

const newRowSource = computed(() => {
  if (!newRow.source) return null
  if (newRow.source.startsWith('A:')) {
    const a = assemblyMap.value[newRow.source.slice(2)]
    return a ? { unit: a.uom, rate: a.rate_per_unit, kind: 'Assembly' } : null
  }
  const r = rateMap.value[newRow.source.slice(2)]
  return r ? { unit: r.uom, rate: r.current_rate, kind: 'Resource' } : null
})
const newRowAmount = computed(() => (Number(newRow.placeholder_qty) || 0) * (newRowSource.value?.rate || 0))

// Keep each child `name` so Frappe updates rows in place; omit uom (server derives it).
function currentRows() {
  return rawRows.value.map((r) => ({
    name: r.name,
    line_type: r.line_type,
    assembly: r.assembly || null,
    resource: r.resource || null,
    group_name: r.group_name || '',
    placeholder_qty: r.placeholder_qty || 0,
    cost_head: r.cost_head || '',
    description: r.description || '',
  }))
}

async function persistRows(next) {
  savingRows.value = true
  try {
    await adapter.update('Estimate Template', props.id, { rows: next })
    await resource?.reload?.()
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to update rows', 'error')
  } finally {
    savingRows.value = false
  }
}

// Edit by child `name` — grouping reorders rows, so the index isn't stable.
function patchRowByName(name, field, value) {
  const next = currentRows()
  const target = next.find((r) => r.name === name)
  if (!target) return
  target[field] = field === 'placeholder_qty' ? (Number(value) || 0) : value
  persistRows(next)
}

// Decode the prefix-encoded source into backend line_type + the right link.
function sourceToFields(source) {
  if (source.startsWith('A:')) return { line_type: 'Assembly', assembly: source.slice(2), resource: null }
  return { line_type: 'Resource', resource: source.slice(2), assembly: null }
}

function startAddRow(groupKey = '') {
  Object.assign(newRow, {
    source: '',
    group_name: '',
    placeholder_qty: 1,
    cost_head: '',
    description: '',
  })
  addingRow.value = groupKey || '__new__'
}
function cancelAddRow() { addingRow.value = '' }

async function saveAddRow() {
  if (!newRow.source || (Number(newRow.placeholder_qty) || 0) < 0) return
  await persistRows([
    ...currentRows(),
    {
      ...sourceToFields(newRow.source),
      group_name: newRow.group_name,
      placeholder_qty: Number(newRow.placeholder_qty) || 0,
      cost_head: newRow.cost_head,
      description: newRow.description,
    },
  ])
  cancelAddRow()
}

async function removeRow(name) {
  const ok = await confirmDialog({
    title: 'Remove row',
    message: 'Remove this line from the template?',
    confirmLabel: 'Remove',
    destructive: true,
  })
  if (!ok) return
  persistRows(currentRows().filter((r) => r.name !== name))
}
</script>

<template>
  <DeskPage v-if="doc" :title="doc.template_name" :subtitle="doc.template_code"
    :breadcrumbs="breadcrumbs" :status="doc.enabled ? 'Enabled' : 'Disabled'">
    <template #actions>
      <button type="button" class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
        style="border-radius: 6px;" @click="startEdit">Edit</button>
      <button type="button"
        class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
        style="border-radius: 6px;" @click="onDelete">Delete</button>
    </template>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
      <div v-for="c in cards" :key="c.label" class="bg-white border border-ink-200 px-3 py-2"
        style="border-radius: 6px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ c.label }}</div>
        <div class="text-sm text-ink-900 mt-0.5" :class="c.cls">{{ c.value }}</div>
      </div>
    </div>

    <div v-if="doc.description" class="mb-4 px-3 py-2 bg-white border border-ink-200" style="border-radius: 6px;">
      <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Description</div>
      <div class="text-sm text-ink-800 leading-snug whitespace-pre-line">{{ doc.description }}</div>
    </div>

    <section>
      <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium border-t border-ink-200 pt-3 mb-1">
        Template rows
      </div>
      <div class="text-[11px] text-ink-500 mb-2">
        Rows seeded onto a BOQ when this template is imported. Assembly-driven rows auto-explode into snapshot sub-items.
      </div>

      <div class="border border-ink-200 overflow-x-auto" style="border-radius: 8px;">
        <div style="min-width: 920px;">
          <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
            :style="{ gridTemplateColumns: GRID_COLS }">
            <div class="px-3 py-1.5">Source</div>
            <div class="px-2 py-1.5">Unit</div>
            <div class="px-2 py-1.5 text-right">Qty</div>
            <div class="px-2 py-1.5 text-right">Rate</div>
            <div class="px-2 py-1.5 text-right">Amount</div>
            <div class="px-2 py-1.5">Group</div>
            <div class="px-2 py-1.5">Cost head</div>
            <div class="px-2 py-1.5"></div>
          </div>

          <template v-if="groupedRows.length">
            <template v-for="group in groupedRows" :key="group.key">
              <div class="grid items-center bg-ink-50 border-b border-ink-200 border-t border-t-ink-200 first:border-t-0"
                :style="{ gridTemplateColumns: GRID_COLS }">
                <div class="px-3 py-2 text-sm font-semibold text-ink-900" style="grid-column: 1 / span 4;">
                  {{ group.name }}
                  <span class="ml-2 text-[11px] text-ink-500 font-normal">· {{ group.count }} row{{ group.count === 1 ? '' : 's' }}</span>
                </div>
                <div class="px-2 py-2 text-right text-[11px] uppercase tracking-wider text-ink-500 font-medium" style="grid-column: 5 / span 1;">Subtotal</div>
                <div class="px-2 py-2 tabular-nums font-semibold text-ink-900" style="grid-column: 6 / span 3;">{{ fmtINR(group.subtotal) }}</div>
              </div>

              <div class="divide-y divide-ink-100">
                <div v-for="row in group.rows" :key="row.name"
                  class="grid items-center text-sm hover:bg-brand-50/40 transition-colors"
                  :style="{ gridTemplateColumns: GRID_COLS }">
                  <div class="px-3 py-1.5 min-w-0">
                    <div class="text-ink-900 font-medium truncate">{{ row.sourceLabel }}</div>
                    <span class="text-[9px] px-1 py-0.5 font-medium uppercase tracking-wider"
                      :class="row.sourceKind === 'Assembly' ? 'bg-brand-50 text-brand-700' : 'bg-ink-100 text-ink-600'"
                      style="border-radius: 2px;">{{ row.sourceKind || '—' }}</span>
                  </div>
                  <div class="px-2 py-1.5 text-xs text-ink-700">{{ row.unit || '—' }}</div>
                  <div class="px-2 py-1">
                    <input type="number" class="desk-input" :value="row.placeholder_qty" :min="0" step="0.01"
                      :disabled="savingRows" @change="patchRowByName(row.name, 'placeholder_qty', $event.target.value)" />
                  </div>
                  <div class="px-2 py-1.5 text-right tabular-nums text-ink-700">{{ fmtINR(row.rate) }}</div>
                  <div class="px-2 py-1.5 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(row.amount) }}</div>
                  <div class="px-2 py-1">
                    <input type="text" class="desk-input" :value="row.group_name" placeholder="Group"
                      list="template-group-options" :disabled="savingRows"
                      @change="patchRowByName(row.name, 'group_name', $event.target.value)" />
                  </div>
                  <div class="px-2 py-1">
                    <DeskSelect :model-value="row.cost_head" :disabled="savingRows"
                      @update:model-value="(v) => patchRowByName(row.name, 'cost_head', v)">
                      <option value="">—</option>
                      <option v-for="c in costHeadOptions" :key="c">{{ c }}</option>
                    </DeskSelect>
                  </div>
                  <div class="px-2 py-1 text-right">
                    <button type="button" class="text-ink-400 hover:text-danger-700 text-base leading-none" title="Remove"
                      :disabled="savingRows" @click="removeRow(row.name)">×</button>
                  </div>
                </div>
              </div>

              <template v-if="addingRow === group.key">
                <div class="grid items-start text-sm border-t border-ink-200 bg-brand-50"
                  :style="{ gridTemplateColumns: GRID_COLS }">
                  <div class="px-2 py-2">
                    <DeskSearchableSelect v-model="newRow.source" :options="sourceOptions"
                      placeholder="Pick a source…" search-placeholder="Search assemblies / rate master…" />
                  </div>
                  <div class="px-2 py-2 text-[11px] text-ink-500">{{ newRowSource?.unit || 'auto' }}</div>
                  <div class="px-2 py-2"><DeskInput v-model="newRow.placeholder_qty" type="number" :min="0" :step="0.01" /></div>
                  <div class="px-2 py-2 text-right text-[11px] text-ink-500">{{ newRowSource ? fmtINR(newRowSource.rate) : 'auto' }}</div>
                  <div class="px-2 py-2 text-right text-[11px] tabular-nums" :class="newRowSource ? 'text-ink-900 font-medium' : 'text-ink-500'">{{ newRowSource ? fmtINR(newRowAmount) : 'auto' }}</div>
                  <div class="px-2 py-2"><DeskInput v-model="newRow.group_name" placeholder="Group" /></div>
                  <div class="px-2 py-2">
                    <DeskSelect v-model="newRow.cost_head">
                      <option value="">—</option>
                      <option v-for="c in costHeadOptions" :key="c">{{ c }}</option>
                    </DeskSelect>
                  </div>
                  <div></div>
                </div>
                <div class="bg-brand-50 border-b border-ink-200 px-3 pb-2 flex items-center justify-end gap-2">
                  <button type="button" class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700" style="border-radius: 6px;" @click="cancelAddRow">Cancel</button>
                  <button type="button" class="desk-save-btn !text-xs" :disabled="savingRows" @click="saveAddRow">+ Add row</button>
                </div>
              </template>

              <div v-if="addingRow !== group.key" class="border-t border-ink-100 px-3 py-1.5 bg-white">
                <button type="button" class="text-[11px] text-ink-500 hover:text-brand-700" @click="startAddRow(group.key)">+ Add to "{{ group.name }}"</button>
              </div>
            </template>
          </template>

          <template v-if="addingRow === '__new__'">
            <div class="grid items-start text-sm border-t border-ink-200 bg-brand-50"
              :style="{ gridTemplateColumns: GRID_COLS }">
              <div class="px-2 py-2">
                <DeskSearchableSelect v-model="newRow.source" :options="sourceOptions"
                  placeholder="Pick a source…" search-placeholder="Search assemblies / rate master…" />
              </div>
              <div class="px-2 py-2 text-[11px] text-ink-500">{{ newRowSource?.unit || 'auto' }}</div>
              <div class="px-2 py-2"><DeskInput v-model="newRow.placeholder_qty" type="number" :min="0" :step="0.01" /></div>
              <div class="px-2 py-2 text-right text-[11px] text-ink-500">{{ newRowSource ? fmtINR(newRowSource.rate) : 'auto' }}</div>
              <div class="px-2 py-2 text-right text-[11px] tabular-nums" :class="newRowSource ? 'text-ink-900 font-medium' : 'text-ink-500'">{{ newRowSource ? fmtINR(newRowAmount) : 'auto' }}</div>
              <div class="px-2 py-2"><DeskInput v-model="newRow.group_name" placeholder="New group name…" /></div>
              <div class="px-2 py-2">
                <DeskSelect v-model="newRow.cost_head">
                  <option value="">—</option>
                  <option v-for="c in costHeadOptions" :key="c">{{ c }}</option>
                </DeskSelect>
              </div>
              <div></div>
            </div>
            <div class="bg-brand-50 border-b border-ink-200 px-3 pb-2 flex items-center justify-end gap-2">
              <button type="button" class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700" style="border-radius: 6px;" @click="cancelAddRow">Cancel</button>
              <button type="button" class="desk-save-btn !text-xs" :disabled="savingRows" @click="saveAddRow">+ Add row</button>
            </div>
          </template>

          <div v-if="!rawRows.length && !addingRow" class="py-6 text-center text-xs text-ink-500 italic">
            No rows yet — click "+ Add row in new group" below to start.
          </div>

          <div class="grid items-center bg-ink-50 border-t border-ink-200 text-xs"
            :style="{ gridTemplateColumns: GRID_COLS }">
            <div class="px-3 py-2 text-[11px] uppercase tracking-wider text-ink-700 font-semibold" style="grid-column: 1 / span 4;">Estimated total</div>
            <div class="px-2 py-2 text-right text-[11px] uppercase tracking-wider text-ink-500 font-medium" style="grid-column: 5 / span 1;">Grand total</div>
            <div class="px-2 py-2 tabular-nums font-semibold text-ink-900 text-sm" style="grid-column: 6 / span 3;">{{ fmtINR(estimatedTotal) }}</div>
          </div>

          <div v-if="addingRow !== '__new__'" class="border-t border-ink-200 px-3 py-2 bg-white">
            <button type="button" class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700" style="border-radius: 6px;" @click="startAddRow('__new__')">+ Add row in new group</button>
          </div>
        </div>
      </div>

      <datalist id="template-group-options">
        <option v-for="g in groupOptions" :key="g" :value="g" />
      </datalist>

      <p class="text-[11px] text-ink-400 mt-2">
        Rate &amp; amount are a live preview from current Assembly / Rate Master rates. Importing this template
        into a BOQ stamps its own snapshot.
      </p>
    </section>

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
              <h2 class="text-sm font-semibold text-ink-900">Edit template</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ doc.template_name }}</p>
            </div>
            <button type="button" class="text-ink-500 hover:text-ink-900 text-lg leading-none" aria-label="Close" @click="cancelEdit">×</button>
          </header>

          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Basic">
              <DeskField label="Code" hint="The template's identifier — not editable.">
                <span class="text-sm font-mono text-ink-700">{{ doc.template_code }}</span>
              </DeskField>
              <DeskField label="Name" required :error="errors.templateName">
                <DeskInput v-model="form.templateName" />
              </DeskField>
              <DeskField label="Project Type tag" hint="Empty = universal.">
                <DeskLinkPicker v-model="form.projectType" doctype="Project Type" label-field="name" value-field="name"
                  placeholder="— Universal —" />
              </DeskField>
              <DeskField label="Enabled">
                <label class="inline-flex items-center gap-2 text-sm text-ink-800">
                  <input type="checkbox" v-model="form.enabled" />
                  <span>Available in pickers</span>
                </label>
              </DeskField>
              <DeskField label="Description">
                <DeskTextarea v-model="form.description" :rows="3" />
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

  <div v-else class="px-3 py-2 text-sm text-ink-500">Loading estimate template…</div>
</template>
