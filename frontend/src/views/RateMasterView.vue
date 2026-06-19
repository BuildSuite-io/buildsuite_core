<script setup>

import { computed, ref } from 'vue'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import { useDocTypeList } from '@/composables/useDocTypeList'
import { useDoctypeMeta } from '@/composables/useDoctypeMeta'
import { useConfirm } from '@/composables/useConfirm'
import { parseFrappeError } from '@/utils/frappeError'
import { showToast } from '@/utils/appToast'
import { fmtINR, fmtDate } from '@/utils/format'
import FrappeUserBadge from '@/components/FrappeUserBadge.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'

const store = useDataStore()
const adapter = createDataAdapter(store)
const confirmDialog = useConfirm()
const { selectOptions } = useDoctypeMeta('Construction Rate Master')

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Rate Master' },
]

// Fetch all rates once — feeds both the KPI cards and the table.
const ratesRes = useDocTypeList('Construction Rate Master', {
  fields: ['name', 'rate_code', 'rate_name', 'category', 'uom', 'current_rate', 'previous_rate', 'effective_date', 'modified_by'],
  orderBy: 'rate_code asc',
  pageLength: 0, // 0 = no limit, so counts cover every rate
  cache: 'buildsuite-rate-master-list',
  transform: (data) =>
    data.map((r) => ({
      id: r.name,
      code: r.rate_code,
      description: r.rate_name,
      category: r.category,
      unit: r.uom,
      currentRate: r.current_rate,
      previousRate: r.previous_rate,
      updatedAt: r.effective_date,
      updatedBy: r.modified_by,
    })),
})

const search = ref('')
const categoryFilter = ref('')
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const form = ref({ code: '', description: '', category: '', uom: '', currentRate: 0 })
const rateRes = ref(null)

const drawer = computed(() => rateRes.value?.doc || null)
const categoryOptions = computed(() => selectOptions('category'))
const kpis = computed(() => {
  const data = ratesRes.data || []
  const byCat = { Material: 0, Labour: 0, Equipment: 0 }
  data.forEach((r) => {
    if (r.category in byCat) byCat[r.category]++
  })
  return { total: data.length, ...byCat }
})
const kpiCards = computed(() => [
  { label: 'Total rates', value: kpis.value.total, color: 'text-ink-900' },
  { label: 'Materials', value: kpis.value.Material, color: 'text-blue-700' },
  { label: 'Labour', value: kpis.value.Labour, color: 'text-amber-700' },
  { label: 'Equipment', value: kpis.value.Equipment, color: 'text-violet-700' },
])
const rows = computed(() => {
  let data = ratesRes.data || []
  if (categoryFilter.value) data = data.filter((r) => r.category === categoryFilter.value)
  const q = search.value.trim().toLowerCase()
  if (q) {
    data = data.filter(
      (r) => (r.code || '').toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q),
    )
  }
  return data
})
const drawerHistory = computed(() => (drawer.value?.history || []).slice().reverse()) // latest first

const columns = [
  { key: 'code', label: 'Code' },
  { key: 'description', label: 'Description' },
  { key: 'category', label: 'Category' },
  { key: 'unit', label: 'UOM' },
  { key: 'currentRate', label: 'Current Rate', align: 'right' },
  { key: 'trend', label: 'Trend', align: 'center' },
  { key: 'updatedAt', label: 'Last Updated' },
]

// Last-change %: current vs the previous rate (denormalized on the record). Null until a rate changes.
function trend(row) {
  const prev = Number(row.previousRate)
  if (!prev) return null
  return { pct: ((row.currentRate - prev) / prev) * 100, up: row.currentRate > prev }
}

function categoryColor(c) {
  return {
    Material: 'bg-blue-50 text-blue-700',
    Labour: 'bg-amber-50 text-amber-700',
    Equipment: 'bg-violet-50 text-violet-700',
  }[c] || 'bg-ink-100 text-ink-600'
}

function startAdd() {
  form.value = { code: '', description: '', category: categoryOptions.value[0], uom: '', currentRate: 0 }
  formError.value = ''
  editing.value = 'new'
}
function cancel() {
  editing.value = null
}

async function save() {
  formError.value = ''
  if (editing.value === 'new' && !form.value.code.trim()) {
    formError.value = 'Code is required.'
    return
  }
  if (!form.value.description.trim()) {
    formError.value = 'Resource name is required.'
    return
  }
  if (!form.value.uom) {
    formError.value = 'UOM is required.'
    return
  }
  if (Number(form.value.currentRate) < 0) {
    formError.value = 'Current rate cannot be negative.'
    return
  }
  saving.value = true
  try {
    if (editing.value === 'new') {
      await adapter.create('Construction Rate Master', {
        rate_code: form.value.code.trim(),
        rate_name: form.value.description.trim(),
        category: form.value.category,
        uom: form.value.uom,
        current_rate: Number(form.value.currentRate),
      })
      showToast('Rate created')
    } else {
      await adapter.update('Construction Rate Master', editing.value.id, {
        rate_name: form.value.description.trim(),
        category: form.value.category,
        uom: form.value.uom,
        current_rate: Number(form.value.currentRate),
      })
      showToast('Rate updated')
      if (rateRes.value) rateRes.value.reload()
    }
    editing.value = null
    await ratesRes.reload()
  } catch (err) {
    formError.value = parseFrappeError(err).summary || 'Could not save the rate.'
  } finally {
    saving.value = false
  }
}

