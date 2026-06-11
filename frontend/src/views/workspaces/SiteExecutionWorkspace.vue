<script setup>
// Site Execution workspace landing — Vue-styled per §12.4. M1 ships this as
// one of the 3 Vue surfaces (locked by Block-A decision 2). Greeting + role-
// filtered shortcuts grid, no Number Cards / Quick Lists / charts per §13.2.
//
// Architectural win: shortcuts are NOT hardcoded — they come from
// store.visibleShortcutsFor('site-execution'), which reads from Workspace
// Structure Settings (Session 34 DocType). A BSA at a customer org can
// reorder / hide / add shortcuts via /app/settings/workspace-structure
// without developer involvement.
//
// Session 35 — EXPLORATORY DESIGN VISUALISATION (additive, NOT M1 scope):
//   1. A prominent Project Dashboard tile rendered ABOVE the shortcuts grid,
//      gated to "owner" roles (Director / PM / Admin / Accountant / BSA).
//      Routes to /app/project-dashboard (Vue composite landing inside Desk).
//   2. A separate "Reports" group rendered BELOW the shortcuts grid with 5
//      hardcoded Frappe-style report tiles. Each tile routes to
//      /app/reports/:slug (a Desk-styled stub).
//
// Both additions are HARDCODED here — in production they would be configured
// via Workspace Structure Settings DocType records (tile_type discriminator,
// per-tile role visibility, dashboard / report references). The hardcoding
// is deliberate and clearly marked: these are visual mockups for stakeholder
// review of dashboard + report layout, not production architecture.

import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import UserAvatar from '@/components/UserAvatar.vue'
import WorkspaceShortcut from '@/components/WorkspaceShortcut.vue'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const store = useDataStore()

const shortcuts = computed(() => store.visibleShortcutsFor('site-execution'))
const definition = computed(() => store.workspaceDefinitionBySlug('site-execution'))

const today = computed(() => {
  const d = new Date()
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
})

// Short descriptions for each shortcut tile, keyed by route_path. Kept as a
// local map (not on the Workspace Structure Settings DocType schema yet) per
// the same exploratory-mockup framing that owns the Reports group below — a
// schema migration to add `description` to the WSST child table is straight-
// forward but out of scope for this UX tweak.
const SHORTCUT_DESCRIPTIONS = {
  '/projects':         'Plan, track, and manage construction projects.',
  '/work-packages':    'Cost-and-control boundaries within a project.',
  '/tasks':            'Day-to-day execution items with progress tracking.',
  '/stage-plannings':  'Time-phased delivery stages and dependencies.',
  '/progress-entries': 'Daily task progress, labour, and blockers.',
  '/sco':              'Scope change orders and BOQ revision tie-ins.',
  '/schedule':         'Gantt view across projects and stages.',
}
function descriptionFor(routePath) {
  return SHORTCUT_DESCRIPTIONS[routePath] || ''
}

// --- Session 35 additive: Project Dashboard tile -------------------------
// "Owner" roles that should see the portfolio dashboard tile. Hardcoded
// here per the exploratory-visualisation framing; production would put this
// on the workspace tile's `roles` child-table column.
const OWNER_ROLES = ['director', 'pm', 'admin', 'accountant', 'bsa']
const showProjectDashboard = computed(() => OWNER_ROLES.includes(store.role))

// --- Session 35 additive: Reports group ----------------------------------
// 5 hardcoded reports per the prompt. `roles: 'all'` = visible to everyone
// who can see this workspace. Per-report role filtering would be wired
// through Workspace Structure Settings in production.
const REPORT_TILES = [
  {
    slug: 'project-status-summary',
    icon: 'chart-line',
    label: 'Project Status Summary',
    desc: 'Active projects · status · progress · variance.',
    roles: 'all',
  },
  {
    slug: 'task-completion-by-week',
    icon: 'chart-line',
    label: 'Task Completion by Week',
    desc: 'Tasks completed per project per week.',
    roles: 'all',
  },
  {
    slug: 'pending-progress-entries',
    icon: 'file-text',
    label: 'Pending Progress Entries',
    desc: 'Open tasks with no progress entry in N days.',
    roles: 'all',
  },
  {
    slug: 'stage-vs-actual',
    icon: 'calendar',
    label: 'Stage Plan vs Actual',
    desc: 'Planned stages vs actual task progress per stage.',
    roles: ['director', 'pm', 'qs', 'admin', 'bsa'],
  },
  {
    slug: 'labour-deployed',
    icon: 'workforce',
    label: 'Labour Deployed',
    desc: 'Skilled + unskilled labour by task / week.',
    roles: ['director', 'pm', 'site-engineer', 'foreman', 'admin', 'bsa'],
  },
]

