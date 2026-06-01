// UI metadata for the 12 workspaces (CLAUDE.md §12.2). Separate from src/data/roles.js
// because that file is logic-only (visibility matrix + ordering); this one is UI-only
// (label, icon, route, group, and the live-count helper landings use on their tiles).
//
// Note: [src/layouts/DeskShell.vue](src/layouts/DeskShell.vue) has its own local copy
// of this same metadata. Eventually one should import the other — leaving them as
// parallel copies for now to avoid a refactor outside the prompt's scope.

export const WORKSPACE_META = {
  'site-execution':  { name: 'Site Execution',  icon: '🏗️', to: '/app/site-execution',  group: 'buildsuite',
                        desc: 'Projects, work packages, tasks, schedule.' },
  'estimation':      { name: 'Estimation',      icon: '📐', to: '/app/estimation',      group: 'buildsuite',
                        desc: 'BOQ, Rate Master, revision compare.' },
  'procurement':     { name: 'Procurement',     icon: '🛒', to: '/app/procurement',     group: 'buildsuite',
                        desc: 'Material requests, supplier follow-up, GRN.' },
  'subcontract':     { name: 'Subcontract',     icon: '🤝', to: '/app/subcontract',     group: 'buildsuite',
                        desc: 'Vendors, work orders, RA bills, retention.' },
  'workforce':       { name: 'Workforce',       icon: '👷', to: '/app/workforce',       group: 'buildsuite',
                        desc: 'Crews, overtime, wages to contractor.' },
  // 'scope-change' removed Session 33 — merged into Site Execution. SCO surface
  // lives at /app/sco and is reached via the Site Execution workspace tile grid.
  'project-finance': { name: 'Project Finance', icon: '💵', to: '/app/project-finance', group: 'buildsuite',
                        desc: 'Petty cash, cost summary, project P&L.' },
  'accounting':      { name: 'Accounting',      icon: '📊', to: '/app/accounting',      group: 'erpnext',
                        desc: 'Inherited from ERPNext.' },
  'buying':          { name: 'Buying',          icon: '📥', to: '/app/buying',          group: 'erpnext',
                        desc: 'Inherited from ERPNext.' },
  'stock':           { name: 'Stock',           icon: '📦', to: '/app/stock',           group: 'erpnext',
                        desc: 'Inherited from ERPNext.' },
  'assets':          { name: 'Assets',          icon: '🏭', to: '/app/assets',          group: 'erpnext',
                        desc: 'Inherited from ERPNext — extended for Plant & Machinery.' },
  'hr':              { name: 'HR',              icon: '👤', to: '/app/hr',              group: 'erpnext',
                        desc: 'Inherited from Frappe HR — office staff only.' },
}

// Friendly labels for access-level hints (CLAUDE.md §12.3). The DeskShell sidebar uses
// single-letter abbreviations (R, A, C, …); landings have more horizontal space so they
// show the full word.
export const ACCESS_LABEL = {
  'read':         'Read',
  'approve':      'Approve',
  'create-own':   'Create',
  'self-service': 'Self-service',
  'team-only':    'Team',
  'pay-only':     'Pay',
  'mr-only':      'MR raise',
}

// One-line "live metric" string for a workspace tile. Returns null when the seed/store
// doesn't have data to back a real number — callers should omit the metric line rather
// than display a fake count. Reading the store here keeps the call site's computed()
// reactive to the underlying state.
export function workspaceMetric(slug, store) {
  switch (slug) {
    case 'site-execution': {
      // Session 33: includes pending-SCO count since Scope Change merged here.
      const projects = store.activeProjectsCount
      const scos = store.pendingScosCount
      const base = `${projects} active project${projects === 1 ? '' : 's'}`
      return scos ? `${base} · ${scos} pending SCO${scos === 1 ? '' : 's'}` : base
    }
    case 'estimation': {
      const active = store.activeBoqsCount
      const draft = store.draftBoqsCount
      if (!active && !draft) return null
      return `${active} active · ${draft} draft BOQ${draft === 1 ? '' : 's'}`
    }
    // The four below have no domain data in seed yet — return null to omit the metric.
    case 'procurement':
    case 'subcontract':
    case 'workforce':
    case 'project-finance':
      return null
    // ERPNext workspaces — placeholder data only.
    case 'accounting':
    case 'buying':
    case 'stock':
    case 'assets':
    case 'hr':
      return null
    default:
      return null
  }
}
