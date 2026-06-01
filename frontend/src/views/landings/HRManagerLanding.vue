<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ROLES } from '@/data/roles'
import { WORKSPACE_META, ACCESS_LABEL, workspaceMetric } from '@/data/workspaces'
import { useDataStore } from '@/stores'
import LandingShell from '@/layouts/LandingShell.vue'

const ROLE_ID = 'hr-manager'
const role = ROLES.find(r => r.id === ROLE_ID)
const store = useDataStore()

const today = new Date()
const todayLabel = today.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' })

// All four KPI values are ILLUSTRATIVE — Frappe HR (the source for office-staff data)
// is not wired in the prototype (CLAUDE.md §12.2 inherits it; §12.5 confirms attendance
// is out of scope here). Replace with live reads once HR is hooked up.
const ILLUSTRATIVE_KPIS = [
  { label: 'Active employees',         value: '47', sub: 'On the rolls' },
  { label: 'On leave today',           value: '3',  sub: 'Approved leave today' },
  { label: 'Pending leave approvals',  value: '5',  sub: 'Awaiting manager' },
  { label: 'Expiring documents',       value: '2',  sub: 'Licences / contracts this month' },
]

// Office staff vs site labour split — these are two different populations and
// each is managed through a different workspace.
const populations = [
  { label: 'Office staff',  value: '47',                     context: 'Managed in HR',        tone: 'info' },
  { label: 'Site labour',   value: '142 across 5 projects',  context: 'Managed in Workforce', tone: 'success' },
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
        <p class="text-xs text-ink-500 uppercase tracking-wider font-medium">{{ role.shortName }} · People operations</p>
      </div>
      <h1 class="text-2xl font-semibold text-ink-900 tracking-tight">HR overview today</h1>
      <p class="text-sm text-ink-500 mt-1">
        {{ todayLabel }} ·
        <span class="text-ink-700 font-medium">5 pending approvals</span>
      </p>

      <!-- KPIs -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
        <div v-for="k in ILLUSTRATIVE_KPIS" :key="k.label" class="bg-white border border-ink-200 rounded-xl p-4">
          <div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{ k.label }}</div>
          <div class="text-2xl font-semibold text-ink-900 mt-1">{{ k.value }}</div>
          <div class="text-[11px] text-ink-400 mt-0.5">{{ k.sub }}</div>
        </div>
      </div>

      <!-- Labour vs office staff -->
      <h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Labour vs office staff</h2>
      <div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
        <div class="px-4 py-3 bg-ink-50 border-b border-ink-200 text-xs text-ink-600 leading-snug">
          Two different populations. Office staff are managed in HR; site labour is managed in Workforce.
        </div>
        <div class="divide-y divide-ink-100">
          <div
            v-for="p in populations"
            :key="p.label"
            class="flex items-center gap-3 px-4 py-4"
          >
            <span
              class="w-2.5 h-2.5 rounded-full flex-shrink-0"
              :class="p.tone === 'info' ? 'bg-info-500' : 'bg-success-500'"
            ></span>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-ink-900">{{ p.label }}</div>
              <div class="text-xs text-ink-500 mt-0.5">{{ p.context }}</div>
            </div>
            <div class="text-base font-semibold text-ink-900 tabular-nums flex-shrink-0">{{ p.value }}</div>
          </div>
        </div>
      </div>

      <!-- Your workspaces -->
      <h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Your workspaces</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