function tileVisibleForRole(tile, roleId) {
  if (tile.roles === 'all') return true
  return Array.isArray(tile.roles) && tile.roles.includes(roleId)
}

const visibleReportTiles = computed(() =>
  REPORT_TILES.filter(t => tileVisibleForRole(t, store.role))
)
</script>

<template>
  <div class="bg-gradient-to-br from-ink-50 to-white min-h-full">
    <div class="max-w-6xl mx-auto px-6 py-8">

      <!-- Title strip — workspace name as the heading; date eyebrow only -->
      <div class="mb-6">
        <div class="text-xs text-ink-500 mb-1">{{ today }}</div>
        <h1 class="text-2xl font-semibold text-ink-900">Site Execution</h1>
      </div>

      <!-- BSA hint banner — only visible to BSA (the audience who can reconfigure) -->
      <div v-if="store.isBSA" class="mb-5 px-3 py-2 bg-brand-50 border border-brand-100 text-[11px] text-brand-700 flex items-center justify-between" style="border-radius: 6px;">
        <span>Customize shortcuts shown on this workspace — reorder, hide per role, or add new ones.</span>
        <RouterLink to="/settings/workspace-structure" class="font-medium hover:underline whitespace-nowrap ml-3">
          Configure →
        </RouterLink>
      </div>

      <!-- Session 35 additive — Project Dashboard tile (owner-gated, hardcoded) -->
      <RouterLink
        v-if="showProjectDashboard"
        to="/project-dashboard"
        class="mb-5 block bg-brand-50 border border-brand-200 hover:border-brand-400 hover:shadow-sm p-4 transition-all group"
        style="border-radius: 8px;"
      >
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-lg bg-white/80 text-brand-700 flex items-center justify-center flex-shrink-0">
            <svg
              class="w-5 h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
              v-html="getWorkspaceIconPath('chart-line')"
            />
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <div class="text-base font-semibold text-ink-900 group-hover:text-brand-700 transition-colors dark:text-[#F5F5F5]">Project Dashboard</div>
              <span class="text-[9px] px-1.5 py-0.5 bg-brand-100 text-brand-700 font-medium uppercase tracking-wider" style="border-radius: 2px;">Owner view</span>
            </div>
            <div class="text-xs text-brand-700 mt-1 leading-snug">Portfolio health, top risks, and high-value approvals at a glance.</div>
          </div>
          <svg
            class="w-5 h-5 text-brand-400 group-hover:text-brand-600 transition-colors"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="m9 6 6 6-6 6" />
          </svg>
        </div>
      </RouterLink>

      <!-- Shortcuts grid — driven by workspaceStructure. Tiles use the
           shared <WorkspaceShortcut> component (Session 40) so every
           workspace landing renders the same tile shape. -->
      <div v-if="shortcuts.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <WorkspaceShortcut
          v-for="sc in shortcuts"
          :key="sc.id"
          :to="sc.route_path"
          :icon="sc.icon"
          :label="sc.label"
          :description="descriptionFor(sc.route_path)"
        />
      </div>

      <!-- Empty / disabled state -->
      <div v-else-if="!definition || !definition.enabled" class="bg-white border border-ink-200 px-4 py-6 text-center" style="border-radius: 8px;">
        <div class="text-sm text-ink-500 mb-1">Site Execution workspace is not configured.</div>
        <RouterLink v-if="store.isBSA" to="/settings/workspace-structure" class="text-xs text-brand-700 hover:underline">
          Open Workspace Structure Settings →
        </RouterLink>
        <div v-else class="text-[11px] text-ink-400 italic">Contact your BuildSuite Administrator to enable.</div>
      </div>

      <!-- No shortcuts visible to this role -->
      <div v-else class="bg-white border border-ink-200 px-4 py-6 text-center" style="border-radius: 8px;">
        <div class="text-sm text-ink-500 mb-1">No Site Execution shortcuts available for your role.</div>
        <div class="text-[11px] text-ink-400 italic">Active role: {{ store.currentRole?.name }}</div>
      </div>

      <!-- Session 35 additive — Reports group (hardcoded, role-filtered).
           Uses the shared WorkspaceShortcut with a "Report" badge slot. -->
      <div v-if="visibleReportTiles.length" class="mt-8">
        <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">Reports</h2>
        <div class="border-t border-ink-200 mb-3"></div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <WorkspaceShortcut
            v-for="rt in visibleReportTiles"
            :key="rt.slug"
            :to="`/reports/${rt.slug}`"
            :icon="rt.icon"
            :label="rt.label"
            :description="rt.desc"
          >
            <template #badge>
              <span class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider" style="border-radius: 2px;">Report</span>
            </template>
          </WorkspaceShortcut>
        </div>
      </div>

    </div>
  </div>
</template>
