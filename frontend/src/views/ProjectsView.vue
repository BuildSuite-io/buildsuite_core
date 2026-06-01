<script setup>
// Projects list — Desk-styled (CLAUDE.md §12.4 destination: Desk in production).
//
// Session 38: simplified to a flat list of root projects only. Subprojects no
// longer appear in this table — they are reached via Project Detail's
// "Subprojects" tab. The Company column was replaced by Project Type; Company
// is still inherited via §14 derivation but isn't a list column anymore.

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtCompactINR, fmtDate } from '@/utils/format'
import { createDataAdapter } from '@/data/adapters'

const store = useDataStore()
const router = useRouter()
const adapter = createDataAdapter(store)

const projectsResource = adapter.getRootProjects()
const companiesResource = adapter.getCompanies()

const search = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
// §14 — Company filter (filter-only, no column). Gated on isMultiCompany,
// so single-company sites never see it. User-driven — not auto-set from the
// active company.
const companyFilter = ref('')

// Derived from the companies resource so both local and remote modes work.
const isMultiCompany = computed(() => (companiesResource.data?.length ?? 0) > 1)

// Flat list of root projects only — no recursion, no subproject rows. Subs
// are reached via Project Detail > Subprojects tab.
const rows = computed(() => {
  const projects = projectsResource.data
  if (!projects) return []
  const term = search.value.trim().toLowerCase()
  return projects.filter(p =>
    (!term ||
      p.name.toLowerCase().includes(term) ||
      p.code.toLowerCase().includes(term) ||
      p.client.toLowerCase().includes(term))
    && (!statusFilter.value || p.status === statusFilter.value)
    && (!typeFilter.value || p.type === typeFilter.value)
    && (!companyFilter.value || p.company === companyFilter.value)
  )
})

function companyName(id) {
  return companiesResource.data?.find(c => c.id === id)?.name || id
}

// Schedule-based variance per project — drives the progress-bar traffic-light color.
// Positive = behind plan (red/amber), negative or near-zero = on track or ahead (green).
const today = new Date()
function projectVariance(p) {
  const start = new Date(p.startDate).getTime()
  const end = new Date(p.endDate).getTime()
  const total = end - start
  if (total <= 0) return 0
  const elapsed = Math.max(0, Math.min(total, today.getTime() - start))
  const expected = (elapsed / total) * 100
  if (expected <= 0) return 0
  return ((expected - p.progress) / expected) * 100
}
function progressBarColor(p) {
  const v = projectVariance(p)
  if (v > 15) return 'bg-danger-500'
  if (v > 5) return 'bg-warning-500'
  return 'bg-success-500'
}

const columns = [
  { key: 'code',     label: 'ID' },
  { key: 'name',     label: 'Project Name' },
  { key: 'client',   label: 'Client' },
  { key: 'type',     label: 'Type' },
  { key: 'status',   label: 'Status' },
  { key: 'budget',   label: 'Budget',   align: 'right' },
  { key: 'progress', label: 'Progress', align: 'right' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'pm',       label: 'PM' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Project' },
]

const subtitle = computed(() => `${rows.value.length} of ${projectsResource.data?.length ?? 0}`)

function onRowClick(row) {
  router.push(`/app/projects/${row.id}`)
}
</script>

<template>
  <DeskPage title="Project" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/app/projects/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <div v-if="projectsResource.loading" class="py-8 text-center text-sm text-ink-500">
      Loading projects…
    </div>

    <DeskList
      v-else
      v-model="search"
      :rows="rows"
      :columns="columns"
      row-key="id"
      search-placeholder="Search by name, code, client…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskSelect v-model="statusFilter" class="!w-32">
          <option value="">Status: Any</option>
          <option>Active</option>
          <option>On Hold</option>
          <option>Completed</option>
        </DeskSelect>
        <DeskSelect v-model="typeFilter" class="!w-32">
          <option value="">Type: Any</option>
          <option>Commercial</option>
          <option>Residential</option>
          <option>Infrastructure</option>
          <option>Industrial</option>
          <option>Renovation</option>
        </DeskSelect>
        <!-- §14 — Company filter (filter-only, no column). Single-company sites
             never see this. DeskSelect ↔ DeskFilterChip toggle pattern. -->
        <template v-if="isMultiCompany">
          <DeskSelect v-if="!companyFilter" v-model="companyFilter" class="!w-44">
            <option value="">Company: Any</option>
            <option v-for="c in companiesResource.data" :key="c.id" :value="c.id">{{ c.name }}</option>
          </DeskSelect>
          <DeskFilterChip
            v-else
            label="Company"
            :value="companyName(companyFilter)"
            @remove="companyFilter = ''"
          />
        </template>
      </template>

      <template #cell-code="{ row }">
        <DeskLink :to="`/app/projects/${row.id}`" @click.stop class="font-mono text-xs">{{ row.code }}</DeskLink>
      </template>

      <template #cell-name="{ row }">
        <span class="text-ink-900 font-medium">{{ row.name }}</span>
      </template>

      <template #cell-type="{ row }">
        <span class="text-xs text-ink-700 whitespace-nowrap">{{ row.type || '—' }}</span>
      </template>

      <template #cell-status="{ row }">
        <StatusBadge :status="row.status" />
      </template>

      <template #cell-budget="{ row }">
        <span class="tabular-nums">{{ fmtCompactINR(row.budget) }}</span>
      </template>

      <template #cell-progress="{ row }">
        <div class="flex items-center justify-end gap-2">
          <div class="w-16 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
            <div class="h-full" :class="progressBarColor(row)" :style="`width:${row.progress}%`"></div>
          </div>
          <span class="text-xs text-ink-700 tabular-nums w-8 text-right">{{ row.progress }}%</span>
        </div>
      </template>

      <template #cell-timeline="{ row }">
        <span class="text-xs text-ink-500 whitespace-nowrap">{{ fmtDate(row.startDate) }} → {{ fmtDate(row.endDate) }}</span>
      </template>

      <template #cell-pm="{ row }">
        <UserAvatar :user-id="row.pm" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No projects match your filters ·
          <DeskLink to="/app/projects/new">Create one →</DeskLink>
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
