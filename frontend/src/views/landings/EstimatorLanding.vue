<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ROLES } from '@/data/roles'
import { WORKSPACE_META, ACCESS_LABEL, workspaceMetric } from '@/data/workspaces'
import { useDataStore } from '@/stores'
import LandingShell from '@/layouts/LandingShell.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { fmtCompactINR, fmtDate } from '@/utils/format'

const ROLE_ID = 'estimator'
const role = ROLES.find(r => r.id === ROLE_ID)
const store = useDataStore()

// Prototype assumption: there is no dedicated "Estimator" in the seed team — Aadith P.
// (USR-003) is labelled "Lead Engineer" but doubles as the estimator persona for demo.
// When the prototype gains real auth, this becomes whichever team member holds the
// Estimator role assignment.
const ESTIMATOR_USER_ID = 'USR-003'

const today = new Date()
const todayLabel = today.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' })

const draftBoqs = computed(() =>
  store.boqs.filter(b => b.status === 'Draft').slice().sort(
    (a, b) => new Date(b.preparedDate).getTime() - new Date(a.preparedDate).getTime()
  )
)

const recentEstimates = computed(() =>
  draftBoqs.value.slice(0, 5).map(b => {
    const proj = store.projectById(b.projectId)
    const totals = store.boqTotals(b.id)
    return {
      ...b,
      projectName: proj?.name || '—',
      plannedAmount: totals.planned,
    }
  })
)

// KPI: total planned value across draft BOQs — a real number we can show.
const draftValueTotal = computed(() => recentEstimates.value.reduce((a, b) => a + (b.plannedAmount || 0), 0))

const tiles = computed(() =>
  store.visibleWorkspaces.map(slug => ({
    slug,
    ...WORKSPACE_META[slug],
    metric: workspaceMetric(slug, store),
    access: store.workspaceAccess(slug),
  }))
)
</script>

<template>
  <LandingShell>
    <div class="max-w-5xl mx-auto px-6 py-10">
      <!-- Greeting -->
      <div class="flex items-center gap-3 mb-2">
        <span :class="role.color" class="w-2.5 h-2.5 rounded-full"></span>
        <p class="text-xs text-ink-500 uppercase tracking-wider font-medium">{{ role.shortName }} · Estimating desk</p>
      </div>
      <h1 class="text-2xl font-semibold text-ink-900 tracking-tight">BOQs to estimate this week</h1>
      <p class="text-sm text-ink-500 mt-1">
        {{ todayLabel }} ·
        <span class="text-ink-700 font-medium">{{ draftBoqs.length }} draft BOQ{{ draftBoqs.length === 1 ? '' : 's' }}</span>
      </p>

      <!-- KPIs -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
        <div class="bg-white border border-ink-200 rounded-xl p-4">
          <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Active estimates</div>
          <div class="text-2xl font-semibold text-ink-900 mt-1">{{ store.draftBoqsCount }}</div>
          <div class="text-[11px] text-ink-400 mt-0.5">Draft BOQs awaiting submission</div>
        </div>
        <div class="bg-white border border-ink-200 rounded-xl p-4">
          <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Tenders due</div>
          <div class="text-2xl font-semibold text-ink-900 mt-1">—</div>
          <div class="text-[11px] text-ink-400 mt-0.5">This week</div>
        </div>
        <div class="bg-white border border-ink-200 rounded-xl p-4">
          <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Avg win rate</div>
          <div class="text-2xl font-semibold text-ink-900 mt-1">62%</div>
          <div class="text-[11px] text-ink-400 mt-0.5">Last 12 months</div>
        </div>
        <div class="bg-white border border-ink-200 rounded-xl p-4">
          <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Approved BOQs</div>
          <div class="text-2xl font-semibold text-ink-900 mt-1">{{ store.activeBoqsCount }}</div>
          <div class="text-[11px] text-ink-400 mt-0.5">In execution as templates</div>
        </div>
      </div>

      <!-- Recent estimates -->
      <h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Recent estimates</h2>
      <div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
        <div class="divide-y divide-ink-100">
          <RouterLink
            v-for="b in recentEstimates"
            :key="b.id"
            :to="`/boq/${b.id}`"
            class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
          >
            <div class="w-8 h-8 rounded-lg bg-warning-50 text-warning-700 flex items-center justify-center text-xs font-semibold">R{{ b.revision }}</div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-ink-900 truncate">{{ b.title }}</div>
              <div class="text-xs text-ink-500 mt-0.5 truncate">{{ b.projectName }} · {{ fmtDate(b.preparedDate) }}</div>
            </div>
            <div class="text-right flex-shrink-0">
              <div class="text-sm font-semibold text-ink-900 tabular-nums">{{ fmtCompactINR(b.plannedAmount) }}</div>
            </div>
            <StatusBadge :status="b.status" />
          </RouterLink>
          <div v-if="!recentEstimates.length" class="px-4 py-8 text-center text-sm text-ink-400">
            No draft BOQs ·
            <RouterLink to="/boq" class="text-brand-600 hover:underline">Open Estimation →</RouterLink>
          </div>
        </div>
        <div v-if="draftValueTotal > 0" class="px-4 py-2 bg-ink-50 text-[11px] text-ink-600 text-right">
          Combined planned value across shown drafts: <span class="font-medium tabular-nums">{{ fmtCompactINR(draftValueTotal) }}</span>
        </div>
      </div>

      <!-- Your workspaces -->
      <h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Your workspaces</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        <RouterLink
          v-for="t in tiles"
          :key="t.slug"
          :to="t.to"
          class="block bg-white border border-ink-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-fp-md transition-all"
        >
          <div class="flex items-start gap-3">
            <div class="text-2xl">{{ t.icon }}</div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-ink-900">{{ t.name }}</span>
                <span v-if="t.access && t.access !== 'full'" class="text-[9px] font-medium text-ink-500 border border-ink-200 rounded px-1.5 leading-4">{{ ACCESS_LABEL[t.access] }}</span>
              </div>
              <div class="text-[11px] text-ink-500 mt-1 leading-snug">{{ t.desc }}</div>
              <div v-if="t.metric" class="text-[11px] text-brand-700 font-medium mt-2">{{ t.metric }}</div>
            </div>
          </div>
        </RouterLink>
      </div>
    </div>
  </LandingShell>
</template>