// Load the full doc (incl. rate_history) for the side sheet — the list payload omits child tables.
function onRowClick(row) {
  rateRes.value = adapter.read('Construction Rate Master', row.id, {
    transform: (docs) =>
      docs.map((d) => ({
        id: d.name,
        code: d.rate_code,
        description: d.rate_name,
        category: d.category,
        unit: d.uom,
        currentRate: d.current_rate,
        updatedAt: d.effective_date,
        updatedBy: d.modified_by,
        history: (d.rate_history || []).map((h) => ({
          id: h.name,
          rate: h.rate,
          effectiveFrom: h.effective_from,
          reason: h.reason,
          changedBy: h.changed_by,
        })),
      })),
  })
}
function closeDrawer() {
  rateRes.value = null
}

function editRate() {
  const target = drawer.value
  if (!target) return
  form.value = {
    code: target.code,
    description: target.description,
    category: target.category,
    uom: target.unit,
    currentRate: target.currentRate,
  }
  formError.value = ''
  editing.value = target
}

async function removeRate() {
  const target = drawer.value
  if (!target) return
  const ok = await confirmDialog({
    title: 'Delete rate',
    message: `Delete ${target.code}? This also removes its rate history.`,
    confirmLabel: 'Delete',
    destructive: true,
  })
  if (!ok) return
  try {
    await adapter.remove('Construction Rate Master', target.id)
    showToast('Rate deleted')
    closeDrawer()
    await ratesRes.reload()
  } catch (err) {
    showToast(parseFrappeError(err).summary || 'Could not delete the rate.', 'error')
  }
}

</script>

