<script setup>
// BOQ list — Desk-styled (CLAUDE.md §12.4 destination: Desk in production). Every
// computed (rows / kpis), the create-draft modal, and the store calls are preserved.
// Visual only.

import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import { fmtCompactINR, fmtINR } from '@/utils/format'

const router = useRouter()
const store = useDataStore()

const search = ref('')
const projectFilter = ref('')
const statusFilter = ref('')
const showNew = ref(false)
const newForm = ref({ projectId: '', title: '' })

const boqProjects = computed(() => store.projects.slice().sort((a,b) => a.name.localeCompare(b.name)))

function openNew() {
  newForm.value = { projectId: store.projects[0]?.id || '', title: '' }
  showNew.value = true
}
function createBoq() {
  if (!newForm.value.projectId) return
  const proj = store.projectById(newForm.value.projectId)
  const existing = store.boqs.filter(b => b.projectId === newForm.value.projectId)
  const nextRev = existing.length ? Math.max(...existing.map(b => b.revision)) + 1 : 1
  const boq = store.addBoq({
    projectId: newForm.value.projectId,
    revision: nextRev,
    title: newForm.value.title?.trim() || `${proj?.name || 'BOQ'} — Revision ${nextRev}`,
  })
  store.addBoqGroup({ boqId: boq.id, code: 'A', name: 'Civil Works — RCC', order: 1 })
  showNew.value = false
  router.push(`/boq/${boq.id}`)
}

const rootProjects = computed(() => store.rootProjects)
function projectName(id) { return store.projectById(id)?.name || id }

const rows = computed(() => {
  const term = search.value.trim().toLowerCase()
  let list = store.boqs.slice()
  if (projectFilter.value) {
    const childIds = store.projects.filter(p => p.parentId === projectFilter.value).map(p => p.id)
    const ids = [projectFilter.value, ...childIds]
    list = list.filter(b => ids.includes(b.projectId))
  }
  if (statusFilter.value) list = list.filter(b => b.status === statusFilter.value)
  if (term) list = list.filter(b => b.id.toLowerCase().includes(term) || (b.title || '').toLowerCase().includes(term))
  return list
    .map(b => {
      const totals = store.boqTotals(b.id)
      const project = store.projectById(b.projectId)
      return { ...b, totals, projectName: project?.name || b.projectId, projectCode: project?.code || '' }
    })
    .sort((a,b) => (b.preparedDate || '').localeCompare(a.preparedDate || ''))
})

const kpis = computed(() => {
  const approved = store.boqs.filter(b => b.status === 'Approved')
  const totalPlanned = approved.reduce((a,b) => a + store.boqTotals(b.id).planned, 0)
  const totalActual  = approved.reduce((a,b) => a + store.boqTotals(b.id).actual,  0)
  const variance = totalActual - totalPlanned
  return {
    active: store.activeBoqsCount,
    draft: store.draftBoqsCount,
    submitted: store.submittedBoqsCount,
    totalPlanned, totalActual, variance,
    variancePct: totalPlanned ? (variance / totalPlanned) * 100 : 0,
  }
})

function variancePill(pct) {
  if (Math.abs(pct) < 0.5) return 'text-ink-500'
  return pct > 0 ? 'text-danger-700' : 'text-success-700'
}

function onRowClick(row) { router.push(`/boq/${row.id}`) }

const columns = [
  { key: 'id',         label: 'ID' },
  { key: 'project',    label: 'Project' },
  { key: 'revision',   label: 'Rev.',     align: 'center' },
  { key: 'status',     label: 'Status' },
  { key: 'planned',    label: 'Planned',  align: 'right' },
  { key: 'actual',     label: 'Actual',   align: 'right' },
  { key: 'variance',   label: 'Variance', align: 'right' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'BOQ' },
]

const subtitle = computed(() => `${rows.value.length} of ${store.boqs.length} · M3 estimation engine`)
</script>

