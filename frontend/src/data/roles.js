// Role system — the 12 standard BuildSuite roles, the workspace visibility matrix,
// and per-role sidebar ordering. These are the locked constraints from CLAUDE.md §12.1–§12.3.
// Update CLAUDE.md §12 alongside any change here so the spec and code stay aligned.
//
// Session 34: BSA (BuildSuite Administrator) added as the 12th role. BSA sits
// alongside System Manager (admin) — they don't replace each other. System
// Manager handles Frappe-platform admin (sites, apps, backups). BSA handles
// BuildSuite-product admin (Workspace Structure Settings, Site Execution
// Settings, Project Type templates, Pro license). Both get ✓ on every workspace.

// =====================================================================
// ROLES — 12 stable role objects. `id` is the persisted slug; `shortName`
// shows in the topbar dropdown trigger; `color` is a Tailwind bg- class for
// the role badge, picked from the project's named palette (see tailwind.config.js).
// =====================================================================
export const ROLES = [
  {
    id: 'director',
    name: 'Director / Owner',
    shortName: 'Director',
    description: 'Executive oversight — portfolio P&L, approvals at threshold, strategic decisions.',
    color: 'bg-ink-900',
  },
  {
    id: 'pm',
    name: 'Project Manager',
    shortName: 'PM',
    description: 'Owns project delivery — schedule, scope, budget, day-to-day approvals.',
    color: 'bg-info-600',
  },
  {
    id: 'estimator',
    name: 'Estimator',
    shortName: 'Estimator',
    description: 'Builds tenders and initial BOQs from drawings and rate analysis.',
    color: 'bg-warning-500',
  },
  {
    id: 'qs',
    name: 'Quantity Surveyor',
    shortName: 'QS',
    description: 'Maintains rates, measurement books, RA bills, and BOQ revisions during execution.',
    color: 'bg-warning-700',
  },
  {
    id: 'site-engineer',
    name: 'Site Engineer',
    shortName: 'Site Engineer',
    description: 'Runs the site day-to-day — tasks, material requests, daily diary, scope flags.',
    color: 'bg-success-600',
  },
  {
    id: 'foreman',
    name: 'Foreman / Supervisor',
    shortName: 'Foreman',
    description: 'Field supervisor — crews, overtime, on-site execution.',
    color: 'bg-success-700',
  },
  {
    id: 'procurement',
    name: 'Procurement Officer',
    shortName: 'Procurement',
    description: 'Converts material requests into POs, manages suppliers and GRN.',
    color: 'bg-info-700',
  },
  {
    id: 'store-keeper',
    name: 'Store Keeper',
    shortName: 'Store',
    description: 'Receives, issues, and reconciles stock at site stores.',
    color: 'bg-ink-600',
  },
  {
    id: 'accountant',
    name: 'Accountant',
    shortName: 'Accountant',
    description: 'Books vendor and subcontractor payments, petty cash, journals.',
    color: 'bg-danger-600',
  },
  {
    id: 'hr-manager',
    name: 'HR Manager',
    shortName: 'HR Manager',
    description: 'Office-staff HR — employees, leave, salary, appraisal (site labour lives in Workforce).',
    color: 'bg-info-500',
  },
  {
    id: 'admin',
    name: 'System Manager (Admin)',
    shortName: 'Admin',
    description: 'Full access — Frappe-platform admin: sites, apps, backups, integrations, troubleshooting.',
    color: 'bg-brand-600',
  },
  {
    id: 'bsa',
    name: 'BuildSuite Administrator',
    shortName: 'BS Admin',
    description: 'BuildSuite-product admin — Workspace Structure, Site Execution Settings, Project Type templates, Pro license. The "BuildSuite owner" at a customer org.',
    color: 'bg-brand-700',
  },
]

