// Project Type templates — CLAUDE.md §13.3 item 19.
//
// HISTORY: was Light-interpretation only (JSON fixtures, no admin UI, no M1
// editor). Session 39 extended the fixtures with default Work Packages and
// default Tasks (exploratory visualisation only — see §10 Session 39 entry).
// The admin editor for Project Types lives at /app/settings/project-types
// (Session 39 — also exploratory, prototype-scope only; production version of
// the Heavy interpretation is BuildSuite Pro per the §13.3 footnote).
//
// Field shape per template:
//   defaultStages[]:
//     stageName              — string, the human label
//     offsetStartDays        — integer, days after project.startDate
//     offsetEndDays          — integer, days after project.startDate
//     plannedTaskCount       — integer, headline planned count for the stage
//     plannedCompletionPct   — integer (0-100), planned target
//     description            — optional, copied into the seeded stage
//
//   defaultWorkPackages[]:  (Session 39 — exploratory)
//     code                   — short stable code (used by defaultTasks to
//                              reference the WP this task lives under)
//     name                   — human label
//     description            — optional
//     budget                 — integer (rupees), 0 for "fill in later"
//     sort_order             — integer
//
//   defaultTasks[]:  (Session 39 — exploratory)
//     workPackageCode        — string matching a defaultWorkPackages[].code,
//                              or null for a task that hangs directly under
//                              the Project with no Work Package
//     name                   — human label
//     priority               — Low / Medium / High
//     estimated_hours        — integer
//     sort_order             — integer within its WP
//
//   defaultActivityTypes[]   — Activity Type IDs (AT-...) that are suggested
//                              for this project type. (Renamed in Session 31
//                              from defaultTaskTypes.)
//
//   defaultFieldVisibility   — PLACEHOLDER. The Project-form-field schema map
//                              per type is M2 work; this is the data shape
//                              that the M2 wiring will read.
//
// Stage offsets are relative to project.startDate and don't have to be
// non-overlapping — stages frequently overlap in real construction.

