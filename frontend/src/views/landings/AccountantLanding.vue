<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ROLES } from '@/data/roles'
import { WORKSPACE_META, ACCESS_LABEL, workspaceMetric } from '@/data/workspaces'
import { useDataStore } from '@/stores'
import LandingShell from '@/layouts/LandingShell.vue'
import { fmtCompactINR } from '@/utils/format'

const ROLE_ID = 'accountant'
const role = ROLES.find(r => r.id === ROLE_ID)
const store = useDataStore()

// Prototype assumption: there is no Accountant in the seed team. The Accountant role is a
// persona-only view for the demo. When the prototype gains real auth, this becomes the
// team member with the Accountant role assignment.

const today = new Date()
const todayLabel = today.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' })

// KPI values are ILLUSTRATIVE — petty cash, RA bills, and project P&L all live in
// modules not yet wired (M8 + ERPNext Accounting, see CLAUDE.md §12.2 / §12.6). The
// total-order-book number is real.
const orderBookCompact = computed(() => fmtCompactINR(store.totalOrderBook))

const ILLUSTRATIVE_KPIS = computed(() => [
  { label: 'Petty cash open',      value: '₹4.8 L',                          sub: 'Project Finance' },
  { label: 'RA bills to pay',      value: '11',                              sub: 'Subcontract' },
  { label: 'Project P&L (month)',  value: orderBookCompact.value + ' booked', sub: 'Order book booked' },
  { label: 'Variance flags',       value: '3',                               sub: 'Projects > 10% off plan' },
])

// Illustrative pending vendor payments list — would come from ERPNext Purchase Invoice +
// the M5 Subcontract RA Bills doctype once wired. Suppliers chosen to match real rate-
// master sources so the list at least references entities visible elsewhere.
const pendingPayments = [
  { id: 'PI-2026-0188', vendor: 'JSW Steel',                  category: 'Material',   amount: 1265000, dueIn: 4 },
  { id: 'PI-2026-0171', vendor: 'Prism Johnson',              category: 'Material',   amount: 842000,  dueIn: 7 },
  { id: 'RA-2026-0042', vendor: 'Sundar Constructions',       category: 'Subcontract', amount: 1850000, dueIn: 9 },
  { id: 'PI-2026-0156', vendor: 'Stone & Aggregate Suppliers', category: 'Material',  amount: 318000,  dueIn: 11 },
  { id: 'RA-2026-0043', vendor: 'Royal Plumbing Works',       category: 'Subcontract', amount: 460000,  dueIn: 14 },
]

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
        <p class="text-xs text-ink-500 uppercase tracking-wider font-medium">{{ role.shortName }} · Books & ledgers</p>
      </div>
      <h1 class="text-2xl font-semibold text-ink-900 tracking-tight">Financial position</h1>
      <p class="text-sm text-ink-500 mt-1">
        {{ todayLabel }} ·
        <span class="text-ink-700 font-medium">{{ pendingPayments.length }} vendor payments pending</span>
      </p>

      <!-- KPIs -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
        <div v-for="k in ILLUSTRATIVE_KPIS" :key="k.label" class="bg-white border border-ink-200 rounded-xl p-4">
          <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{ k.label }}</div>
          <div class="text-2xl font-semibold text-ink-900 mt-1">{{ k.value }}</div>
          <div class="text-[11px] text-ink-400 mt-0.5">{{ k.sub }}</div>
        </div>
      </div>

      <!-- Pending vendor payments -->
      <h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Pending vendor payments</h2>
      <div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
        <div class="divide-y divide-ink-100">
          <RouterLink
            v-for="p in pendingPayments"
            :key="p.id"
            to="/accounting"
            class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
          >
            <div
              class="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-semibold"
              :class="p.category === 'Subcontract' ? 'bg-info-50 text-info-700' : 'bg-warning-50 text-warning-700'"
            >{{ p.category === 'Subcontract' ? 'SC' : 'PI' }}</div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-ink-900 truncate">{{ p.vendor }}</div>
              <div class="text-xs text-ink-500 mt-0.5 font-mono">{{ p.id }} · {{ p.category }}</div>
            </div>
            <div class="text-right flex-shrink-0">
              <div class="text-sm font-semibold text-ink-900 tabular-nums">{{ fmtCompactINR(p.amount) }}</div>
              <div class="text-[11px]" :class="p.dueIn <= 7 ? 'text-warning-700' : 'text-ink-500'">due in {{ p.dueIn }}d</div>
            </div>
          </RouterLink>
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
