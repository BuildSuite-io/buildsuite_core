// Central data store for BuildSuite prototype.
// Persists to localStorage so created data survives page reloads.
// To reset: in browser DevTools > Application > Local Storage, remove the 'buildsuite:data:v1' key, then reload.

import { defineStore } from 'pinia'
import { seedData } from '@/data/seed'
import { ROLES, WORKSPACE_VISIBILITY, WORKSPACE_ORDER } from '@/data/roles'
import { PROJECT_TYPE_TEMPLATES, templateForType } from '@/data/projectTypeTemplates'
import { COMPANIES, DEFAULT_COMPANY_ID } from '@/data/companies'

const STORAGE_KEY = 'buildsuite:data:v1'
// Role is persisted under its own key so resetAll() (which wipes domain data)
// preserves the active role — it's a UI preference, not seed-derived state.
const ROLE_STORAGE_KEY = 'buildsuite:role'
const DEFAULT_ROLE = 'admin'
// Active company also persisted independently — same rationale as role.
const COMPANY_STORAGE_KEY = 'buildsuite:company'
// Light / dark theme — same independent-persistence pattern as role + company.
const THEME_STORAGE_KEY = 'buildsuite:theme'
const DEFAULT_THEME = 'light'

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch (e) {
    console.warn('Failed to read store from localStorage:', e)
    return null
  }
}

function loadRoleFromStorage() {
  try {
    return localStorage.getItem(ROLE_STORAGE_KEY)
  } catch (e) {
    console.warn('Failed to read role from localStorage:', e)
    return null
  }
}

function saveRoleToStorage(roleId) {
  try {
    localStorage.setItem(ROLE_STORAGE_KEY, roleId)
  } catch (e) {
    console.warn('Failed to persist role:', e)
  }
}

function loadCompanyFromStorage() {
  try {
    return localStorage.getItem(COMPANY_STORAGE_KEY)
  } catch (e) {
    console.warn('Failed to read active company from localStorage:', e)
    return null
  }
}

function saveCompanyToStorage(companyId) {
  try {
    localStorage.setItem(COMPANY_STORAGE_KEY, companyId)
  } catch (e) {
    console.warn('Failed to persist active company:', e)
  }
}

function loadThemeFromStorage() {
  try {
    return localStorage.getItem(THEME_STORAGE_KEY)
  } catch (e) {
    console.warn('Failed to read theme from localStorage:', e)
    return null
  }
}
function saveThemeToStorage(theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch (e) {
    console.warn('Failed to persist theme:', e)
  }
}