export const PROJECT_TYPE_TEMPLATES = {
  Commercial: {
    defaultStages: [
      { stageName: 'Foundation',     offsetStartDays:   0, offsetEndDays:  60, plannedTaskCount:  8, plannedCompletionPct: 100, description: 'Earthwork, excavation, PCC, and raft foundation.' },
      { stageName: 'Substructure',   offsetStartDays:  45, offsetEndDays: 120, plannedTaskCount: 12, plannedCompletionPct: 100, description: 'Basement walls, raft cap, ground-floor slab.' },
      { stageName: 'Superstructure', offsetStartDays:  90, offsetEndDays: 240, plannedTaskCount: 28, plannedCompletionPct: 100, description: 'RCC frame — columns, beams, slabs across all floors.' },
      { stageName: 'MEP rough-in',   offsetStartDays: 180, offsetEndDays: 300, plannedTaskCount: 16, plannedCompletionPct: 100, description: 'Electrical conduits, plumbing rough-in, HVAC ducts.' },
      { stageName: 'Finishing',      offsetStartDays: 240, offsetEndDays: 360, plannedTaskCount: 22, plannedCompletionPct: 100, description: 'Masonry, plaster, flooring, painting, façade.' },
      { stageName: 'Handover',       offsetStartDays: 350, offsetEndDays: 380, plannedTaskCount:  4, plannedCompletionPct: 100, description: 'Snagging, statutory clearances, client handover.' },
    ],
    defaultWorkPackages: [
      { code: 'WP-FND',     name: 'Foundation Works',  description: 'Excavation, PCC, raft & footing pours.',              budget: 5000000,  sort_order: 1 },
      { code: 'WP-STRUCT',  name: 'Superstructure',    description: 'Vertical RCC frame across all floors.',               budget: 15000000, sort_order: 2 },
      { code: 'WP-MEP',     name: 'MEP Rough-in',      description: 'Electrical, plumbing, HVAC rough-in across floors.', budget: 6000000,  sort_order: 3 },
      { code: 'WP-FIN',     name: 'Finishing',         description: 'Masonry, plaster, flooring, paint, façade.',         budget: 8000000,  sort_order: 4 },
      { code: 'WP-HND',     name: 'Handover',          description: 'Snagging, statutory clearances, client handover.',    budget: 500000,   sort_order: 5 },
    ],
    defaultTasks: [
      { workPackageCode: 'WP-FND',    name: 'Earthwork excavation',          priority: 'High',   estimated_hours: 240, sort_order: 1 },
      { workPackageCode: 'WP-FND',    name: 'PCC laying',                    priority: 'Medium', estimated_hours: 120, sort_order: 2 },
      { workPackageCode: 'WP-FND',    name: 'Raft foundation casting',       priority: 'High',   estimated_hours: 400, sort_order: 3 },
      { workPackageCode: 'WP-STRUCT', name: 'Column casting — Level 1 to 5', priority: 'High',   estimated_hours: 800, sort_order: 1 },
      { workPackageCode: 'WP-STRUCT', name: 'Slab casting — Level 1 to 5',   priority: 'High',   estimated_hours: 720, sort_order: 2 },
      { workPackageCode: 'WP-MEP',    name: 'Electrical conduit laying',     priority: 'Medium', estimated_hours: 320, sort_order: 1 },
      { workPackageCode: 'WP-MEP',    name: 'Plumbing rough-in',             priority: 'Medium', estimated_hours: 280, sort_order: 2 },
      { workPackageCode: 'WP-FIN',    name: 'Internal plaster',              priority: 'Medium', estimated_hours: 360, sort_order: 1 },
      { workPackageCode: 'WP-FIN',    name: 'Floor tiling',                  priority: 'Medium', estimated_hours: 240, sort_order: 2 },
      { workPackageCode: 'WP-FIN',    name: 'Painting',                      priority: 'Low',    estimated_hours: 180, sort_order: 3 },
      { workPackageCode: 'WP-HND',    name: 'Snagging walkthrough',          priority: 'High',   estimated_hours:  40, sort_order: 1 },
      { workPackageCode: 'WP-HND',    name: 'Occupancy certificate',         priority: 'High',   estimated_hours:  20, sort_order: 2 },
    ],
    defaultActivityTypes: ['AT-008', 'AT-001', 'AT-002', 'AT-006', 'AT-007', 'AT-003', 'AT-004', 'AT-005'],
    defaultFieldVisibility: {
      plot_area_sqft:      true,
      floors_above_ground: true,
      has_basement:        true,
      parking_floors:      true,
      retail_floors:       true,
      total_units:         false,
      has_clubhouse:       false,
    },
  },

  Residential: {
    defaultStages: [
      { stageName: 'Foundation',     offsetStartDays:   0, offsetEndDays:  60, plannedTaskCount:  6, plannedCompletionPct: 100, description: 'Earthwork, excavation, PCC, raft foundation.' },
      { stageName: 'Substructure',   offsetStartDays:  45, offsetEndDays: 120, plannedTaskCount: 10, plannedCompletionPct: 100, description: 'Basement walls, raft cap, ground-floor slab.' },
      { stageName: 'Superstructure', offsetStartDays:  90, offsetEndDays: 240, plannedTaskCount: 26, plannedCompletionPct: 100, description: 'RCC frame for the residential floors.' },
      { stageName: 'MEP rough-in',   offsetStartDays: 180, offsetEndDays: 300, plannedTaskCount: 14, plannedCompletionPct: 100, description: 'Conduit, plumbing rough-in, gas pipework where applicable.' },
      { stageName: 'Finishing',      offsetStartDays: 240, offsetEndDays: 360, plannedTaskCount: 32, plannedCompletionPct: 100, description: 'Masonry, plaster, tiling, painting, joinery, kitchen / bath fit-out.' },
      { stageName: 'Handover',       offsetStartDays: 350, offsetEndDays: 380, plannedTaskCount:  6, plannedCompletionPct: 100, description: 'Snagging, statutory clearances, possession handover.' },
    ],
    defaultWorkPackages: [
      { code: 'WP-FND',     name: 'Foundation Works',     description: 'Excavation, PCC, raft foundation for the tower.',     budget: 4000000,  sort_order: 1 },
      { code: 'WP-STRUCT',  name: 'Tower Superstructure', description: 'RCC frame for the residential tower.',                budget: 12000000, sort_order: 2 },
      { code: 'WP-MEP',     name: 'MEP Rough-in',         description: 'Electrical, plumbing, gas piping rough-in per unit.', budget: 5000000,  sort_order: 3 },
      { code: 'WP-FIT',     name: 'Unit Fit-out',         description: 'Joinery, kitchen, bath, internal finishes per unit.', budget: 9000000,  sort_order: 4 },
      { code: 'WP-AMEN',    name: 'Amenities',            description: 'Clubhouse, landscaping, common areas.',               budget: 2500000,  sort_order: 5 },
    ],
    defaultTasks: [
      { workPackageCode: 'WP-FND',    name: 'Earthwork excavation',          priority: 'High',   estimated_hours: 200, sort_order: 1 },
      { workPackageCode: 'WP-FND',    name: 'Raft foundation casting',       priority: 'High',   estimated_hours: 360, sort_order: 2 },
      { workPackageCode: 'WP-STRUCT', name: 'Tower column casting',          priority: 'High',   estimated_hours: 720, sort_order: 1 },
      { workPackageCode: 'WP-STRUCT', name: 'Tower slab casting',            priority: 'High',   estimated_hours: 640, sort_order: 2 },
      { workPackageCode: 'WP-MEP',    name: 'Conduit + plumbing per unit',   priority: 'Medium', estimated_hours: 480, sort_order: 1 },
      { workPackageCode: 'WP-FIT',    name: 'Wall plaster + putty',          priority: 'Medium', estimated_hours: 320, sort_order: 1 },
      { workPackageCode: 'WP-FIT',    name: 'Floor tiling per unit',         priority: 'Medium', estimated_hours: 280, sort_order: 2 },
      { workPackageCode: 'WP-FIT',    name: 'Joinery + kitchen fit-out',     priority: 'Medium', estimated_hours: 360, sort_order: 3 },
      { workPackageCode: 'WP-FIT',    name: 'Painting',                      priority: 'Low',    estimated_hours: 200, sort_order: 4 },
      { workPackageCode: 'WP-AMEN',   name: 'Clubhouse finishing',           priority: 'Medium', estimated_hours: 240, sort_order: 1 },
      { workPackageCode: 'WP-AMEN',   name: 'Landscaping',                   priority: 'Low',    estimated_hours: 160, sort_order: 2 },
    ],
    defaultActivityTypes: ['AT-008', 'AT-001', 'AT-002', 'AT-003', 'AT-004', 'AT-005', 'AT-006', 'AT-007'],
    defaultFieldVisibility: {
      plot_area_sqft:      true,
      floors_above_ground: true,
      has_basement:        true,
      parking_floors:      true,
      retail_floors:       false,
      total_units:         true,
      has_clubhouse:       true,
    },
  },

  Infrastructure: {
    defaultStages: [
      { stageName: 'Site Prep',                  offsetStartDays:   0, offsetEndDays:  90, plannedTaskCount:  6, plannedCompletionPct: 100, description: 'Site grading, retaining wall layout, mass excavation, utility diversion.' },
      { stageName: 'Foundation',                 offsetStartDays:  60, offsetEndDays: 180, plannedTaskCount: 10, plannedCompletionPct: 100, description: 'Pile foundations, pile caps, sub-structure footings.' },
      { stageName: 'Structure',                  offsetStartDays: 150, offsetEndDays: 330, plannedTaskCount: 24, plannedCompletionPct: 100, description: 'Main civil structure — columns, decks, retaining walls, station box etc.' },
      { stageName: 'Finishing & Commissioning',  offsetStartDays: 300, offsetEndDays: 400, plannedTaskCount: 12, plannedCompletionPct: 100, description: 'Finishes, electrical / signalling fit-out, testing, commissioning.' },
    ],
    defaultWorkPackages: [
      { code: 'WP-SITE',    name: 'Site Preparation', description: 'Grading, mass excavation, utility diversion, site access.', budget: 6000000,  sort_order: 1 },
      { code: 'WP-PILE',    name: 'Piling & Foundations', description: 'Pile foundations, pile caps, footings.',               budget: 18000000, sort_order: 2 },
      { code: 'WP-STRUCT',  name: 'Civil Structure',  description: 'Columns, decks, retaining walls, station box.',            budget: 32000000, sort_order: 3 },
      { code: 'WP-COMM',    name: 'Commissioning',    description: 'Finishes, signalling fit-out, testing, commissioning.',    budget: 10000000, sort_order: 4 },
    ],
    defaultTasks: [
      { workPackageCode: 'WP-SITE',   name: 'Site grading',                   priority: 'High',   estimated_hours: 320, sort_order: 1 },
      { workPackageCode: 'WP-SITE',   name: 'Utility diversion',              priority: 'High',   estimated_hours: 240, sort_order: 2 },
      { workPackageCode: 'WP-PILE',   name: 'Pile installation',              priority: 'High',   estimated_hours: 800, sort_order: 1 },
      { workPackageCode: 'WP-PILE',   name: 'Pile cap casting',               priority: 'High',   estimated_hours: 400, sort_order: 2 },
      { workPackageCode: 'WP-STRUCT', name: 'Column casting',                 priority: 'High',   estimated_hours: 960, sort_order: 1 },
      { workPackageCode: 'WP-STRUCT', name: 'Deck casting',                   priority: 'High',   estimated_hours: 720, sort_order: 2 },
      { workPackageCode: 'WP-STRUCT', name: 'Retaining wall construction',   priority: 'Medium', estimated_hours: 540, sort_order: 3 },
      { workPackageCode: 'WP-COMM',   name: 'Signalling fit-out',             priority: 'High',   estimated_hours: 480, sort_order: 1 },
      { workPackageCode: 'WP-COMM',   name: 'Testing & commissioning',        priority: 'High',   estimated_hours: 320, sort_order: 2 },
    ],
    defaultActivityTypes: ['AT-008', 'AT-001', 'AT-002', 'AT-006'],
    defaultFieldVisibility: {
      plot_area_sqft:              false,
      floors_above_ground:         false,
      has_basement:                false,
      corridor_length_km:          true,
      has_overhead_structures:     true,
      max_span_m:                  true,
      has_underground_works:       true,
    },
  },
}

// Helper used by both the store seed and the UI preview. Pure — no store deps.
export function templateForType(typeName) {
  return PROJECT_TYPE_TEMPLATES[typeName] || null
}