<template>
  <DeskPage title="Construction Rate Master" :breadcrumbs="breadcrumbs">
    <template #actions>
      <button type="button" class="desk-save-btn" @click="startAdd">+ New rate</button>
    </template>

    <!-- KPI cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
      <div v-for="c in kpiCards" :key="c.label" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ c.label }}</div>
        <div class="text-base font-semibold mt-0.5" :class="c.color">{{ c.value }}</div>
      </div>
    </div>


    <DeskList v-model="search" :rows="rows" :columns="columns" row-key="id"
      search-placeholder="Search code or description…" @row-click="onRowClick">
      <template #filter-chips>
        <DeskSelect v-if="!categoryFilter" v-model="categoryFilter" class="!w-40">
          <option value="">Category: Any</option>
          <option v-for="c in categoryOptions" :key="c">{{ c }}</option>
        </DeskSelect>
        <DeskFilterChip v-else label="Category" :value="categoryFilter" @remove="categoryFilter = ''" />
      </template>

      <template #cell-code="{ row }">
        <DeskLink class="font-mono text-xs" @click.stop="onRowClick(row)">{{ row.code }}</DeskLink>
      </template>
      <template #cell-description="{ row }">
        <span class="text-ink-800 text-xs">{{ row.description }}</span>
      </template>
      <template #cell-category="{ row }">
        <span :class="['text-[10px] px-1.5 py-0.5 font-medium', categoryColor(row.category)]"
          style="border-radius: 2px;">{{ row.category }}</span>
      </template>
      <template #cell-unit="{ row }">
        <span class="text-ink-600 text-xs">{{ row.unit }}</span>
      </template>
      <template #cell-currentRate="{ row }">
        <span class="tabular-nums text-ink-900 font-medium">{{ fmtINR(row.currentRate) }}</span>
      </template>
      <template #cell-trend="{ row }">
        <span v-if="trend(row)" class="text-[11px] tabular-nums font-medium"
          :class="trend(row).up ? 'text-danger-700' : 'text-success-700'">
          {{ trend(row).up ? '▲' : '▼' }} {{ Math.abs(trend(row).pct).toFixed(1) }}%
        </span>
        <span v-else class="text-ink-300">—</span>
      </template>

      <template #cell-updatedAt="{ row }">
        <div class="flex items-center gap-1 text-xs text-ink-500">
          <FrappeUserBadge :user-id="row.updatedBy" :show-name="false" size="xs" />
          <span>{{ fmtDate(row.updatedAt) }}</span>
        </div>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          {{ ratesRes.loading ? 'Loading rates…' : 'No rates match your filters.' }}
        </div>
      </template>
    </DeskList>

    <!-- New / edit modal -->
    <div v-if="editing" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4" @click="cancel">
      <div class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md" style="border-radius: 2px;" @click.stop>
        <div class="px-4 py-3 border-b border-ink-200 flex items-center">
          <h2 class="text-sm font-semibold text-ink-900">
            {{ editing === 'new' ? 'New rate' : `Edit rate · ${editing.code}` }}
          </h2>
          <button type="button" @click="cancel" class="ml-auto text-ink-400 hover:text-ink-900"
            aria-label="Close">✕</button>
        </div>
        <div class="p-4 space-y-3">
          <div v-if="formError" class="px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700"
            style="border-radius: 6px;">
            {{ formError }}
          </div>
          <div class="grid grid-cols-2 gap-3">
            <DeskField label="Code" required>
              <DeskInput v-model="form.code" :disabled="editing !== 'new'" placeholder="e.g. CEM-OPC53"
                @input="formError = ''" />
            </DeskField>
            <DeskField label="Category">
              <DeskSelect v-model="form.category">
                <option v-for="c in categoryOptions" :key="c">{{ c }}</option>
              </DeskSelect>
            </DeskField>
          </div>
          <DeskField label="Description" required>
            <DeskInput v-model="form.description" placeholder="Cement — OPC 53 Grade" @input="formError = ''" />
          </DeskField>
          <div class="grid grid-cols-2 gap-3">
            <DeskField label="UOM" required>
              <DeskLinkPicker v-model="form.uom" doctype="UOM" label-field="name" value-field="name"
                placeholder="— Select UOM —" @change="formError = ''" />
            </DeskField>
            <DeskField label="Current rate (₹)" required>
              <DeskInput v-model.number="form.currentRate" type="number" @input="formError = ''" />
            </DeskField>
          </div>
          <DeskField label="Source"
            hint="Manual edits stamp 'Manual'. Rate updates triggered from an approved Purchase Order will stamp the PO number automatically — that flow lives on the PO page.">
            <DeskInput :model-value="'Manual'" disabled />
          </DeskField>
        </div>
        <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
          <button type="button" :disabled="saving" @click="cancel"
            class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1">Cancel</button>
          <button type="button" :disabled="saving" @click="save" class="desk-save-btn">
            {{ saving ? 'Saving…' : editing === 'new' ? 'Create rate' : 'Save changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- History side sheet -->
    <div v-if="rateRes" class="fixed inset-0 bg-ink-900/30 z-30 flex justify-end" @click="closeDrawer">
      <div class="w-96 h-full bg-white border-l border-ink-200 shadow-fp-lg flex flex-col" @click.stop>
        <div v-if="!drawer" class="flex-1 flex items-center justify-center text-sm text-ink-500">Loading…</div>
        <template v-else>
          <div class="px-4 py-3 border-b border-ink-200">
            <div class="flex items-center gap-2">
              <span class="font-mono text-xs text-brand-700">{{ drawer.code }}</span>
              <span :class="['text-[10px] px-1.5 py-0.5 font-medium', categoryColor(drawer.category)]"
                style="border-radius: 2px;">{{ drawer.category }}</span>
              <button type="button" @click="closeDrawer" class="ml-auto text-ink-400 hover:text-ink-900"
                aria-label="Close">✕</button>
            </div>
            <div class="text-sm text-ink-900 mt-2">{{ drawer.description }}</div>
            <div class="flex items-baseline gap-2 mt-2">
              <span class="text-xl font-semibold text-ink-900 tabular-nums">{{ fmtINR(drawer.currentRate) }}</span>
              <span class="text-xs text-ink-500">per {{ drawer.unit }}</span>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto">
            <div class="px-4 pt-3 pb-1 text-[10px] uppercase tracking-wider text-ink-500 font-semibold">Rate history
            </div>
            <table class="w-full text-xs">
              <thead>
                <tr class="bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500">
                  <th class="px-3 py-1.5 text-right font-semibold">Rate</th>
                  <th class="px-3 py-1.5 text-left font-semibold">Effective</th>
                  <th class="px-3 py-1.5 text-left font-semibold">Reason</th>
                  <th class="px-3 py-1.5"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="h in drawerHistory" :key="h.id" class="border-b border-ink-100">
                  <td class="px-3 py-1.5 text-right tabular-nums text-ink-900 font-medium">{{ fmtINR(h.rate) }}</td>
                  <td class="px-3 py-1.5 text-ink-700">{{ fmtDate(h.effectiveFrom) }}</td>
                  <td class="px-3 py-1.5 text-ink-600">{{ h.reason }}</td>
                  <td class="px-3 py-1.5 text-right">
                    <FrappeUserBadge :user-id="h.changedBy" :show-name="false" size="xs" />
                  </td>
                </tr>
                <tr v-if="!drawerHistory.length">
                  <td colspan="4" class="px-4 py-6 text-center text-xs text-ink-400 italic">No history recorded yet.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-between gap-2">
            <div class="flex items-center gap-1.5 text-[10px] text-ink-500 min-w-0 truncate">
              <span>By</span>
              <FrappeUserBadge :user-id="drawer.updatedBy" size="xs" />
              <span class="flex-shrink-0">· {{ fmtDate(drawer.updatedAt) }}</span>
            </div>
            <div class="flex items-center gap-2 flex-shrink-0">
              <button type="button"
                class="text-xs px-2 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
                style="border-radius: 6px;" @click="removeRate">Delete</button>
              <button type="button" class="desk-save-btn" @click="editRate">Edit</button>
            </div>
          </div>
        </template>
      </div>
    </div>

  </DeskPage>
</template>
