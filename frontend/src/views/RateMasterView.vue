<script setup>
// Construction Rate Master (M3) — Desk-styled (CLAUDE.md §12.4). All store calls
// (addRate / updateRate / deleteRate / rateHistoryFor), computed (rows / kpis),
// sparkline math, and modal/drawer state are preserved verbatim. Visual only.

import { computed, ref } from 'vue'
import { useDataStore } from '@/stores'
import { useConfirm } from '@/composables/useConfirm'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import { fmtINR, fmtDate } from '@/utils/format'

const store = useDataStore()

const categoryFilter = ref('')
const search = ref('')
const editing = ref(null)         // rate object being edited, or 'new' for the add form
const drawer = ref(null)          // rate selected for history drawer

const form = ref({
  code: '', description: '', category: 'Material', unit: '', currentRate: 0, source: 'Manual'
})

function startEdit(r) {
  editing.value = r
  form.value = { code: r.code, description: r.description, category: r.category, unit: r.unit, currentRate: r.currentRate, source: r.source }
}
function startAdd() {
  editing.value = 'new'
  form.value = { code: '', description: '', category: 'Material', unit: '', currentRate: 0, source: 'Manual' }
}
function cancel() { editing.value = null }
function save() {
  if (!form.value.code || !form.value.description || !form.value.unit) {
    alert('Code, description, and unit are required.')
    return
  }
  if (editing.value === 'new') store.addRate(form.value)
  else store.updateRate(editing.value.id, form.value)
  editing.value = null
}
const confirmDialog = useConfirm()
async function remove(r) {
  const ok = await confirmDialog({
    title: 'Delete rate',
    message: `Delete rate ${r.code}? This will also delete its history entries.`,
    confirmLabel: 'Delete',
    destructive: true,
  })
  if (!ok) return
  store.deleteRate(r.id)
  if (drawer.value?.id === r.id) drawer.value = null
}

const rows = computed(() => {
  let list = store.rateMaster.slice()
  if (categoryFilter.value) list = list.filter(r => r.category === categoryFilter.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(r => r.code.toLowerCase().includes(q) || r.description.toLowerCase().includes(q))
  }
  return list.sort((a,b) => a.code.localeCompare(b.code))
})

const kpis = computed(() => {
  const byCat = { Material: 0, Labour: 0, Equipment: 0 }
  store.rateMaster.forEach(r => { byCat[r.category] = (byCat[r.category] || 0) + 1 })
  const dates = store.rateMaster.map(r => r.updatedAt).filter(Boolean).sort()
  const lastUpdate = dates.length ? dates[dates.length - 1] : null
  const fromPo = store.rateMaster.filter(r => r.source !== 'Manual').length
  return { total: store.rateMaster.length, ...byCat, lastUpdate, fromPo }
})

// Sparkline math — preserved exactly. Returns the SVG points / width / height / trendPct
// for the row, or null when there isn't enough history to draw a trend line.
function spark(rateId, currentRate) {
  const history = store.rateHistoryFor(rateId)
  const series = [...history.map(h => ({ rate: h.rate, date: h.effectiveDate })), { rate: currentRate, date: 'now' }]
  if (series.length < 2) return null
  const rates = series.map(s => s.rate)
  const min = Math.min(...rates)
  const max = Math.max(...rates)
  const w = 60, h = 20, pad = 2
  const dx = (w - pad * 2) / (series.length - 1)
  const norm = (r) => max === min ? h / 2 : pad + (h - pad * 2) * (1 - (r - min) / (max - min))
  const points = series.map((s, i) => `${pad + i * dx},${norm(s.rate).toFixed(1)}`).join(' ')
  const first = series[0].rate
  const last = series[series.length - 1].rate
  const trendPct = first ? ((last - first) / first) * 100 : 0
  return { points, w, h, trendPct }
}

function categoryColor(c) {
  return {
    Material:  'bg-blue-50 text-blue-700',
    Labour:    'bg-amber-50 text-amber-700',
    Equipment: 'bg-violet-50 text-violet-700',
  }[c] || 'bg-ink-100 text-ink-600'
}