<template>
  <DeskPage title="Bill of Quantities" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <DeskLink to="/rate-master" class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50" style="border-radius: 2px;">₹ Rate Master</DeskLink>
      <button type="button" class="desk-save-btn" @click="openNew">+ New BOQ</button>
    </template>

    <!-- KPI strip — Desk-tight: thin border, modest number sizing -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Approved</div>
        <div class="text-base font-semibold text-success-700 mt-0.5">{{ kpis.active }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Drafts</div>
        <div class="text-base font-semibold text-ink-700 mt-0.5">{{ kpis.draft }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Submitted</div>
        <div class="text-base font-semibold text-warning-700 mt-0.5">{{ kpis.submitted }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total planned</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">{{ fmtCompactINR(kpis.totalPlanned) }}</div>
        <div class="text-[10px] text-ink-500 mt-0.5">approved BOQs</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Variance</div>
        <div class="text-base font-semibold mt-0.5 tabular-nums" :class="variancePill(kpis.variancePct)">
          {{ kpis.variancePct > 0 ? '+' : '' }}{{ kpis.variancePct.toFixed(1) }}%
        </div>
        <div class="text-[10px] text-ink-500 mt-0.5">{{ fmtCompactINR(kpis.variance) }} delta</div>
      </div>
    </div>

    <DeskList
      v-model="search"
      :rows="rows"
      :columns="columns"
      row-key="id"
      search-placeholder="Search BOQ id or title…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskSelect v-if="!projectFilter" v-model="projectFilter" class="!w-48">
          <option value="">Project: Any</option>
          <option v-for="p in rootProjects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Project"
          :value="projectName(projectFilter)"
          @remove="projectFilter = ''"
        />

        <DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-36">
          <option value="">Status: Any</option>
          <option>Draft</option>
          <option>Submitted</option>
          <option>Approved</option>
          <option>Superseded</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Status"
          :value="statusFilter"
          @remove="statusFilter = ''"
        />
      </template>

      <template #cell-id="{ row }">
        <DeskLink :to="`/boq/${row.id}`" @click.stop class="font-mono text-xs">{{ row.id }}</DeskLink>
      </template>
      <template #cell-project="{ row }">
        <div class="text-xs">
          <div class="text-ink-900">{{ row.projectName }}</div>
          <div class="font-mono text-ink-400">{{ row.projectCode }}</div>
        </div>
      </template>
      <template #cell-revision="{ row }">
        <span class="font-mono text-xs px-1.5 py-0.5 bg-ink-100 text-ink-700" style="border-radius: 2px;">R{{ row.revision }}</span>
      </template>
      <template #cell-status="{ row }">
        <StatusBadge :status="row.status" />
      </template>
      <template #cell-planned="{ row }">
        <span class="tabular-nums text-ink-900">{{ fmtINR(row.totals.planned) }}</span>
      </template>
      <template #cell-actual="{ row }">
        <span class="tabular-nums text-ink-700">{{ fmtINR(row.totals.actual) }}</span>
      </template>
      <template #cell-variance="{ row }">
        <span class="tabular-nums" :class="variancePill(row.totals.variancePct)">
          {{ row.totals.variancePct > 0 ? '+' : '' }}{{ row.totals.variancePct.toFixed(1) }}%
        </span>
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">No BOQs match these filters.</div>
      </template>
    </DeskList>

    <!-- New BOQ modal — kept as a modal pattern (modal ≠ Desk form); inputs restyled to Desk primitives -->
    <div
      v-if="showNew"
      class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
      @click="showNew = false"
    >
      <div
        class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md"
        style="border-radius: 2px;"
        @click.stop
      >
        <div class="px-4 py-3 border-b border-ink-200 flex items-center">
          <h2 class="text-sm font-semibold text-ink-900">New BOQ</h2>
          <button type="button" @click="showNew = false" class="ml-auto text-ink-400 hover:text-ink-900" aria-label="Close">✕</button>
        </div>
        <div class="p-4 space-y-3">
          <DeskField label="Project" required hint="BOQs live at sub-project level too (per proposal).">
            <DeskSelect v-model="newForm.projectId">
              <option v-for="p in boqProjects" :key="p.id" :value="p.id">
                {{ p.parentId ? '↳ ' : '' }}{{ p.name }}
              </option>
            </DeskSelect>
          </DeskField>
          <DeskField label="Title" hint="Leave blank to auto-name. Revision number is computed.">
            <DeskInput v-model="newForm.title" placeholder="e.g. Original BOQ, Tender draft…" />
          </DeskField>
        </div>
        <div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
          <button type="button" @click="showNew = false" class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1">Cancel</button>
          <button type="button" @click="createBoq" class="desk-save-btn">Create draft</button>
        </div>
      </div>
    </div>
  </DeskPage>
</template>