function saveToStorage(state) {
  try {
    const payload = {
      companies: state.companies,
      user: state.user,
      team: state.team,
      projects: state.projects,
      workPackages: state.workPackages,
      tasks: state.tasks,
      activityTypes: state.activityTypes,
      taskProgressEntries: state.taskProgressEntries,
      stagePlannings: state.stagePlannings,
      attachments: state.attachments,
      scos: state.scos,
      rateMaster: state.rateMaster,
      rateHistory: state.rateHistory,
      boqs: state.boqs,
      boqGroups: state.boqGroups,
      boqItems: state.boqItems,
      boqSubItems: state.boqSubItems,
      // Settings DocTypes (Session 34)
      coreSettings: state.coreSettings,
      siteExecutionSettings: state.siteExecutionSettings,
      workspaceStructure: state.workspaceStructure,
      // Session 39 — Project Type Settings (exploratory; brings forward the
      // Heavy interpretation from §13.3 item 19 and the M2-deferred configurable
      // WP label from Session 36).
      projectTypes: state.projectTypes,
      // Session 40 — Customer master (ERPNext-native shape).
      customers: state.customers,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch (e) {
    console.warn('Failed to persist store:', e)
  }
}

function uid(prefix) {
  return `${prefix}-${Date.now().toString().slice(-6)}-${Math.floor(Math.random() * 1000)}`
}

// Add N days to a YYYY-MM-DD string and return YYYY-MM-DD. The 'T00:00:00'
// suffix avoids the UTC-vs-local-midnight one-day-shift that bites on naive
// `new Date(iso)` parsing in many timezones.
function addDaysISO(isoDate, days) {
  if (!isoDate) return ''
  const d = new Date(isoDate + 'T00:00:00')
  d.setDate(d.getDate() + Number(days || 0))
  return d.toISOString().slice(0, 10)
}

export const useDataStore = defineStore('data', {
  state: () => ({
    hydrated: false,
    // Active role id. NOT persisted via _persist() — see ROLE_STORAGE_KEY above.
    role: DEFAULT_ROLE,
    // Active company id. Same independent-persistence rationale as `role` — lives
    // in COMPANY_STORAGE_KEY so resetAll() preserves it as a UI preference.
    activeCompany: DEFAULT_COMPANY_ID,
    // Light / dark theme. Same independent-persistence pattern as role +
    // company — lives in THEME_STORAGE_KEY so resetAll() preserves it as
    // a UI preference.
    theme: DEFAULT_THEME,
    // Companies master list. Project-scoped slices derive `company` from their
    // parent project; this slice is the source of truth for what companies exist.
    companies: [],
    // Customer master (Session 40). Mirrors ERPNext Customer DocType. The
    // join key onto project.client is the customer's `name` field — existing
    // project.client values are plain strings and the seed records match.
    customers: [],
    user: null,
    team: [],
    projects: [],
    workPackages: [],
    tasks: [],
    activityTypes: [],
    taskProgressEntries: [],
    stagePlannings: [],
    attachments: [],
    scos: [],
    rateMaster: [],
    rateHistory: [],
    boqs: [],
    boqGroups: [],
    boqItems: [],
    boqSubItems: [],
    // Settings DocTypes (Session 34) — three Single DocTypes that ship in M1.
    // coreSettings + siteExecutionSettings are flat objects (Single records);
    // workspaceStructure is a nested child-table shape (parent definitions +
    // shortcuts children) that drives the Site Execution workspace landing.
    coreSettings: {},
    siteExecutionSettings: {},
    workspaceStructure: { workspace_definitions: [] },
    // Project Type Settings (Session 39 — exploratory). Each record:
    //   { id, name, workPackageLabel, workPackageLabelPlural,
    //     defaultTemplate (string — Project Type name in the templates fixture,
    //                       or '' for no template), enabled }
    // The `name` field is what the user sees and is the join key onto
    // project.type (so seeding tasks/WPs from a record's template still works
    // against the existing fixture file).
    projectTypes: [],
  }),

  getters: {
    rootProjects: (s) => s.projects.filter(p => !p.parentId),
    subProjects: (s) => (parentId) => s.projects.filter(p => p.parentId === parentId),
    projectById: (s) => (id) => s.projects.find(p => p.id === id),
    workPackagesByProject: (s) => (projectId) => {
      const childIds = s.projects.filter(p => p.parentId === projectId).map(p => p.id)
      const ids = [projectId, ...childIds]
      return s.workPackages.filter(wp => ids.includes(wp.projectId))
    },
    tasksByProject: (s) => (projectId) => {
      const childIds = s.projects.filter(p => p.parentId === projectId).map(p => p.id)
      const ids = [projectId, ...childIds]
      return s.tasks.filter(t => ids.includes(t.projectId))
    },
    tasksByWorkPackage: (s) => (wpId) => s.tasks.filter(t => t.workPackageId === wpId),
    taskById: (s) => (id) => s.tasks.find(t => t.id === id),
    workPackageById: (s) => (id) => s.workPackages.find(wp => wp.id === id),

    // ===== Activity Type (master, §13.3 item 16) =====
    // Renamed in Session 31 from "Task Type" to align with proposal §M2 — the
    // proposal reserves task_type as a Select on Task (Activity / Milestone /
    // Inspection). The master here is the construction-activity template
    // (RCC Column Casting / Brick Masonry / etc.) — was misnamed.
    //
    // Not project-scoped — masters live independent of projects, so deleteProject
    // does NOT cascade these. CRUD is on the Activity Type management screen only.
    activityTypeById: (s) => (id) => s.activityTypes.find(at => at.id === id),
    activityTypesByCategory: (s) => (category) => s.activityTypes.filter(at => at.category === category),
    // Filter for the Project Type → Activity Type mapping. An activity type with
    // no applicableProjectTypes (or an empty list) is considered universal.
    activityTypesForProjectType: (s) => (projectType) => s.activityTypes.filter(at => {
      const apt = at.applicableProjectTypes
      if (!apt || !apt.length) return true
      return apt.includes(projectType)
    }),

    // ===== Project Type template engine (§13.3 item 19) =====
    // Returns the JSON template fixture for a project type, or null if no
    // template exists for it (Industrial / Renovation currently have none).
    // The fixtures live at src/data/projectTypeTemplates.js. Session 39
    // promoted Project Type itself to a configurable record (see below) — but
    // the templates themselves remain JSON fixtures keyed by the project type
    // name; the configurable bit is the WP label and which template a type
    // points at.
    templateForProjectType: () => (typeName) => templateForType(typeName),

    // ===== Project Type Settings (Session 39, exploratory) =====
    // Records here own the configurable surface of a project type: the human
    // label for Work Package (Block / Tower / Villa Type / Chainage Segment /
    // …) and which template the type's projects get seeded from. The
    // underlying template data is still the JSON fixture; this slice is the
    // admin-editable wrapper around it.
    projectTypeByName: (s) => (typeName) =>
      s.projectTypes.find(pt => pt.name === typeName) || null,
    projectTypeById: (s) => (id) =>
      s.projectTypes.find(pt => pt.id === id) || null,
    // Active project types (enabled === true) sorted by sort_order. Used by
    // the New Project form's "Project type" dropdown so admins can hide a
    // type without deleting the record. Falls back to all records if no
    // sort_order is set anywhere.
    activeProjectTypes: (s) =>
      s.projectTypes
        .filter(pt => pt.enabled !== false)
        .slice()
        .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)),
    // Resolve the Work Package label for a given project. Honours the
    // Session 36 precedence: Project Type label → site default. The site
    // default lives on Core Settings (workPackageLabel / workPackageLabelPlural)
    // if set there, otherwise falls back to the hardcoded "Work Package(s)".
    workPackageLabelFor: (s) => (project, plural = false) => {
      const type = project ? s.projectTypes.find(pt => pt.name === project.type) : null
      if (type) {
        const v = plural ? type.workPackageLabelPlural : type.workPackageLabel
        if (v) return v
      }
      const siteV = plural ? s.coreSettings?.workPackageLabelPlural : s.coreSettings?.workPackageLabel
      if (siteV) return siteV
      return plural ? 'Work Packages' : 'Work Package'
    },

    // ===== Attachments (§13.3 items 13 + 26) =====
    // Frappe-native shape — `parentDoctype` + `parentId` form the polymorphic
    // back-reference. The store seed and the UI only use 'Project' today; the
    // cascade in deleteProject is doctype-aware so future Task/WP/TPE attach
    // surfaces drop in without store changes.
    attachmentsByParent: (s) => (doctype, parentId) => s.attachments
      .filter(a => a.parentDoctype === doctype && a.parentId === parentId)
      .slice()
      .sort((a, b) => (b.uploadedAt || '').localeCompare(a.uploadedAt || '')),

    // ===== Stage Planning (§13.3 item 18) =====
    // Project-scoped; cascades from deleteProject. `stagePlanningTasks` is an
    // embedded child array on each stage record — NOT a separate slice. Stage
    // Review aggregation (rollup of labour / GL / procurement) is deferred to
    // M3+ per §13.3 — no review getter or computed lives here.
    stagePlanningById: (s) => (id) => s.stagePlannings.find(sp => sp.id === id),
    stagePlanningsByProject: (s) => (projectId) => {
      // Stages on the project itself plus any of its direct subprojects, ordered
      // by plannedStart asc (stale or undated stages fall to the end).
      const childIds = s.projects.filter(p => p.parentId === projectId).map(p => p.id)
      const ids = [projectId, ...childIds]
      return s.stagePlannings
        .filter(sp => ids.includes(sp.project))
        .slice()
        .sort((a, b) => (a.plannedStart || '~').localeCompare(b.plannedStart || '~'))
    },

    // ===== Task Progress Entry (M2 canonical, §13.3 item 17) =====
    // Sorted latest-first (by entryDate desc, then id desc as tiebreaker on same date)
    // so the consumer can just take [0] for "most recent".
    taskProgressEntriesByTask: (s) => (taskId) => s.taskProgressEntries
      .filter(e => e.taskId === taskId)
      .slice()
      .sort((a, b) => {
        const cmp = (b.entryDate || '').localeCompare(a.entryDate || '')
        return cmp !== 0 ? cmp : (b.id || '').localeCompare(a.id || '')
      }),
    latestProgressEntry: (s) => (taskId) => {
      const list = s.taskProgressEntries.filter(e => e.taskId === taskId)
      if (!list.length) return null
      return list.slice().sort((a, b) => {
        const cmp = (b.entryDate || '').localeCompare(a.entryDate || '')
        return cmp !== 0 ? cmp : (b.id || '').localeCompare(a.id || '')
      })[0]
    },
    scosByProject: (s) => (projectId) => {
      const childIds = s.projects.filter(p => p.parentId === projectId).map(p => p.id)
      const ids = [projectId, ...childIds]
      return s.scos.filter(sco => ids.includes(sco.projectId))
    },
    teamMember: (s) => (id) => s.team.find(t => t.id === id),
    // Expanded project team: PM always first, then unique project.team entries,
    // each rehydrated into the full team-member record. Skips IDs that no
    // longer resolve (defensive against stale references).
    projectTeamMembers: (s) => (projectId) => {
      const p = s.projects.find(pp => pp.id === projectId)
      if (!p) return []
      const ids = []
      if (p.pm) ids.push(p.pm)
      for (const uid of (p.team || [])) {
        if (uid && !ids.includes(uid)) ids.push(uid)
      }
      return ids.map(uid => s.team.find(t => t.id === uid)).filter(Boolean)
    },

    // ===== BOQ getters =====
    boqById: (s) => (id) => s.boqs.find(b => b.id === id),
    // BOQs filtered to a project and (recursively) its sub-projects
    boqsByProject: (s) => (projectId) => {
      const childIds = s.projects.filter(p => p.parentId === projectId).map(p => p.id)
      const ids = [projectId, ...childIds]
      return s.boqs.filter(b => ids.includes(b.projectId))
    },
    // The currently-Approved revision for a project (single live BOQ)
    activeBoqForProject: (s) => (projectId) => {
      return s.boqs.find(b => b.projectId === projectId && b.status === 'Approved')
    },
    boqGroupsByBoq: (s) => (boqId) => s.boqGroups.filter(g => g.boqId === boqId).slice().sort((a,b) => a.order - b.order),
    boqItemsByGroup: (s) => (groupId) => s.boqItems.filter(i => i.groupId === groupId),
    boqItemsByBoq: (s) => (boqId) => s.boqItems.filter(i => i.boqId === boqId),
    boqSubItemsByItem: (s) => (itemId) => s.boqSubItems.filter(si => si.itemId === itemId),

    // Rollups — totals on a BOQ
    boqTotals: (s) => (boqId) => {
      const items = s.boqItems.filter(i => i.boqId === boqId)
      const planned = items.reduce((a,i) => a + (i.plannedAmount || 0), 0)
      const actual  = items.reduce((a,i) => a + (i.actualAmount  || 0), 0)
      const variance = actual - planned
      const variancePct = planned ? (variance / planned) * 100 : 0
      return { planned, actual, variance, variancePct, itemCount: items.length }
    },

    // ===== Rate Master =====
    rateById: (s) => (id) => s.rateMaster.find(r => r.id === id),
    rateHistoryFor: (s) => (rateId) => s.rateHistory.filter(h => h.rateMasterId === rateId).slice().sort((a,b) => a.effectiveDate.localeCompare(b.effectiveDate)),

    // ===== Aggregate KPIs =====
    activeProjectsCount: (s) => s.projects.filter(p => !p.parentId && p.status === 'Active').length,
    openTasksCount: (s) => s.tasks.filter(t => t.status !== 'Completed' && t.status !== 'Cancelled').length,
    pendingScosCount: (s) => s.scos.filter(s => s.status === 'Pending Approval').length,
    totalOrderBook: (s) => s.projects.filter(p => !p.parentId && p.status !== 'Completed').reduce((a, p) => a + (p.budget || 0), 0),

    activeBoqsCount: (s) => s.boqs.filter(b => b.status === 'Approved').length,
    draftBoqsCount: (s) => s.boqs.filter(b => b.status === 'Draft').length,
    submittedBoqsCount: (s) => s.boqs.filter(b => b.status === 'Submitted').length,

    // ===== Role system (see src/data/roles.js, CLAUDE.md §12) =====
    currentRole: (s) => ROLES.find(r => r.id === s.role) || ROLES.find(r => r.id === DEFAULT_ROLE),
    // Workspace slugs visible to the active role, ordered per WORKSPACE_ORDER[roleId].
    // A slug listed in WORKSPACE_ORDER but null in WORKSPACE_VISIBILITY is filtered out.
    visibleWorkspaces: (s) => {
      const order = WORKSPACE_ORDER[s.role] || []
      return order.filter(slug => {
        const wsMap = WORKSPACE_VISIBILITY[slug]
        return wsMap && wsMap[s.role] != null
      })
    },
    // Function getter: returns the access level for the active role on a given workspace,
    // or null if hidden. Use this to gate CTAs / route guards downstream.
    workspaceAccess: (s) => (slug) => {
      const wsMap = WORKSPACE_VISIBILITY[slug]
      if (!wsMap) return null
      return wsMap[s.role] ?? null
    },

    // ===== Company (§14) =====
    // Full company object for the active id (defensive — falls back to the first
    // company if the active id has been removed from the slice).
    currentCompany: (s) => s.companies.find(c => c.id === s.activeCompany) || s.companies[0] || null,
    companyById: (s) => (id) => s.companies.find(c => c.id === id) || null,
    // ===== Customer master (Session 40) =====
    // Mirrors ERPNext Customer DocType. Sorted by name for the New Project
    // dropdown. The join key onto project.client is the customer's `name`.
    sortedCustomers: (s) => s.customers.slice().sort((a, b) => a.name.localeCompare(b.name)),
    customerById:    (s) => (id)   => s.customers.find(c => c.id === id) || null,
    customerByName:  (s) => (name) => s.customers.find(c => c.name === name) || null,
    // Per §14.3 the UI hides the company switcher / column / select when there's
    // only one company — single-company users never see the field.
    isMultiCompany: (s) => s.companies.length > 1,
    // Project count per company — used by the Settings → Companies list and by
    // the delete-guard error message (which projects reference this company?).
    projectsByCompany: (s) => (companyId) => s.projects.filter(p => p.company === companyId),

    // ===== Role helpers =====
    // System Manager (admin) gating per §12.1. Settings tiles like Users /
    // Custom Fields / Workflows hide for non-admin per Session 32 design.
    // Session 34: admin-like predicate. BSA (BuildSuite Administrator) and the
    // System Manager (admin) both see admin-only Settings tiles. Per §12.1 they
    // coexist — Admin owns Frappe-platform admin, BSA owns BuildSuite-product
    // admin. Both gate the same Settings tiles in this prototype since the
    // distinction is conceptual; production Frappe would split via real Role
    // records + permissions.
    isAdmin: (s) => s.role === 'admin' || s.role === 'bsa',
    // Narrower getter for BSA-only surfaces (Workspace Structure Settings is
    // the canonical example — only BSA can reconfigure workspace shortcuts).
    isBSA: (s) => s.role === 'bsa',

    // ===== Settings (Session 34) =====
    // Resolve a workspace definition by slug. Returns null if not configured —
    // the Site Execution landing falls back to a hardcoded message in that case.
    workspaceDefinitionBySlug: (s) => (slug) =>
      s.workspaceStructure.workspace_definitions.find(d => d.workspace_slug === slug) || null,
    // Shortcuts visible to the active role for a given workspace slug. Per the
    // §12.3 visibility matrix and the per-shortcut visible_to_roles override.
    // null visible_to_roles on a shortcut/definition = "no role restriction"
    // (anyone who can see the workspace sees the shortcut).
    visibleShortcutsFor: (s) => (slug) => {
      const def = s.workspaceStructure.workspace_definitions.find(d => d.workspace_slug === slug)
      if (!def || !def.enabled) return []
      // Definition-level role gate first
      if (def.visible_to_roles && !def.visible_to_roles.includes(s.role)) return []
      return (def.shortcuts || [])
        .filter(sc => !sc.visible_to_roles || sc.visible_to_roles.includes(s.role))
        .slice()
        .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    },
  },

  actions: {
    hydrate() {
      if (this.hydrated) return
      // Role lives in its own localStorage key, independent of the main data payload.
      // Defensive: if the stored id is no longer in ROLES, fall back to admin.
      const storedRole = loadRoleFromStorage()
      const validRoleIds = ROLES.map(r => r.id)
      this.role = (storedRole && validRoleIds.includes(storedRole)) ? storedRole : DEFAULT_ROLE
      // Theme is independently persisted — same pattern as role.
      const storedTheme = loadThemeFromStorage()
      this.theme = (storedTheme === 'dark' || storedTheme === 'light') ? storedTheme : DEFAULT_THEME
      const stored = loadFromStorage()
      if (stored) {
        this.user = stored.user
        this.team = stored.team
        // Companies first — back-compat fallback for payloads predating §14.
        this.companies = stored.companies ?? JSON.parse(JSON.stringify(seedData.companies))
        // Session 40 — Customer master with seed fallback.
        this.customers = stored.customers ?? JSON.parse(JSON.stringify(seedData.customers))
        this.projects = stored.projects
        this.workPackages = stored.workPackages
        this.tasks = stored.tasks
        this.scos = stored.scos
        // Backwards-compatible hydration: if older localStorage exists without BOQ keys
        // (or, since M2 prep, without the taskProgressEntries / activityTypes keys),
        // fall back to seed for those slices so the new screens have data to render.
        //
        // §M2 rename migration (Session 31): pre-rename payloads stored the slice as
        // `taskTypes`. If we find that key, lift it into `activityTypes` so the user
        // keeps any local edits to their master records. Tasks themselves keep their
        // old `taskType` Link values during this migration (the field is just renamed
        // to `activityType` via the seed; if a stored task has `taskType` we copy
        // it onto `activityType` below before the persist).
        this.activityTypes       = stored.activityTypes ?? stored.taskTypes ?? JSON.parse(JSON.stringify(seedData.activityTypes))
        this.taskProgressEntries = stored.taskProgressEntries ?? JSON.parse(JSON.stringify(seedData.taskProgressEntries))
        this.stagePlannings      = stored.stagePlannings      ?? JSON.parse(JSON.stringify(seedData.stagePlannings))
        this.attachments         = stored.attachments         ?? JSON.parse(JSON.stringify(seedData.attachments))
        this.rateMaster  = stored.rateMaster  ?? JSON.parse(JSON.stringify(seedData.rateMaster))
        this.rateHistory = stored.rateHistory ?? JSON.parse(JSON.stringify(seedData.rateHistory))
        this.boqs        = stored.boqs        ?? JSON.parse(JSON.stringify(seedData.boqs))
        this.boqGroups   = stored.boqGroups   ?? JSON.parse(JSON.stringify(seedData.boqGroups))
        this.boqItems    = stored.boqItems    ?? JSON.parse(JSON.stringify(seedData.boqItems))
        this.boqSubItems = stored.boqSubItems ?? JSON.parse(JSON.stringify(seedData.boqSubItems))
        // Session 34: Settings DocTypes. coreSettings + siteExecutionSettings
        // are merged (stored ∪ seed defaults) so adding new fields to the seed
        // surfaces them without wiping user-set values. workspaceStructure
        // takes stored if present, else the seed (parent + child arrays).
        this.coreSettings          = { ...JSON.parse(JSON.stringify(seedData.coreSettings)),          ...(stored.coreSettings          || {}) }
        this.siteExecutionSettings = { ...JSON.parse(JSON.stringify(seedData.siteExecutionSettings)), ...(stored.siteExecutionSettings || {}) }
        this.workspaceStructure    = stored.workspaceStructure ?? JSON.parse(JSON.stringify(seedData.workspaceStructure))
        // Session 39 — projectTypes slice (exploratory). Seed-fallback so older
        // payloads continue to work.
        this.projectTypes          = stored.projectTypes        ?? JSON.parse(JSON.stringify(seedData.projectTypes))
        // Session 38 — strip retired Site Execution shortcuts from any stored
        // workspace definition: WSST-002 (Work Packages), WSST-004 (Stage
        // Planning), WSST-006 (Scope Change Orders). All three are still
        // reachable via Project Detail tabs / direct URLs; just not surfaced
        // as workspace tiles. Idempotent — only marks dirty if rows were
        // actually present. New (post-S38) localStorage never had them.
        const RETIRED_SITE_EXEC_SHORTCUTS = ['WSST-002', 'WSST-004', 'WSST-006']
        let workspaceMigrationDirty = false
        for (const def of (this.workspaceStructure.workspace_definitions || [])) {
          if (def.workspace_slug !== 'site-execution') continue
          const before = (def.shortcuts || []).length
          def.shortcuts = (def.shortcuts || []).filter(s => !RETIRED_SITE_EXEC_SHORTCUTS.includes(s.id))
          if (def.shortcuts.length !== before) workspaceMigrationDirty = true
        }
        // §M2 task field migration: stored tasks may still have `taskType` (old
        // field name) instead of `activityType`. Mirror the value over and stamp
        // a default `task_type` of 'Activity' on any task that lacks it.
        let taskMigrationDirty = false
        for (const t of this.tasks) {
          if (t.taskType !== undefined && t.activityType === undefined) {
            t.activityType = t.taskType
            delete t.taskType
            taskMigrationDirty = true
          }
          if (!t.task_type) {
            t.task_type = 'Activity'
            taskMigrationDirty = true
          }
        }
        if (!stored.rateMaster || !stored.boqs || !stored.taskProgressEntries || !stored.activityTypes || !stored.stagePlannings || !stored.attachments || !stored.companies || !stored.customers || !stored.coreSettings || !stored.siteExecutionSettings || !stored.workspaceStructure || !stored.projectTypes || taskMigrationDirty || workspaceMigrationDirty) this._persist()
      } else {
        this.user = seedData.user
        this.team = seedData.team
        this.companies   = JSON.parse(JSON.stringify(seedData.companies))
        this.customers   = JSON.parse(JSON.stringify(seedData.customers))
        this.projects    = JSON.parse(JSON.stringify(seedData.projects))
        this.workPackages= JSON.parse(JSON.stringify(seedData.workPackages))
        this.tasks       = JSON.parse(JSON.stringify(seedData.tasks))
        this.activityTypes       = JSON.parse(JSON.stringify(seedData.activityTypes))
        this.taskProgressEntries = JSON.parse(JSON.stringify(seedData.taskProgressEntries))
        this.stagePlannings      = JSON.parse(JSON.stringify(seedData.stagePlannings))
        this.attachments         = JSON.parse(JSON.stringify(seedData.attachments))
        this.scos        = JSON.parse(JSON.stringify(seedData.scos))
        this.rateMaster  = JSON.parse(JSON.stringify(seedData.rateMaster))
        this.rateHistory = JSON.parse(JSON.stringify(seedData.rateHistory))
        this.boqs        = JSON.parse(JSON.stringify(seedData.boqs))
        this.boqGroups   = JSON.parse(JSON.stringify(seedData.boqGroups))
        this.boqItems    = JSON.parse(JSON.stringify(seedData.boqItems))
        this.boqSubItems = JSON.parse(JSON.stringify(seedData.boqSubItems))
        // Session 34 — Settings DocTypes from seed defaults (first-run branch).
        this.coreSettings          = JSON.parse(JSON.stringify(seedData.coreSettings))
        this.siteExecutionSettings = JSON.parse(JSON.stringify(seedData.siteExecutionSettings))
        this.workspaceStructure    = JSON.parse(JSON.stringify(seedData.workspaceStructure))
        // Session 39 — Project Type Settings (exploratory).
        this.projectTypes          = JSON.parse(JSON.stringify(seedData.projectTypes))
        this._persist()
      }
      // Resolve active company AFTER companies slice is populated. Defensive: if
      // the stored id is no longer present (companies removed from the fixture),
      // fall back to the first available company or the DEFAULT_COMPANY_ID seed.
      const storedCompany = loadCompanyFromStorage()
      const validCompanyIds = this.companies.map(c => c.id)
      this.activeCompany = (storedCompany && validCompanyIds.includes(storedCompany))
        ? storedCompany
        : (this.companies[0]?.id || DEFAULT_COMPANY_ID)
      // Backfill `company` onto child records that predate §14. Idempotent — only
      // sets the field where it's missing. Simulates the production hook that
      // would auto-populate `company` on cascade.
      this._backfillCompany()
      this.hydrated = true
    },

    // §14 — backfill `company` onto child records based on their parent project.
    // Idempotent. Called once from hydrate(). The matching production hook lives
    // server-side in Frappe; this is the prototype simulation.
    _backfillCompany() {
      let dirty = false
      // First pass: ensure every project has a company. Stale localStorage from
      // pre-§14 sessions may have projects without the field — fall back to the
      // active company so child records have something to derive from.
      const fallback = this.activeCompany || (this.companies[0]?.id)
      for (const p of this.projects) {
        if (!p.company && fallback) {
          // Subprojects inherit from their parent if available.
          const parent = p.parentId ? this.projects.find(x => x.id === p.parentId) : null
          p.company = parent?.company || fallback
          dirty = true
        }
      }
      const projectCompany = new Map(this.projects.map(p => [p.id, p.company]))
      const stamp = (record, company) => {
        if (record.company || !company) return
        record.company = company
        dirty = true
      }
      for (const wp of this.workPackages) stamp(wp, projectCompany.get(wp.projectId))
      for (const t of this.tasks)         stamp(t,  projectCompany.get(t.projectId))
      // Tasks now have company; derive TPE company from task → project.
      const taskCompany = new Map(this.tasks.map(t => [t.id, t.company]))
      for (const e of this.taskProgressEntries) stamp(e, taskCompany.get(e.taskId))
      for (const sp of this.stagePlannings)     stamp(sp, projectCompany.get(sp.project))
      for (const s of this.scos)                stamp(s,  projectCompany.get(s.projectId))
      for (const b of this.boqs)                stamp(b,  projectCompany.get(b.projectId))
      // Attachments — only Project parents today. Future Task / WP / TPE attach
      // surfaces would extend this lookup.
      for (const a of this.attachments) {
        if (a.parentDoctype === 'Project') stamp(a, projectCompany.get(a.parentId))
      }
      if (dirty) this._persist()
    },

    _persist() {
      saveToStorage(this.$state)
    },

    resetAll() {
      localStorage.removeItem(STORAGE_KEY)
      this.hydrated = false
      this.hydrate()
    },

    // ===== Role (UI preference, persisted to ROLE_STORAGE_KEY, NOT _persist()) =====
    setRole(roleId) {
      const validRoleIds = ROLES.map(r => r.id)
      if (!validRoleIds.includes(roleId)) return
      this.role = roleId
      saveRoleToStorage(roleId)
    },

    // ===== Theme (UI preference, persisted to THEME_STORAGE_KEY) =====
    setTheme(theme) {
      if (theme !== 'light' && theme !== 'dark') return
      this.theme = theme
      saveThemeToStorage(theme)
    },
    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    },

    // ===== Active company (UI preference, persisted to COMPANY_STORAGE_KEY) =====
    // Same independent-persistence pattern as setRole. Validates against the
    // companies slice (not the static COMPANIES fixture import) so editing the
    // seed after first run doesn't strand the user on a deleted id.
    setActiveCompany(companyId) {
      if (!this.companies.find(c => c.id === companyId)) return
      this.activeCompany = companyId
      saveCompanyToStorage(companyId)
    },

    // ===== Settings DocTypes (Session 34) =====
    // Three Single DocTypes per the M1 Block-B decision. Production each is a
    // Frappe Single record with one row; the prototype represents them as
    // store slices with shallow merges. Mutation actions are admin-or-BSA
    // gated at the UI layer (the store doesn't enforce — same pattern as the
    // Company CRUD).
    updateCoreSettings(patch) {
      this.coreSettings = { ...this.coreSettings, ...patch }
      this._persist()
      return this.coreSettings
    },
    updateSiteExecutionSettings(patch) {
      this.siteExecutionSettings = { ...this.siteExecutionSettings, ...patch }
      this._persist()
      return this.siteExecutionSettings
    },

    // Workspace Structure CRUD — nested child-table shape. Parent rows live in
    // workspace_definitions; shortcuts live as embedded children on each parent.
    // Same model as stagePlanningTasks on stagePlannings.
    addWorkspaceDefinition(data) {
      const id = uid('WSDEF')
      const def = {
        id,
        workspace_slug: data.workspace_slug || '',
        display_name: data.display_name || 'Untitled Workspace',
        enabled: data.enabled !== false,
        visible_to_roles: data.visible_to_roles || null,
        shortcuts: Array.isArray(data.shortcuts) ? data.shortcuts.slice() : [],
      }
      this.workspaceStructure.workspace_definitions.push(def)
      this._persist()
      return def
    },
    updateWorkspaceDefinition(id, patch) {
      const idx = this.workspaceStructure.workspace_definitions.findIndex(d => d.id === id)
      if (idx === -1) return null
      const merged = { ...this.workspaceStructure.workspace_definitions[idx], ...patch }
      // shortcuts is a child array — only replace if patch explicitly passes one.
      if (patch.shortcuts === undefined) merged.shortcuts = this.workspaceStructure.workspace_definitions[idx].shortcuts
      this.workspaceStructure.workspace_definitions[idx] = merged
      this._persist()
      return merged
    },
    deleteWorkspaceDefinition(id) {
      this.workspaceStructure.workspace_definitions = this.workspaceStructure.workspace_definitions.filter(d => d.id !== id)
      this._persist()
    },
    // Shortcut child rows — patch the parent definition's array.
    addWorkspaceShortcut(defId, rowData) {
      const idx = this.workspaceStructure.workspace_definitions.findIndex(d => d.id === defId)
      if (idx === -1) return null
      const existing = this.workspaceStructure.workspace_definitions[idx].shortcuts || []
      const nextOrder = (existing.reduce((max, s) => Math.max(max, s.sort_order || 0), 0)) + 1
      const row = {
        id: uid('WSST'),
        label: rowData.label || 'New shortcut',
        icon: rowData.icon || '🔗',
        route_path: rowData.route_path || '/',
        visible_to_roles: rowData.visible_to_roles || null,
        sort_order: Number(rowData.sort_order) || nextOrder,
      }
      const next = [...existing, row]
      this.workspaceStructure.workspace_definitions[idx] = {
        ...this.workspaceStructure.workspace_definitions[idx],
        shortcuts: next,
      }
      this._persist()
      return row
    },
    updateWorkspaceShortcut(defId, shortcutId, patch) {
      const idx = this.workspaceStructure.workspace_definitions.findIndex(d => d.id === defId)
      if (idx === -1) return null
      const rows = (this.workspaceStructure.workspace_definitions[idx].shortcuts || []).map(s => {
        if (s.id !== shortcutId) return s
        const merged = { ...s, ...patch }
        if (patch.sort_order !== undefined) merged.sort_order = Number(patch.sort_order) || 0
        return merged
      })
      this.workspaceStructure.workspace_definitions[idx] = {
        ...this.workspaceStructure.workspace_definitions[idx],
        shortcuts: rows,
      }
      this._persist()
      return rows.find(s => s.id === shortcutId) || null
    },
    removeWorkspaceShortcut(defId, shortcutId) {
      const idx = this.workspaceStructure.workspace_definitions.findIndex(d => d.id === defId)
      if (idx === -1) return
      const rows = (this.workspaceStructure.workspace_definitions[idx].shortcuts || []).filter(s => s.id !== shortcutId)
      this.workspaceStructure.workspace_definitions[idx] = {
        ...this.workspaceStructure.workspace_definitions[idx],
        shortcuts: rows,
      }
      this._persist()
    },

    // ===== Company CRUD (Session 32 — Settings page) =====
    // Note: companies are org-wide masters (§14.4) — not project-scoped. Deletion
    // is blocked when any project references the company (Frappe-standard
    // LinkExistsError pattern, per the user's design-question choice).
    addCompany(data) {
      // ID is user-provided OR auto-generated. We normalise to uppercase and
      // ensure uniqueness — if a collision, append a numeric suffix.
      let id = (data.id || '').trim().toUpperCase()
      if (!id) id = uid('CMP').toUpperCase()
      if (this.companies.find(c => c.id === id)) {
        let n = 2
        while (this.companies.find(c => c.id === `${id}-${n}`)) n++
        id = `${id}-${n}`
      }
      const company = {
        id,
        name: (data.name || 'Untitled Company').trim(),
        shortName: (data.shortName || data.name || 'Company').trim(),
        description: (data.description || '').trim(),
        color: data.color || 'bg-ink-600',
      }
      this.companies.push(company)
      this._persist()
      return company
    },
    updateCompany(id, patch) {
      const idx = this.companies.findIndex(c => c.id === id)
      if (idx === -1) return null
      // ID is locked after create — strip it from any patch to avoid silent rename.
      const safe = { ...patch }
      delete safe.id
      this.companies[idx] = { ...this.companies[idx], ...safe }
      this._persist()
      return this.companies[idx]
    },
    deleteCompany(id) {
      // Refuse if any project references this company. Mirror of Frappe's
      // LinkExistsError — return a result the UI can render meaningfully.
      const linked = this.projects.filter(p => p.company === id)
      if (linked.length) {
        return {
          ok: false,
          reason: 'referenced',
          projects: linked.map(p => ({ id: p.id, name: p.name, code: p.code })),
        }
      }
      const idx = this.companies.findIndex(c => c.id === id)
      if (idx === -1) return { ok: false, reason: 'not_found' }
      this.companies.splice(idx, 1)
      // If the deleted company was the active one, pivot to the first remaining
      // company so the topbar switcher doesn't strand on a missing id.
      if (this.activeCompany === id) {
        const next = this.companies[0]?.id
        if (next) {
          this.activeCompany = next
          saveCompanyToStorage(next)
        }
      }
      this._persist()
      return { ok: true }
    },

    // ===== Projects =====
    // `seedDefaultStages` (default true) controls the §13.3 item 19 hook: after
    // create, if the project type has a template, default Stage Planning rows
    // are inserted with plannedStart/End offset from project.startDate. Callers
    // creating SUBprojects should pass `seedDefaultStages: false` — the parent
    // project already owns the stage timeline. NewProjectView surfaces this as
    // a checkbox in the UI and defaults it based on whether parentId is set.
    addProject(data) {
      const id = uid('PROJ')
      // Nested subprojects are not allowed — if the supplied parentId points
      // at a record that is itself a subproject, drop the parentId so the
      // new record lands as top-level. This protects against URL manipulation
      // (UI already hides the "+ Add Subproject" button on a subproject).
      let parentId = data.parentId || null
      if (parentId) {
        const parent = this.projects.find(p => p.id === parentId)
        if (parent && parent.parentId) parentId = null
      }
      // §14 — Company is required on Project. Subprojects inherit from the
      // parent (consistent with the auto-derive rule on child docs); top-level
      // projects fall back to the active company when not explicitly set.
      let company = data.company
      if (!company && parentId) {
        const parent = this.projects.find(p => p.id === parentId)
        if (parent) company = parent.company
      }
      if (!company) company = this.activeCompany
      const project = {
        id,
        code: data.code || id.slice(-6),
        name: data.name,
        client: data.client || '',
        status: data.status || 'Active',
        priority: data.priority || 'Medium',
        type: data.type || 'Commercial',
        company,
        startDate: data.startDate || new Date().toISOString().slice(0, 10),
        endDate: data.endDate || '',
        budget: Number(data.budget) || 0,
        progress: 0,
        pm: data.pm || (this.team[0] && this.team[0].id),
        team: Array.isArray(data.team) ? [...data.team] : [],
        location: data.location || '',
        description: data.description || '',
        parentId,
        createdAt: new Date().toISOString(),
      }
      this.projects.unshift(project)
      // Template-driven Stage Planning seed (§13.3 item 19). Default ON; opt-out
      // via `seedDefaultStages: false`. We persist once at the very end rather
      // than after each stage to keep the localStorage write count low.
      const seedFlag = data.seedDefaultStages !== false
      if (seedFlag) {
        this._instantiateStagesFromTemplate(project)
      }
      // Session 39 — optional Work Packages + Tasks seed from the project type
      // template. Off by default; opt-in via seedDefaultWorkPackagesAndTasks
      // on NewProjectView. Subprojects don't seed WPs/tasks (parent owns the
      // breakdown structure).
      if (data.seedDefaultWorkPackagesAndTasks === true && !project.parentId) {
        this._instantiateWorkPackagesFromTemplate(project)
      }
      this._persist()
      return project
    },
    updateProject(id, patch) {
      const idx = this.projects.findIndex(p => p.id === id)
      if (idx === -1) return null
      this.projects[idx] = { ...this.projects[idx], ...patch, updatedAt: new Date().toISOString() }
      this._persist()
      return this.projects[idx]
    },
    // Project team membership — append-or-skip on add (no duplicates),
    // filter on remove. PM is always considered a member implicitly; the
    // store doesn't enforce that — the UI does (renders PM at the top of
    // the team list regardless of project.team).
    addProjectTeamMember(projectId, userId) {
      const idx = this.projects.findIndex(p => p.id === projectId)
      if (idx === -1 || !userId) return null
      const team = Array.isArray(this.projects[idx].team) ? [...this.projects[idx].team] : []
      if (!team.includes(userId)) team.push(userId)
      this.projects[idx] = { ...this.projects[idx], team, updatedAt: new Date().toISOString() }
      this._persist()
      return this.projects[idx]
    },
    removeProjectTeamMember(projectId, userId) {
      const idx = this.projects.findIndex(p => p.id === projectId)
      if (idx === -1) return null
      const team = (this.projects[idx].team || []).filter(uid => uid !== userId)
      this.projects[idx] = { ...this.projects[idx], team, updatedAt: new Date().toISOString() }
      this._persist()
      return this.projects[idx]
    },
    deleteProject(id) {
      const subIds = this.projects.filter(p => p.parentId === id).map(p => p.id)
      const allIds = [id, ...subIds]
      // Collect task IDs before deletion so we can cascade their progress entries.
      const deletedTaskIds = this.tasks.filter(t => allIds.includes(t.projectId)).map(t => t.id)
      // Collect all the IDs across cascaded record types BEFORE filtering, so
      // the attachments sweep can match against any parent doctype's id set.
      const deletedWpIds = this.workPackages.filter(wp => allIds.includes(wp.projectId)).map(wp => wp.id)
      const deletedTpeIds = this.taskProgressEntries.filter(e => deletedTaskIds.includes(e.taskId)).map(e => e.id)
      const deletedStageIds = this.stagePlannings.filter(s => allIds.includes(s.project)).map(s => s.id)
      this.projects = this.projects.filter(p => !allIds.includes(p.id))
      this.workPackages = this.workPackages.filter(wp => !allIds.includes(wp.projectId))
      this.tasks = this.tasks.filter(t => !allIds.includes(t.projectId))
      this.taskProgressEntries = this.taskProgressEntries.filter(e => !deletedTaskIds.includes(e.taskId))
      this.stagePlannings = this.stagePlannings.filter(s => !allIds.includes(s.project))
      this.scos = this.scos.filter(s => !allIds.includes(s.projectId))
      // Attachments cascade — drop any attachment whose parent record was just
      // deleted. Recursive across all the cascaded doctypes — today only Project
      // attachments exist in the prototype, but this is the future-proof shape
      // for when Task / WP / TPE gain attachments in later milestones.
      this.attachments = this.attachments.filter(a => {
        if (a.parentDoctype === 'Project'             && allIds.includes(a.parentId))            return false
        if (a.parentDoctype === 'Work Package'        && deletedWpIds.includes(a.parentId))      return false
        if (a.parentDoctype === 'Task'                && deletedTaskIds.includes(a.parentId))    return false
        if (a.parentDoctype === 'Task Progress Entry' && deletedTpeIds.includes(a.parentId))     return false
        if (a.parentDoctype === 'Stage Planning'      && deletedStageIds.includes(a.parentId))   return false
        return true
      })
      // Cascade-delete BOQs and their nested rows
      const boqIds = this.boqs.filter(b => allIds.includes(b.projectId)).map(b => b.id)
      this.boqs        = this.boqs.filter(b => !allIds.includes(b.projectId))
      this.boqGroups   = this.boqGroups.filter(g => !boqIds.includes(g.boqId))
      this.boqItems    = this.boqItems.filter(i => !boqIds.includes(i.boqId))
      this.boqSubItems = this.boqSubItems.filter(si => !boqIds.includes(si.boqId))
      this._persist()
    },

    // ===== Work Packages =====
    addWorkPackage(data) {
      const id = uid('WP')
      // §14.2 — Company auto-derived from parent project.
      const parentProject = this.projects.find(p => p.id === data.projectId)
      const wp = {
        id, projectId: data.projectId, code: data.code || id.slice(-6),
        company: parentProject?.company || this.activeCompany,
        name: data.name, description: data.description || '',
        status: data.status || 'Planned', progress: 0,
        budget: Number(data.budget) || 0,
        startDate: data.startDate || '', endDate: data.endDate || '',
        owner: data.owner || (this.team[0] && this.team[0].id),
      }
      this.workPackages.unshift(wp)
      this._persist()
      return wp
    },
    updateWorkPackage(id, patch) {
      const idx = this.workPackages.findIndex(wp => wp.id === id)
      if (idx === -1) return null
      this.workPackages[idx] = { ...this.workPackages[idx], ...patch }
      this._persist()
      return this.workPackages[idx]
    },
    deleteWorkPackage(id) {
      // Collect task IDs before deletion so we can cascade their progress entries.
      const deletedTaskIds = this.tasks.filter(t => t.workPackageId === id).map(t => t.id)
      const deletedTpeIds = this.taskProgressEntries.filter(e => deletedTaskIds.includes(e.taskId)).map(e => e.id)
      this.workPackages = this.workPackages.filter(wp => wp.id !== id)
      this.tasks = this.tasks.filter(t => t.workPackageId !== id)
      this.taskProgressEntries = this.taskProgressEntries.filter(e => !deletedTaskIds.includes(e.taskId))
      // Attachments cascade (no UI for WP/Task/TPE attachments yet, but the
      // store contract should stay coherent — same pattern as deleteProject).
      this.attachments = this.attachments.filter(a => {
        if (a.parentDoctype === 'Work Package'        && a.parentId === id)                    return false
        if (a.parentDoctype === 'Task'                && deletedTaskIds.includes(a.parentId))  return false
        if (a.parentDoctype === 'Task Progress Entry' && deletedTpeIds.includes(a.parentId))   return false
        return true
      })
      this._persist()
    },

    // ===== Tasks =====
    // task_type per proposal M2 — drives progress flow:
    //   - Activity: standard progress entry flow (current behavior)
    //   - Milestone: checkpoint, no qty progress (status-only, future M2 work)
    //   - Inspection: pass/fail gate (future M2 — inspection workflow)
    // activityType is separate — optional Link to Activity Type master providing
    // labour mix + productivity defaults.
    addTask(data) {
      const id = uid('TSK')
      // §14.2 — Company auto-derived from parent project.
      const parentProject = this.projects.find(p => p.id === data.projectId)
      // Validate task_type against the proposal-locked enum. Invalid values
      // fall back to 'Activity' (don't throw — keeps the create flow resilient).
      const VALID_TASK_TYPES = ['Activity', 'Milestone', 'Inspection']
      const task_type = VALID_TASK_TYPES.includes(data.task_type) ? data.task_type : 'Activity'
      const task = {
        id, projectId: data.projectId, workPackageId: data.workPackageId || null,
        company: parentProject?.company || this.activeCompany,
        task_type,
        activityType: data.activityType || null,
        name: data.name, description: data.description || '',
        status: data.status || 'Open', priority: data.priority || 'Medium',
        assignee: data.assignee || (this.team[0] && this.team[0].id),
        startDate: data.startDate || '', endDate: data.endDate || '',
        progress: 0,
        estimatedHours: Number(data.estimatedHours) || 0,
        actualHours: 0,
      }
      this.tasks.unshift(task)
      this._persist()
      return task
    },
    updateTask(id, patch) {
      const idx = this.tasks.findIndex(t => t.id === id)
      if (idx === -1) return null
      const merged = { ...this.tasks[idx], ...patch }
      // Validate task_type if the patch touches it — fall back to 'Activity'
      // on anything outside the proposal-locked enum.
      if (patch.task_type !== undefined) {
        const VALID = ['Activity', 'Milestone', 'Inspection']
        merged.task_type = VALID.includes(patch.task_type) ? patch.task_type : 'Activity'
      }
      this.tasks[idx] = merged
      this._persist()
      return this.tasks[idx]
    },
    deleteTask(id) {
      // Collect TPE ids BEFORE the filter so attachments cascade can match them.
      const deletedTpeIds = this.taskProgressEntries.filter(e => e.taskId === id).map(e => e.id)
      this.tasks = this.tasks.filter(t => t.id !== id)
      this.taskProgressEntries = this.taskProgressEntries.filter(e => e.taskId !== id)
      // Attachments cascade (Task + its TPE attachments).
      this.attachments = this.attachments.filter(a => {
        if (a.parentDoctype === 'Task'                && a.parentId === id)                   return false
        if (a.parentDoctype === 'Task Progress Entry' && deletedTpeIds.includes(a.parentId))  return false
        return true
      })
      this._persist()
    },

    // ===== Activity Type (master, §13.3 item 16) =====
    // Masters are NOT cascaded by deleteProject — they're org-wide setup records,
    // independent of any project. When an Activity Type is deleted, tasks that
    // linked to it keep their `activityType` field as a dangling reference
    // (treated as null by the UI via store.activityTypeById returning undefined).
    // Same model production Frappe uses for Link fields without on_delete: 'Cascade'.
    addActivityType(data) {
      const id = uid('AT')
      const skilled = Number(data.defaultSkilledRatio)
      const safeSkilled = Number.isFinite(skilled) ? Math.min(1, Math.max(0, skilled)) : 0.5
      const type = {
        id,
        name: data.name || 'Untitled Activity Type',
        category: data.category || 'Other',
        description: data.description || '',
        defaultChecklist: Array.isArray(data.defaultChecklist) ? data.defaultChecklist.filter(c => c && c.item) : [],
        defaultSkilledRatio: safeSkilled,
        defaultUnskilledRatio: 1 - safeSkilled,
        expectedProductivityPerManDay: Number(data.expectedProductivityPerManDay) || 0,
        productivityUnit: data.productivityUnit || '',
        applicableProjectTypes: Array.isArray(data.applicableProjectTypes) ? data.applicableProjectTypes.slice() : [],
      }
      this.activityTypes.unshift(type)
      this._persist()
      return type
    },
    updateActivityType(id, patch) {
      const idx = this.activityTypes.findIndex(at => at.id === id)
      if (idx === -1) return null
      const merged = { ...this.activityTypes[idx], ...patch }
      // Keep skilled/unskilled ratios coherent: if skilled is patched, recompute
      // unskilled from it (and vice versa). They must sum to 1.
      if (patch.defaultSkilledRatio !== undefined) {
        const v = Number(patch.defaultSkilledRatio)
        const safe = Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0.5
        merged.defaultSkilledRatio = safe
        merged.defaultUnskilledRatio = 1 - safe
      } else if (patch.defaultUnskilledRatio !== undefined) {
        const v = Number(patch.defaultUnskilledRatio)
        const safe = Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0.5
        merged.defaultUnskilledRatio = safe
        merged.defaultSkilledRatio = 1 - safe
      }
      if (patch.expectedProductivityPerManDay !== undefined) {
        merged.expectedProductivityPerManDay = Number(patch.expectedProductivityPerManDay) || 0
      }
      if (patch.defaultChecklist !== undefined) {
        merged.defaultChecklist = Array.isArray(patch.defaultChecklist) ? patch.defaultChecklist.filter(c => c && c.item) : []
      }
      if (patch.applicableProjectTypes !== undefined) {
        merged.applicableProjectTypes = Array.isArray(patch.applicableProjectTypes) ? patch.applicableProjectTypes.slice() : []
      }
      this.activityTypes[idx] = merged
      this._persist()
      return merged
    },
    deleteActivityType(id) {
      this.activityTypes = this.activityTypes.filter(at => at.id !== id)
      // Do NOT cascade-null tasks' activityType field — dangling Link references
      // are the Frappe-native behavior. UI treats unresolved IDs as no link.
      this._persist()
    },

    // ===== Stage Planning (§13.3 item 18) =====
    // Stages-as-structure. Stage Review (the M3+ scorecard that rolls up labour,
    // procurement, and GL data into a stage-level completion verdict) attaches
    // here later — there's no review action / computed in this prototype.
    addStagePlanning(data) {
      const id = uid('STG')
      // §14.2 — Company auto-derived from parent project.
      const parentProject = this.projects.find(p => p.id === data.project)
      const stage = {
        id,
        stageName: data.stageName || 'Untitled stage',
        project: data.project,
        company: parentProject?.company || this.activeCompany,
        plannedStart: data.plannedStart || '',
        plannedEnd: data.plannedEnd || '',
        plannedTaskCount: Number(data.plannedTaskCount) || 0,
        plannedCompletionPct: Number(data.plannedCompletionPct) || 100,
        description: data.description || '',
        dependencies: Array.isArray(data.dependencies) ? data.dependencies.slice() : [],
        stagePlanningTasks: Array.isArray(data.stagePlanningTasks) ? data.stagePlanningTasks.slice() : [],
      }
      this.stagePlannings.unshift(stage)
      this._persist()
      return stage
    },
    updateStagePlanning(id, patch) {
      const idx = this.stagePlannings.findIndex(sp => sp.id === id)
      if (idx === -1) return null
      const merged = { ...this.stagePlannings[idx], ...patch }
      if (patch.plannedTaskCount     !== undefined) merged.plannedTaskCount     = Number(patch.plannedTaskCount) || 0
      if (patch.plannedCompletionPct !== undefined) merged.plannedCompletionPct = Number(patch.plannedCompletionPct) || 0
      if (patch.dependencies !== undefined) {
        merged.dependencies = Array.isArray(patch.dependencies) ? patch.dependencies.slice() : []
      }
      if (patch.stagePlanningTasks !== undefined) {
        merged.stagePlanningTasks = Array.isArray(patch.stagePlanningTasks) ? patch.stagePlanningTasks.slice() : []
      }
      this.stagePlannings[idx] = merged
      this._persist()
      return merged
    },
    deleteStagePlanning(id) {
      this.stagePlannings = this.stagePlannings.filter(sp => sp.id !== id)
      // Other stages may have this id in their `dependencies` array — clean up so
      // the UI doesn't surface phantom dependency chips.
      this.stagePlannings = this.stagePlannings.map(sp => ({
        ...sp,
        dependencies: (sp.dependencies || []).filter(d => d !== id),
      }))
      this._persist()
    },

    // Stage Planning Task — child table operations. The child rows live on the
    // parent stage record, so each operation patches the parent.
    addStagePlanningTask(stageId, rowData) {
      const idx = this.stagePlannings.findIndex(sp => sp.id === stageId)
      if (idx === -1) return null
      const row = {
        id: uid('SPT'),
        task: rowData.task || null,
        plannedStart: rowData.plannedStart || '',
        plannedEnd: rowData.plannedEnd || '',
        plannedQty: Number(rowData.plannedQty) || 0,
        qtyUnit: rowData.qtyUnit || '',
      }
      const next = [...(this.stagePlannings[idx].stagePlanningTasks || []), row]
      this.stagePlannings[idx] = { ...this.stagePlannings[idx], stagePlanningTasks: next }
      this._persist()
      return row
    },
    updateStagePlanningTask(stageId, sptId, patch) {
      const idx = this.stagePlannings.findIndex(sp => sp.id === stageId)
      if (idx === -1) return null
      const rows = (this.stagePlannings[idx].stagePlanningTasks || []).map(r => {
        if (r.id !== sptId) return r
        const merged = { ...r, ...patch }
        if (patch.plannedQty !== undefined) merged.plannedQty = Number(patch.plannedQty) || 0
        return merged
      })
      this.stagePlannings[idx] = { ...this.stagePlannings[idx], stagePlanningTasks: rows }
      this._persist()
      return rows.find(r => r.id === sptId) || null
    },
    removeStagePlanningTask(stageId, sptId) {
      const idx = this.stagePlannings.findIndex(sp => sp.id === stageId)
      if (idx === -1) return
      const rows = (this.stagePlannings[idx].stagePlanningTasks || []).filter(r => r.id !== sptId)
      this.stagePlannings[idx] = { ...this.stagePlannings[idx], stagePlanningTasks: rows }
      this._persist()
    },

    // ===== Project Type template instantiation (§13.3 item 19) =====
    // Internal helper used by addProject and by seedStagesFromTemplate. Inserts
    // stage records into this.stagePlannings without persisting (the caller is
    // responsible for the single trailing _persist). Returns the array of new
    // stage records, or [] if no template exists for the project's type.
    _instantiateStagesFromTemplate(project) {
      const template = templateForType(project.type)
      if (!template || !Array.isArray(template.defaultStages) || !template.defaultStages.length) return []
      // Pre-allocate IDs so cross-stage dependencies (if templates ever encode
      // them — they don't today) can be wired in one pass. Each template stage
      // gets a new STG- id; deps stay empty for now since templates don't
      // specify them.
      const newStages = template.defaultStages.map((s, i) => ({
        id: uid('STG'),
        stageName: s.stageName,
        project: project.id,
        // §14.2 — derive company from the project this stage belongs to.
        company: project.company,
        plannedStart: addDaysISO(project.startDate, s.offsetStartDays),
        plannedEnd:   addDaysISO(project.startDate, s.offsetEndDays),
        plannedTaskCount: Number(s.plannedTaskCount) || 0,
        plannedCompletionPct: Number(s.plannedCompletionPct) || 100,
        description: s.description || '',
        dependencies: [],
        stagePlanningTasks: [],
        _seededFromTemplate: project.type,  // marker for UI/audit; safe to ignore on reads
        _seedOrder: i,
      }))
      // Append rather than unshift so the existing seed ordering is preserved.
      this.stagePlannings = [...this.stagePlannings, ...newStages]
      return newStages
    },
    // Public action — used by the "+ Seed from Project Type template" button on
    // the Project Detail Stage Planning empty state. Re-running this on a
    // project that already has stages will ADD a full new set on top — it does
    // NOT replace or merge. Callers should check stagePlanningsByProject first
    // and only call this when the project is empty (the UI does).
    seedStagesFromTemplate(projectId) {
      const project = this.projects.find(p => p.id === projectId)
      if (!project) return []
      const newStages = this._instantiateStagesFromTemplate(project)
      if (newStages.length) this._persist()
      return newStages
    },

    // ===== Project Type Settings CRUD (Session 39, exploratory) =====
    // The slice lives under `projectTypes`. Fields: id, name, workPackageLabel,
    // workPackageLabelPlural, defaultTemplate, enabled, sort_order. These
    // records DON'T migrate the existing project.type Select to a Link — that
    // would be a real DocType conversion (M2 scope). Today project.type still
    // stores the human name (e.g. "Commercial"); these records sit alongside
    // and provide configuration keyed by that same name.
    addProjectType(data) {
      const id = uid('PT')
      const nextOrder = (this.projectTypes.reduce((max, pt) => Math.max(max, pt.sort_order || 0), 0)) + 1
      const record = {
        id,
        name: data.name || 'New type',
        workPackageLabel: data.workPackageLabel || '',
        workPackageLabelPlural: data.workPackageLabelPlural || '',
        defaultTemplate: data.defaultTemplate || data.name || '',
        enabled: data.enabled !== false,
        sort_order: Number(data.sort_order) || nextOrder,
      }
      this.projectTypes.push(record)
      this._persist()
      return record
    },
    updateProjectType(id, patch) {
      const idx = this.projectTypes.findIndex(pt => pt.id === id)
      if (idx === -1) return null
      this.projectTypes[idx] = { ...this.projectTypes[idx], ...patch }
      this._persist()
      return this.projectTypes[idx]
    },
    deleteProjectType(id) {
      this.projectTypes = this.projectTypes.filter(pt => pt.id !== id)
      this._persist()
    },

    // ===== Project Type — Work Package + Task instantiation (Session 39) =====
    // Reads defaultWorkPackages + defaultTasks off the template fixture for the
    // project's type and inserts records into this.workPackages + this.tasks.
    // Does NOT persist — caller (addProject) handles the single trailing
    // _persist. Returns { workPackagesCreated, tasksCreated } counts.
    //
    // Honours the configurable WP label by stamping the wp record with the
    // resolved label as `displayLabel` (the resolver still reads from getters
    // at render time; the stamp is just there for forward audit). Tasks are
    // linked to the right WP via the WP's id (we build a code→id map after
    // creating all WPs in the first pass).
    _instantiateWorkPackagesFromTemplate(project) {
      const ptRecord = this.projectTypes.find(pt => pt.name === project.type)
      const templateKey = ptRecord?.defaultTemplate || project.type
      const template = templateForType(templateKey)
      if (!template) return { workPackagesCreated: 0, tasksCreated: 0 }

      const wpDefs   = Array.isArray(template.defaultWorkPackages) ? template.defaultWorkPackages : []
      const taskDefs = Array.isArray(template.defaultTasks)        ? template.defaultTasks        : []

      // Pass 1: create work packages, keep a code → new id map for task linking.
      const codeToId = {}
      const newWps = []
      const sortedWps = wpDefs.slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
      for (const def of sortedWps) {
        const id = uid('WP')
        const wp = {
          id,
          projectId: project.id,
          code: def.code || id.slice(-6),
          company: project.company,
          name: def.name || 'Work Package',
          description: def.description || '',
          status: 'Planned',
          progress: 0,
          budget: Number(def.budget) || 0,
          startDate: project.startDate || '',
          endDate: project.endDate || '',
          owner: project.pm || '',
          _seededFromTemplate: project.type,
        }
        newWps.push(wp)
        codeToId[def.code] = id
      }
      this.workPackages = [...this.workPackages, ...newWps]

      // Pass 2: create tasks, linking workPackageId via the code map.
      const newTasks = []
      const sortedTasks = taskDefs.slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
      for (const def of sortedTasks) {
        const id = uid('TSK')
        const wpId = def.workPackageCode ? (codeToId[def.workPackageCode] || null) : null
        newTasks.push({
          id,
          projectId: project.id,
          workPackageId: wpId,
          company: project.company,
          name: def.name || 'Task',
          description: def.description || '',
          status: 'Open',
          progress: 0,
          priority: def.priority || 'Medium',
          assignee: project.pm || '',
          startDate: project.startDate || '',
          endDate: project.endDate || '',
          estimated_hours: Number(def.estimated_hours) || 0,
          actual_hours: 0,
          task_type: 'Activity',
          _seededFromTemplate: project.type,
        })
      }
      this.tasks = [...this.tasks, ...newTasks]

      return { workPackagesCreated: newWps.length, tasksCreated: newTasks.length }
    },
    // Public action — wired to the "+ Seed work packages & tasks from template"
    // affordance on Project Detail (if/when added). For now used only at create.
    seedWorkPackagesFromTemplate(projectId) {
      const project = this.projects.find(p => p.id === projectId)
      if (!project) return { workPackagesCreated: 0, tasksCreated: 0 }
      const counts = this._instantiateWorkPackagesFromTemplate(project)
      if (counts.workPackagesCreated || counts.tasksCreated) this._persist()
      return counts
    },

    // ===== Attachments (§13.3 items 13 + 26) =====
    // Production uses Frappe's File DocType with persistent storage on disk +
    // referenced from the parent doctype's Attachments sidebar. In the
    // prototype we mirror just the metadata shape — file bytes are held as
    // browser `blob:` URLs created via URL.createObjectURL on upload. **Blob
    // URLs are SESSION-ONLY: they're lost on tab close (the binary lives in
    // the renderer process, not localStorage).** Seed entries have url=null
    // and the UI surfaces that as a "(metadata only)" hint.
    addAttachment(data) {
      const id = uid('ATT')
      // §14.2 — derive company from the parent record. Only `Project` parents
      // are surfaced in M1; the lookup is doctype-aware for future Task/WP/TPE.
      const doctype = data.parentDoctype || 'Project'
      let company = null
      if (doctype === 'Project') company = this.projects.find(p => p.id === data.parentId)?.company
      else if (doctype === 'Task')          company = this.tasks.find(t => t.id === data.parentId)?.company
      else if (doctype === 'Work Package')  company = this.workPackages.find(wp => wp.id === data.parentId)?.company
      else if (doctype === 'Task Progress Entry') company = this.taskProgressEntries.find(e => e.id === data.parentId)?.company
      const att = {
        id,
        parentDoctype: doctype,
        parentId: data.parentId,
        company: company || this.activeCompany,
        fileName: data.fileName || 'untitled',
        mime: data.mime || 'application/octet-stream',
        size: Number(data.size) || 0,
        url: data.url || null,
        uploadedAt: data.uploadedAt || new Date().toISOString(),
        uploadedBy: data.uploadedBy || this.user?.id || (this.team[0] && this.team[0].id),
      }
      this.attachments.unshift(att)
      this._persist()
      return att
    },
    deleteAttachment(id) {
      // Revoke the blob URL so the browser can free the memory the file bytes
      // are holding. Safe even if url is null or wasn't a blob URL (the API
      // tolerates non-blob inputs).
      const att = this.attachments.find(a => a.id === id)
      if (att && att.url && typeof URL !== 'undefined' && URL.revokeObjectURL) {
        try { URL.revokeObjectURL(att.url) } catch (e) { /* ignore — non-blob URL */ }
      }
      this.attachments = this.attachments.filter(a => a.id !== id)
      this._persist()
    },

    // ===== Task Progress Entry (M2 canonical, §13.3 item 17) =====
    // Adding / updating / deleting an entry triggers _recomputeTaskFromEntries
    // which is the prototype's simulation of the M1 server hook: the parent Task's
    // `progress` and `status` get rewritten from the latest entry's `progressPct`.
    //
    // The Task.progress slider in TaskDetailView.vue still calls updateTask directly
    // (pre-M1 path). The two paths coexist for now — the slider's writes are NOT
    // canonical and will be overwritten the next time an entry is added/updated.
    // Phase-4 UI work will route slider edits through addTaskProgressEntry instead.
    addTaskProgressEntry(data) {
      const id = uid('TPE')
      // §14.2 — Company auto-derived from task → project.
      const parentTask = this.tasks.find(t => t.id === data.taskId)
      // Clamp progressPct hard to 0–100. The UI uses min/max on the input
      // for browser-level enforcement; this is the belt-and-braces guard for
      // paste / programmatic writes.
      const clampedPct = Math.max(0, Math.min(100, Number(data.progressPct) || 0))
      const entry = {
        id,
        taskId: data.taskId,
        company: parentTask?.company || this.activeCompany,
        entryDate: data.entryDate || new Date().toISOString().slice(0, 10),
        enteredBy: data.enteredBy || this.user?.id,
        progressPct: clampedPct,
        narrative: data.narrative || '',
        attachments: data.attachments || [],
        skilledLabour: Number(data.skilledLabour) || 0,
        unskilledLabour: Number(data.unskilledLabour) || 0,
        weather: data.weather || '',
        blockerFlag: !!data.blockerFlag,
        blockerNote: data.blockerNote || '',
      }
      this.taskProgressEntries.unshift(entry)
      this._recomputeTaskFromEntries(entry.taskId)
      this._persist()
      return entry
    },
    updateTaskProgressEntry(id, patch) {
      const idx = this.taskProgressEntries.findIndex(e => e.id === id)
      if (idx === -1) return null
      const merged = { ...this.taskProgressEntries[idx], ...patch }
      if (patch.progressPct     !== undefined) merged.progressPct     = Math.max(0, Math.min(100, Number(patch.progressPct) || 0))
      if (patch.skilledLabour   !== undefined) merged.skilledLabour   = Number(patch.skilledLabour) || 0
      if (patch.unskilledLabour !== undefined) merged.unskilledLabour = Number(patch.unskilledLabour) || 0
      if (patch.blockerFlag     !== undefined) merged.blockerFlag     = !!patch.blockerFlag
      this.taskProgressEntries[idx] = merged
      this._recomputeTaskFromEntries(merged.taskId)
      this._persist()
      return merged
    },
    deleteTaskProgressEntry(id) {
      const entry = this.taskProgressEntries.find(e => e.id === id)
      if (!entry) return
      this.taskProgressEntries = this.taskProgressEntries.filter(e => e.id !== id)
      this._recomputeTaskFromEntries(entry.taskId)
      this._persist()
    },
    // Server-hook simulation: pull latest entry for the task and rewrite the parent
    // Task's `progress` + `status`. No-op when nothing actually changes so we don't
    // churn the array. If the task has zero entries, progress falls back to 0 / Open.
    _recomputeTaskFromEntries(taskId) {
      const taskIdx = this.tasks.findIndex(t => t.id === taskId)
      if (taskIdx === -1) return
      const entries = this.taskProgressEntries
        .filter(e => e.taskId === taskId)
        .slice()
        .sort((a, b) => {
          const cmp = (b.entryDate || '').localeCompare(a.entryDate || '')
          return cmp !== 0 ? cmp : (b.id || '').localeCompare(a.id || '')
        })
      const latest = entries[0]
      const progress = latest ? Number(latest.progressPct) || 0 : 0
      const status = progress === 100 ? 'Completed' : progress > 0 ? 'In Progress' : 'Open'
      const current = this.tasks[taskIdx]
      if (current.progress !== progress || current.status !== status) {
        this.tasks[taskIdx] = { ...current, progress, status }
      }
    },

    // ===== SCOs =====
    addSco(data) {
      const id = uid('SCO')
      // §14.2 — Company auto-derived from parent project.
      const parentProject = this.projects.find(p => p.id === data.projectId)
      const sco = {
        id, projectId: data.projectId, title: data.title,
        company: parentProject?.company || this.activeCompany,
        type: data.type || 'Design Change', impact: Number(data.impact) || 0,
        recoverable: !!data.recoverable, status: 'Pending Approval',
        raisedBy: data.raisedBy || (this.team[0] && this.team[0].id),
        raisedDate: new Date().toISOString().slice(0, 10),
        reason: data.reason || '',
        boqRevisionRef: null,
      }
      this.scos.unshift(sco)
      this._persist()
      return sco
    },
    updateSco(id, patch) {
      const idx = this.scos.findIndex(s => s.id === id)
      if (idx === -1) return null
      this.scos[idx] = { ...this.scos[idx], ...patch }
      this._persist()
      return this.scos[idx]
    },

    // ===== Rate Master (M3) =====
    addRate(data) {
      const id = uid('RM')
      const rate = {
        id,
        code: data.code,
        category: data.category || 'Material',
        description: data.description,
        unit: data.unit,
        currentRate: Number(data.currentRate) || 0,
        updatedAt: new Date().toISOString().slice(0,10),
        source: data.source || 'Manual',
        updatedBy: data.updatedBy || this.user?.id,
      }
      this.rateMaster.unshift(rate)
      this._persist()
      return rate
    },
    // Update a rate — and append the previous value to rateHistory so we keep the audit trail.
    updateRate(id, patch) {
      const idx = this.rateMaster.findIndex(r => r.id === id)
      if (idx === -1) return null
      const prev = this.rateMaster[idx]
      // Log history if the rate itself changed
      if (patch.currentRate !== undefined && Number(patch.currentRate) !== prev.currentRate) {
        this.rateHistory.push({
          id: uid('RH'),
          rateMasterId: id,
          rate: prev.currentRate,
          effectiveDate: prev.updatedAt,
          source: prev.source,
          updatedBy: prev.updatedBy,
        })
      }
      this.rateMaster[idx] = {
        ...prev,
        ...patch,
        currentRate: patch.currentRate !== undefined ? Number(patch.currentRate) : prev.currentRate,
        updatedAt: new Date().toISOString().slice(0,10),
        updatedBy: patch.updatedBy || this.user?.id || prev.updatedBy,
      }
      this._persist()
      return this.rateMaster[idx]
    },
    deleteRate(id) {
      this.rateMaster = this.rateMaster.filter(r => r.id !== id)
      this.rateHistory = this.rateHistory.filter(h => h.rateMasterId !== id)
      this._persist()
    },

    // ===== BOQ (M3) =====
    addBoq(data) {
      const id = uid('BOQ')
      // §14.2 — Company auto-derived from parent project. createBoqRevisionFrom
      // passes through this same code path so revision clones inherit correctly.
      const parentProject = this.projects.find(p => p.id === data.projectId)
      const boq = {
        id,
        projectId: data.projectId,
        company: parentProject?.company || this.activeCompany,
        revision: data.revision || 1,
        baseRevisionId: data.baseRevisionId || null,
        status: data.status || 'Draft',
        sourceScoId: data.sourceScoId || null,
        title: data.title || `BOQ Revision ${data.revision || 1}`,
        preparedBy: data.preparedBy || this.user?.id,
        preparedDate: new Date().toISOString().slice(0,10),
        approvedBy: null,
        approvedDate: null,
      }
      this.boqs.unshift(boq)
      this._persist()
      return boq
    },
    updateBoq(id, patch) {
      const idx = this.boqs.findIndex(b => b.id === id)
      if (idx === -1) return null
      this.boqs[idx] = { ...this.boqs[idx], ...patch }
      this._persist()
      return this.boqs[idx]
    },
    submitBoq(id) {
      return this.updateBoq(id, { status: 'Submitted' })
    },
    // Approve a BOQ. Per spec: only one Approved revision per project — supersede any others.
    approveBoq(id) {
      const boq = this.boqById(id)
      if (!boq) return null
      // Supersede other Approved revisions for the same project
      this.boqs = this.boqs.map(b => {
        if (b.id !== id && b.projectId === boq.projectId && b.status === 'Approved') {
          return { ...b, status: 'Superseded' }
        }
        return b
      })
      return this.updateBoq(id, { status: 'Approved', approvedBy: this.user?.id, approvedDate: new Date().toISOString().slice(0,10) })
    },
    deleteBoq(id) {
      this.boqs = this.boqs.filter(b => b.id !== id)
      this.boqGroups = this.boqGroups.filter(g => g.boqId !== id)
      this.boqItems = this.boqItems.filter(i => i.boqId !== id)
      this.boqSubItems = this.boqSubItems.filter(si => si.boqId !== id)
      this._persist()
    },

    // ===== BOQ Groups / Items / Sub-items =====
    addBoqGroup(data) {
      const id = uid('BG')
      const order = data.order ?? (this.boqGroups.filter(g => g.boqId === data.boqId).length + 1)
      const group = { id, boqId: data.boqId, code: data.code || '', name: data.name, order }
      this.boqGroups.push(group)
      this._persist()
      return group
    },
    updateBoqGroup(id, patch) {
      const idx = this.boqGroups.findIndex(g => g.id === id)
      if (idx === -1) return null
      this.boqGroups[idx] = { ...this.boqGroups[idx], ...patch }
      this._persist()
      return this.boqGroups[idx]
    },
    deleteBoqGroup(id) {
      this.boqGroups = this.boqGroups.filter(g => g.id !== id)
      const itemIds = this.boqItems.filter(i => i.groupId === id).map(i => i.id)
      this.boqItems = this.boqItems.filter(i => i.groupId !== id)
      this.boqSubItems = this.boqSubItems.filter(si => !itemIds.includes(si.itemId))
      this._persist()
    },

    addBoqItem(data) {
      const id = uid('BI')
      const plannedQty = Number(data.plannedQty) || 0
      const rate = Number(data.rate) || 0
      const item = {
        id,
        boqId: data.boqId,
        groupId: data.groupId,
        code: data.code || '',
        description: data.description || '',
        unit: data.unit || 'nos',
        plannedQty, rate,
        plannedAmount: plannedQty * rate,
        actualQty: 0,
        actualAmount: 0,
        taskId: data.taskId || null,
      }
      this.boqItems.push(item)
      this._persist()
      return item
    },
    updateBoqItem(id, patch) {
      const idx = this.boqItems.findIndex(i => i.id === id)
      if (idx === -1) return null
      const merged = { ...this.boqItems[idx], ...patch }
      // Keep plannedAmount derived from qty × rate so the user can edit either.
      if (patch.plannedQty !== undefined || patch.rate !== undefined) {
        merged.plannedQty = Number(merged.plannedQty) || 0
        merged.rate = Number(merged.rate) || 0
        merged.plannedAmount = merged.plannedQty * merged.rate
      }
      this.boqItems[idx] = merged
      this._persist()
      return merged
    },
    deleteBoqItem(id) {
      this.boqItems = this.boqItems.filter(i => i.id !== id)
      this.boqSubItems = this.boqSubItems.filter(si => si.itemId !== id)
      this._persist()
    },

    addBoqSubItem(data) {
      const id = uid('BS')
      const qtyPerUnit = Number(data.qtyPerUnit) || 0
      // If rateMasterId given, auto-fetch rate from master (proposal spec).
      let rate = Number(data.rate) || 0
      if (data.rateMasterId) {
        const r = this.rateMaster.find(x => x.id === data.rateMasterId)
        if (r) rate = r.currentRate
      }
      const sub = {
        id,
        boqId: data.boqId,
        itemId: data.itemId,
        rateMasterId: data.rateMasterId || null,
        description: data.description || '',
        qtyPerUnit, rate,
        amount: qtyPerUnit * rate,
      }
      this.boqSubItems.push(sub)
      this._persist()
      return sub
    },
    updateBoqSubItem(id, patch) {
      const idx = this.boqSubItems.findIndex(si => si.id === id)
      if (idx === -1) return null
      const merged = { ...this.boqSubItems[idx], ...patch }
      // Auto-refresh rate from master if rateMasterId changed
      if (patch.rateMasterId) {
        const r = this.rateMaster.find(x => x.id === patch.rateMasterId)
        if (r) merged.rate = r.currentRate
      }
      merged.qtyPerUnit = Number(merged.qtyPerUnit) || 0
      merged.rate = Number(merged.rate) || 0
      merged.amount = merged.qtyPerUnit * merged.rate
      this.boqSubItems[idx] = merged
      this._persist()
      return merged
    },
    deleteBoqSubItem(id) {
      this.boqSubItems = this.boqSubItems.filter(si => si.id !== id)
      this._persist()
    },

    // ===== BOQ Revision Engine (M3) =====
    // Copy a BOQ and all its children into a new Draft revision. Optionally link to a source SCO.
    createBoqRevisionFrom(sourceBoqId, opts = {}) {
      const src = this.boqById(sourceBoqId)
      if (!src) return null
      // Find the highest existing revision for this project to compute next revision number
      const projectBoqs = this.boqs.filter(b => b.projectId === src.projectId)
      const nextRev = Math.max(...projectBoqs.map(b => b.revision)) + 1

      const newBoq = this.addBoq({
        projectId: src.projectId,
        revision: nextRev,
        baseRevisionId: src.id,
        status: 'Draft',
        sourceScoId: opts.sourceScoId || null,
        title: opts.title || `Revision ${nextRev}${opts.sourceScoId ? ` (from ${opts.sourceScoId})` : ''}`,
      })

      // Clone groups
      const groupIdMap = {}
      this.boqGroups.filter(g => g.boqId === src.id).forEach(g => {
        const newGroup = this.addBoqGroup({ boqId: newBoq.id, code: g.code, name: g.name, order: g.order })
        groupIdMap[g.id] = newGroup.id
      })

      // Clone items (reset actuals — new revision starts from zero)
      const itemIdMap = {}
      this.boqItems.filter(i => i.boqId === src.id).forEach(i => {
        const newItem = this.addBoqItem({
          boqId: newBoq.id,
          groupId: groupIdMap[i.groupId],
          code: i.code,
          description: i.description,
          unit: i.unit,
          plannedQty: i.plannedQty,
          rate: i.rate,
          taskId: i.taskId,
        })
        itemIdMap[i.id] = newItem.id
      })

      // Clone sub-items
      this.boqSubItems.filter(si => si.boqId === src.id).forEach(si => {
        this.addBoqSubItem({
          boqId: newBoq.id,
          itemId: itemIdMap[si.itemId],
          rateMasterId: si.rateMasterId,
          description: si.description,
          qtyPerUnit: si.qtyPerUnit,
          rate: si.rate,
        })
      })

      // Link the SCO back to this revision if applicable
      if (opts.sourceScoId) {
        this.updateSco(opts.sourceScoId, { boqRevisionRef: newBoq.id })
      }

      return newBoq
    },

    // Recalculate actual qty/amount for every BOQ item linked to a task,
    // by reading task progress %. This stands in for the four real upstream hooks
    // (Task Progress Entry, Stock Entry issue, RA Bill, Petty Cash) in the proposal.
    recalculateActuals(boqId) {
      const items = this.boqItems.filter(i => i.boqId === boqId)
      items.forEach(item => {
        if (!item.taskId) return
        const task = this.tasks.find(t => t.id === item.taskId)
        if (!task) return
        const pct = (task.progress || 0) / 100
        const actualQty = +(item.plannedQty * pct).toFixed(2)
        const actualAmount = +(actualQty * item.rate).toFixed(2)
        const idx = this.boqItems.findIndex(i => i.id === item.id)
        if (idx !== -1) this.boqItems[idx] = { ...this.boqItems[idx], actualQty, actualAmount }
      })
      this._persist()
    },
  },
})