// =====================================================================
// WORKSPACE_VISIBILITY — verbatim encoding of CLAUDE.md §12.3.
// Keyed by workspace slug, then by role id, value is the access level
// or null if the workspace is hidden for that role.
//
//   'full'         — ✓   full access
//   'read'         — ✓R  read-only
//   'approve'      — ✓A  approve-only (can't create or edit, only approve)
//   'create-own'   — ✓C  create-own (e.g. raise own tasks)
//   'self-service' — ✓SS self-service (own leave / payslip)
//   'team-only'    — ✓T  team-only (HR scoped to direct reports)
//   'pay-only'     — ✓P  pay-only (sees billing/payment view only)
//   'mr-only'      — ✓MR material-request raise only
//    null          — —   hidden
// =====================================================================
export const WORKSPACE_VISIBILITY = {
  // Session 33 — Scope Change merged into Site Execution. Estimator + Accountant
  // gain read access here so they can still reach SCOs (which moved under this
  // workspace from the dropped Scope Change workspace). Previously they had no
  // Site Execution access; the SCO-visibility gap was the explicit reason for
  // this matrix revision.
  'site-execution': {
    director: 'full',     pm: 'full',     estimator: 'read', qs: 'read',
    'site-engineer': 'full', foreman: 'create-own',
    procurement: null,    'store-keeper': null,
    accountant: 'read',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  estimation: {
    director: 'full',     pm: 'read',     estimator: 'full', qs: 'full',
    'site-engineer': null, foreman: null,
    procurement: null,    'store-keeper': null,
    accountant: null,     'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  procurement: {
    director: 'full',     pm: 'approve',  estimator: null,   qs: null,
    'site-engineer': 'mr-only', foreman: null,
    procurement: 'full',  'store-keeper': 'full',
    accountant: 'read',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  subcontract: {
    director: 'full',     pm: 'approve',  estimator: null,   qs: 'full',
    'site-engineer': null, foreman: null,
    procurement: null,    'store-keeper': null,
    accountant: 'pay-only', 'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  workforce: {
    director: 'full',     pm: 'approve',  estimator: null,   qs: null,
    'site-engineer': 'full', foreman: 'full',
    procurement: null,    'store-keeper': null,
    accountant: 'pay-only', 'hr-manager': 'read',
    admin: 'full',
    bsa: 'full',
  },
  // 'scope-change' removed in Session 33 — merged into Site Execution. The
  // SCO list still exists at /app/sco; access is governed by the Site Execution
  // row above. See CLAUDE.md §10 Session 33 for the rationale + §12.2 revision.
  'project-finance': {
    director: 'full',     pm: 'full',     estimator: null,   qs: 'read',
    'site-engineer': null, foreman: null,
    procurement: null,    'store-keeper': null,
    accountant: 'full',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  accounting: {
    director: 'full',     pm: 'read',     estimator: null,   qs: null,
    'site-engineer': null, foreman: null,
    procurement: null,    'store-keeper': null,
    accountant: 'full',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  buying: {
    director: 'full',     pm: 'read',     estimator: null,   qs: null,
    'site-engineer': null, foreman: null,
    procurement: 'full',  'store-keeper': 'read',
    accountant: 'read',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  stock: {
    director: 'full',     pm: 'read',     estimator: null,   qs: null,
    'site-engineer': 'read', foreman: null,
    procurement: 'read',  'store-keeper': 'full',
    accountant: 'read',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  assets: {
    director: 'full',     pm: 'read',     estimator: null,   qs: null,
    'site-engineer': 'read', foreman: 'read',
    procurement: null,    'store-keeper': null,
    accountant: 'full',   'hr-manager': null,
    admin: 'full',
    bsa: 'full',
  },
  hr: {
    director: 'full',     pm: 'team-only', estimator: 'self-service', qs: 'self-service',
    'site-engineer': 'self-service', foreman: 'self-service',
    procurement: 'self-service',     'store-keeper': 'self-service',
    accountant: 'full',   'hr-manager': 'full',
    admin: 'full',
    bsa: 'full',
  },
}

// =====================================================================
// WORKSPACE_ORDER — sidebar ordering per role, by frequency of use.
// Not alphabetical. Hidden workspaces are simply omitted (the store getter
// also filters out anything with a null visibility, so leaving a slug here
// for a role that can't see it is harmless — but keep the lists honest).
//
// Orderings for Foreman, PM, and Site Engineer are taken verbatim from
// CLAUDE.md §12.3. The others are chosen by frequency-of-use given the
// visibility matrix. Admin and Director see all 12: BuildSuite workspaces
// first, then the inherited ERPNext / Frappe HR block at the bottom.
// =====================================================================
// Session 33 — 6 BuildSuite workspaces (was 7). Scope Change merged into
// Site Execution; SCOs are reached via the merged workspace's shortcut tile.
const BUILDSUITE_WORKSPACES = [
  'site-execution',
  'estimation',
  'procurement',
  'subcontract',
  'workforce',
  'project-finance',
]
const INHERITED_WORKSPACES = [
  'accounting',
  'buying',
  'stock',
  'assets',
  'hr',
]

export const WORKSPACE_ORDER = {
  // All 11. Director leads with finance/oversight; Admin and BSA with execution.
  director: [
    'project-finance',
    'site-execution',
    'estimation',
    'subcontract',
    'procurement',
    'workforce',
    ...INHERITED_WORKSPACES,
  ],
  admin: [...BUILDSUITE_WORKSPACES, ...INHERITED_WORKSPACES],
  // BSA (Session 34) — BuildSuite-product admin. Same full-access surface as
  // Admin per the §12.3 matrix revision. Ordered identically.
  bsa: [...BUILDSUITE_WORKSPACES, ...INHERITED_WORKSPACES],

  // From §12.3 verbatim, revised Session 33: 'scope-change' dropped (merged
  // into Site Execution) wherever it appeared.
  pm: [
    'site-execution',
    'procurement',
    'subcontract',
    'workforce',
    'project-finance',
    'estimation',
    'assets',
    'hr',
  ],
  'site-engineer': [
    'site-execution',
    'workforce',
    'stock',
    'hr',
  ],
  foreman: [
    'workforce',
    'site-execution',
    'assets',
    'hr',
  ],

  // Filled in by frequency of use given visibility.
  estimator: [
    'estimation',
    // Site Execution added Session 33 — Estimator gets read access to reach
    // SCOs which moved here when Scope Change workspace was merged.
    'site-execution',
    'hr',
  ],
  qs: [
    'estimation',
    'subcontract',
    'site-execution',
    'project-finance',
    'hr',
  ],
  procurement: [
    'procurement',
    'buying',
    'stock',
    'hr',
  ],
  'store-keeper': [
    'stock',
    'procurement',
    'buying',
    'hr',
  ],
  accountant: [
    'project-finance',
    'accounting',
    'assets',
    'subcontract',
    'workforce',
    // Site Execution added Session 33 — Accountant gets read access to reach
    // SCOs (financial impact tracking) which moved into Site Execution when
    // the Scope Change workspace was merged.
    'site-execution',
    'procurement',
    'buying',
    'stock',
    'hr',
  ],
  'hr-manager': [
    'hr',
    'workforce',
  ],
}

// Map a User.persona Select value (the human label, e.g. "Project Manager") to
// the persona id used by the role switcher / gating (e.g. "pm"). Returns null
// when the label isn't a recognised persona.
export function personaIdFromName(name) {
  if (!name) return null
  const match = ROLES.find((r) => r.name === name)
  return match ? match.id : null
}

// Frappe BuildSuite role -> persona id. Used as a fallback when the User.persona
// field is unset (e.g. Administrator). Mirrors the backend permissions/setup map.
export const ROLE_TO_PERSONA = {
  'BuildSuite Director': 'director',
  'BuildSuite PM': 'pm',
  'BuildSuite Estimator': 'estimator',
  'BuildSuite QS': 'qs',
  'BuildSuite Site Engineer': 'site-engineer',
  'BuildSuite Foreman': 'foreman',
  'BuildSuite Procurement Officer': 'procurement',
  'BuildSuite Store Keeper': 'store-keeper',
  'BuildSuite Accountant': 'accountant',
  'BuildSuite HR Manager': 'hr-manager',
  'BuildSuite Administrator': 'bsa',
  'System Manager': 'admin',
}

// Derive a persona id from a user's Frappe roles. Prefers a specific BuildSuite
// persona role over the broad admin roles, so e.g. a PM who also has System
// Manager still reads as 'pm'.
export function personaIdFromRoles(roles) {
  const set = new Set(roles || [])
  for (const [role, persona] of Object.entries(ROLE_TO_PERSONA)) {
    if (role === 'System Manager' || role === 'BuildSuite Administrator') continue
    if (set.has(role)) return persona
  }
  if (set.has('BuildSuite Administrator')) return 'bsa'
  if (set.has('System Manager')) return 'admin'
  return null
}

// ---------------------------------------------------------------------------
// UI permission matrix (S124-130). The BACKEND (permissions/*.py) is the real
// enforcement; this only decides which affordances to SHOW so personas don't
// click buttons that will fail. Keyed by persona id (= store.role, set from the
// logged-in user on load).
//
// Per doctype: c(reate) / r(ead) / e(dit) / d(elete) — true | false | 'own'.
// 'own' means the persona can act on their own records; we SHOW the affordance
// and let the backend enforce the precise own-record rule (avoids hiding a
// user's legitimate own-record action). Full personas are true; read-only are
// false. Settings CRUD stays gated on isAdmin/isBSA separately.
// ---------------------------------------------------------------------------
const _FULL = { c: true, r: true, e: true, d: true }
const _READ = { c: false, r: true, e: false, d: false }
const _NONE = { c: false, r: false, e: false, d: false }
const _OWN = { c: true, r: true, e: 'own', d: 'own' }

export const PERSONA_CAPS = {
  director:       { project: _FULL, workPackage: _FULL, task: _FULL, taskProgressEntry: _FULL, stagePlanning: _FULL },
  pm:             { project: _FULL, workPackage: _FULL, task: _FULL, taskProgressEntry: _FULL, stagePlanning: _FULL },
  admin:          { project: _FULL, workPackage: _FULL, task: _FULL, taskProgressEntry: _FULL, stagePlanning: _FULL },
  bsa:            { project: _FULL, workPackage: _FULL, task: _FULL, taskProgressEntry: _FULL, stagePlanning: _FULL },
  estimator:      { project: _READ, workPackage: _READ, task: _READ, taskProgressEntry: _READ, stagePlanning: _READ },
  qs:             { project: _READ, workPackage: _READ, task: _READ, taskProgressEntry: _READ, stagePlanning: _READ },
  accountant:     { project: _READ, workPackage: _READ, task: _READ, taskProgressEntry: _READ, stagePlanning: _READ },
  procurement:    { project: _READ, workPackage: _READ, task: _READ, taskProgressEntry: _NONE, stagePlanning: _NONE },
  'store-keeper': { project: _READ, workPackage: _READ, task: _READ, taskProgressEntry: _NONE, stagePlanning: _NONE },
  'site-engineer':{ project: _READ, workPackage: _READ, task: _OWN,  taskProgressEntry: _OWN,  stagePlanning: _OWN },
  foreman:        { project: _READ, workPackage: _READ, task: _OWN,  taskProgressEntry: _OWN,  stagePlanning: _OWN },
  'hr-manager':   { project: _NONE, workPackage: _NONE, task: _NONE, taskProgressEntry: _READ, stagePlanning: _NONE },
}