const columns = [
  { key: 'code',        label: 'Code' },
  { key: 'description', label: 'Description' },
  { key: 'category',    label: 'Category' },
  { key: 'unit',        label: 'UOM' },
  { key: 'currentRate', label: 'Current Rate', align: 'right' },
  { key: 'trend',       label: 'Trend',         align: 'center' },
  { key: 'updatedAt',   label: 'Last Updated' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Estimation', to: '/estimation' },
  { label: 'Rate Master' },
]

const subtitle = computed(() => `${rows.value.length} of ${store.rateMaster.length} · M3 · QS price book`)

function onRowClick(row) { drawer.value = row }
</script>

<template>
  <DeskPage title="Construction Rate Master" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <button type="button" class="desk-save-btn" @click="startAdd">+ New rate</button>
    </template>

    <!-- KPI strip — Desk density -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total rates</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ kpis.total }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Materials</div>
        <div class="text-base font-semibold text-blue-700 mt-0.5">{{ kpis.Material }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Labour</div>
        <div class="text-base font-semibold text-amber-700 mt-0.5">{{ kpis.Labour }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Equipment</div>
        <div class="text-base font-semibold text-violet-700 mt-0.5">{{ kpis.Equipment }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">From POs</div>
        <div class="text-base font-semibold text-success-700 mt-0.5">{{ kpis.fromPo }}</div>
        <div class="text-[10px] text-ink-500 mt-0.5">last update {{ fmtDate(kpis.lastUpdate) }}</div>
      </div>
    </div>

    <DeskList
      v-model="search"
      :rows="rows"
      :columns="columns"
      row-key="id"
      search-placeholder="Search code or description…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskSelect v-if="!categoryFilter" v-model="categoryFilter" class="!w-40">
          <option value="">Category: Any</option>
          <option>Material</option>
          <option>Labour</option>
          <option>Equipment</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Category"
          :value="categoryFilter"
          @remove="categoryFilter = ''"
        />
      </template>

      <template #cell-code="{ row }">
        <DeskLink @click.stop="onRowClick(row)" class="font-mono text-xs">{{ row.code }}</DeskLink>
      </template>
      <template #cell-description="{ row }">
        <span class="text-ink-800 text-xs">{{ row.description }}</span>
      </template>
      <template #cell-category="{ row }">
        <span :class="['text-[10px] px-1.5 py-0.5 font-medium', categoryColor(row.category)]" style="border-radius: 2px;">{{ row.category }}</span>
      </template>
      <template #cell-unit="{ row }">
        <span class="text-ink-600 text-xs">{{ row.unit }}</span>
      </template>
      <template #cell-currentRate="{ row }">
        <span class="tabular-nums text-ink-900 font-medium">{{ fmtINR(row.currentRate) }}</span>
      </template>
      <template #cell-trend="{ row }">
        <div v-if="spark(row.id, row.currentRate)" class="flex items-center justify-center gap-1.5">
          <svg :width="spark(row.id, row.currentRate).w" :height="spark(row.id, row.currentRate).h" class="overflow-visible">
            <polyline
              :points="spark(row.id, row.currentRate).points"
              :stroke="spark(row.id, row.currentRate).trendPct > 0 ? '#dc2626' : '#16a34a'"
              stroke-width="1.5"
              fill="none"
            />
          </svg>
          <span class="text-[10px] tabular-nums" :class="spark(row.id, row.currentRate).trendPct > 0 ? 'text-danger-700' : 'text-success-700'">
            {{ spark(row.id, row.currentRate).trendPct > 0 ? '+' : '' }}{{ spark(row.id, row.currentRate).trendPct.toFixed(1) }}%
          </span>
        </div>
        <div v-else class="text-center text-[10px] text-ink-300">—</div>
      </template>
      <template #cell-updatedAt="{ row }">
        <div class="flex items-center gap-1 text-xs text-ink-500">
          <UserAvatar :user-id="row.updatedBy" size="xs" />
          <span>{{ fmtDate(row.updatedAt) }}</span>
          <span v-if="row.source !== 'Manual'" class="font-mono text-[10px] text-[#16A34A] ml-1">{{ row.source }}</span>
        </div>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No rates match your filters.</div>
      </template>
    </DeskList>

    <!-- Edit / add modal — Desk-styled inputs -->
    <div
      v-if="editing"
      class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-4"
      @click="cancel"
    >
      <div
        class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md"
        style="border-radius: 2px;"
        @click.stop
      >
        <div class="px-4 py-3 border-b border-ink-200 flex items-center">
          <h2 class="text-sm font-semibold text-ink-900">
            {{ editing === 'new' ? 'New rate' : `Edit rate · ${editing.code}` }}
          </h2>
          <button type="button" @click="cancel" class="ml-auto text-ink-400 hover:text-ink-900" aria-label="Close">✕</button>
        </div>
        <div class="p-4 space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <DeskField label="Code" required>
              <DeskInput v-model="form.code" placeholder="e.g. CEM-OPC53" />
            </DeskField>
            <DeskField label="Category">
              <DeskSelect v-model="form.category">
                <option>Material</option>
                <option>Labour</option>
                <option>Equipment</option>
              </DeskSelect>
            </DeskField>
          </div>
          <DeskField label="Description" required>
            <DeskInput v-model="form.description" placeholder="Cement — OPC 53 Grade" />
          </DeskField>
          <div class="grid grid-cols-2 gap-3">
            <DeskField label="Unit" required>
              <DeskInput v-model="form.unit" placeholder="bag, m³, kg, day…" />
            </DeskField>
            <DeskField label="Current rate (₹)">
              <DeskInput v-model.number="form.currentRate" type="number" />
            </DeskField>
          </div>
          <DeskField label="Source" hint="Updating rate auto-archives the previous value to history.">
            <DeskInput v-model="form.source" placeholder="Manual or PO-2026-xxxx" />
          </DeskField>
        </div>
        <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
          <button type="button" @click="cancel" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1">Cancel</button>
          <button type="button" @click="save" class="desk-save-btn">
            {{ editing === 'new' ? 'Create rate' : 'Save changes' }}
          </button>
        </div>
      </div>
    </div>

    <!-- History drawer — Desk-styled table inside; drawer pattern preserved -->
    <div
      v-if="drawer"
      class="fixed inset-0 bg-ink-900/30 z-30 flex justify-end"
      @click="drawer = null"
    >
      <div
        class="w-96 h-full bg-white border-l border-ink-200 shadow-fp-lg flex flex-col"
        @click.stop
      >
        <div class="px-4 py-3 border-b border-ink-200">
          <div class="flex items-center gap-2">
            <span class="font-mono text-xs text-[#16A34A]">{{ drawer.code }}</span>
            <span :class="['text-[10px] px-1.5 py-0.5 font-medium', categoryColor(drawer.category)]" style="border-radius: 2px;">{{ drawer.category }}</span>
            <button type="button" @click="drawer = null" class="ml-auto text-ink-400 hover:text-ink-900" aria-label="Close">✕</button>
          </div>
          <div class="text-sm text-ink-900 mt-2">{{ drawer.description }}</div>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-xl font-semibold text-ink-900 tabular-nums">{{ fmtINR(drawer.currentRate) }}</span>
            <span class="text-xs text-ink-500">per {{ drawer.unit }}</span>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div class="px-4 pt-3 pb-1 text-[10px] uppercase tracking-wider text-ink-500 font-semibold">Rate history</div>
          <table class="w-full text-xs">
            <thead>
              <tr class="bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500">
                <th class="px-3 py-1.5 text-right font-semibold">Rate</th>
                <th class="px-3 py-1.5 text-left font-semibold">Effective</th>
                <th class="px-3 py-1.5 text-left font-semibold">Source</th>
                <th class="px-3 py-1.5"></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="h in store.rateHistoryFor(drawer.id).slice().reverse()"
                :key="h.id"
                class="desk-row-stripe border-b border-ink-100"
              >
                <td class="px-3 py-1.5 text-right tabular-nums text-ink-900 font-medium">{{ fmtINR(h.rate) }}</td>
                <td class="px-3 py-1.5 text-ink-700">{{ fmtDate(h.effectiveDate) }}</td>
                <td class="px-3 py-1.5">
                  <span v-if="h.source === 'Manual'" class="text-ink-500">Manual</span>
                  <span v-else class="font-mono text-[#16A34A]">{{ h.source }}</span>
                </td>
                <td class="px-3 py-1.5 text-right"><UserAvatar :user-id="h.updatedBy" size="xs" /></td>
              </tr>
              <tr v-if="!store.rateHistoryFor(drawer.id).length">
                <td colspan="4" class="px-4 py-6 text-center text-xs text-ink-400 italic">No history recorded yet.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-between gap-2">
          <span class="text-[10px] text-ink-500 truncate">
            By <span class="text-ink-700">{{ store.teamMember(drawer.updatedBy)?.name }}</span> · {{ fmtDate(drawer.updatedAt) }}
          </span>
          <div class="flex items-center gap-2 flex-shrink-0">
            <button
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px; color: #B91C1C;"
              @click="remove(drawer)"
            >Delete</button>
            <button type="button" class="desk-save-btn" @click="startEdit(drawer)">Edit</button>
          </div>
        </div>
      </div>
    </div>
  </DeskPage>
</template>
