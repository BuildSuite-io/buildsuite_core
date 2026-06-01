<script setup>
// Scope Change Orders (M7) — Desk-styled list (CLAUDE.md §12.4). Every computed and
// store call preserved verbatim. Variance-style coloring on impact: positive = cost
// to the project = red; negative = savings = green (matches the convention in
// ProjectDetailView's SCO tab).

import { computed, ref } from 'vue'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtINR, fmtCompactINR, fmtDate } from '@/utils/format'

const store = useDataStore()

const search = ref('')
const statusFilter = ref('')

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return store.scos.filter(s => {
    if (statusFilter.value && s.status !== statusFilter.value) return false
    if (term && !s.title.toLowerCase().includes(term) && !s.id.toLowerCase().includes(term)) return false
    return true
  })
})

function projectName(id) { return store.projectById(id)?.name || id }

const totalImpact      = computed(() => store.scos.reduce((a, s) => a + (s.impact || 0), 0))
const recoverableTotal = computed(() => store.scos.filter(s => s.recoverable).reduce((a, s) => a + (s.impact || 0), 0))

const columns = [
  { key: 'id',          label: 'ID' },
  { key: 'title',       label: 'Title' },
  { key: 'project',     label: 'Project' },
  { key: 'type',        label: 'Type' },
  { key: 'impact',      label: 'Impact',      align: 'right' },
  { key: 'recoverable', label: 'Recoverable' },
  { key: 'status',      label: 'Status' },
  { key: 'raisedBy',    label: 'Raised by' },
  { key: 'raisedDate',  label: 'Date' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Scope Change' },
]

const subtitle = computed(() => `${items.value.length} of ${store.scos.length} · M7 module`)
</script>

<template>
  <DeskPage title="Scope Change Order" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <button type="button" class="desk-save-btn">+ Raise SCO</button>
    </template>

    <!-- KPI strip — Desk-tight -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total SCOs</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ store.scos.length }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Pending approval</div>
        <div class="text-base font-semibold text-warning-700 mt-0.5">{{ store.pendingScosCount }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Net cost impact</div>
        <div class="text-base font-semibold mt-0.5 tabular-nums" :class="totalImpact >= 0 ? 'text-danger-700' : 'text-success-700'">
          {{ totalImpact >= 0 ? '+' : '' }}{{ fmtCompactINR(Math.abs(totalImpact)) }}
        </div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Client recoverable</div>
        <div class="text-base font-semibold text-success-700 mt-0.5 tabular-nums">{{ fmtCompactINR(recoverableTotal) }}</div>
      </div>
    </div>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search SCO id or title…"
    >
      <template #filter-chips>
        <DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-44">
          <option value="">Status: Any</option>
          <option>Pending Approval</option>
          <option>Approved</option>
          <option>Rejected</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Status"
          :value="statusFilter"
          @remove="statusFilter = ''"
        />
      </template>

      <template #cell-id="{ row }">
        <DeskLink class="font-mono text-xs">{{ row.id }}</DeskLink>
      </template>
      <template #cell-title="{ row }">
        <span class="text-ink-900 font-medium text-sm">{{ row.title }}</span>
      </template>
      <template #cell-project="{ row }">
        <span class="text-ink-700 text-xs">{{ projectName(row.projectId) }}</span>
      </template>
      <template #cell-type="{ row }">
        <span class="text-ink-700 text-xs">{{ row.type }}</span>
      </template>
      <template #cell-impact="{ row }">
        <span class="tabular-nums" :class="row.impact >= 0 ? 'text-danger-700' : 'text-success-700'">
          {{ row.impact >= 0 ? '+' : '' }}{{ fmtINR(Math.abs(row.impact)) }}
        </span>
      </template>
      <template #cell-recoverable="{ row }">
        <span
          v-if="row.recoverable"
          class="text-[10px] px-1.5 py-0.5 bg-success-50 text-success-700 font-medium"
          style="border-radius: 2px;"
        >Yes</span>
        <span
          v-else
          class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600 font-medium"
          style="border-radius: 2px;"
        >Internal</span>
      </template>
      <template #cell-status="{ row }">
        <StatusBadge :status="row.status" />
      </template>
      <template #cell-raisedBy="{ row }">
        <UserAvatar :user-id="row.raisedBy" size="xs" />
      </template>
      <template #cell-raisedDate="{ row }">
        <span class="text-xs text-ink-500">{{ fmtDate(row.raisedDate) }}</span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No SCOs match your filters.</div>
      </template>
    </DeskList>
  </DeskPage>
</template>
