// Initial seed data — populated to localStorage on first run.
// Reset by clearing the 'buildsuite:data' key in browser DevTools > Application > Local Storage.

export const seedData = {
  // Companies — CLAUDE.md §14. The 3-company multi-company demo set. To go
  // single-company, trim this array to one entry — the topbar switcher, the
  // NewProject company field, and the Projects-list company column all auto-
  // hide when length === 1 via `store.isMultiCompany`.
  companies: [
    { id: 'ACME-COM', name: 'Acme Commercial Pvt Ltd',   shortName: 'Acme Commercial', description: 'Commercial buildings · offices · IT parks · retail',     color: 'bg-violet-600' },
    { id: 'ACME-RES', name: 'Acme Builders Pvt Ltd',     shortName: 'Acme Builders',   description: 'Residential towers · apartments · gated communities',     color: 'bg-blue-600'   },
    { id: 'ACME-INF', name: 'Acme Infrastructure Pvt Ltd', shortName: 'Acme Infra',    description: 'Metro stations · roads · bridges · public infrastructure', color: 'bg-amber-600'  },
  ],

  // Customer master (Session 40). Frappe-native shape — mirrors the ERPNext
  // Customer DocType (Selling module). `name` is the join key onto
  // project.client (existing project.client values are plain strings; the
  // customer record's `name` field exactly matches so lookups resolve).
  // ID prefix CUST- per ERPNext convention.
  customers: [
    { id: 'CUST-001', name: 'Prestige Group', type: 'Builder',    contactPerson: 'Rakesh Iyer',  email: 'rakesh.iyer@prestige.example',  phone: '+91 98450 11111', gstin: '29AABCP1234A1Z5' },
    { id: 'CUST-002', name: 'Casagrand',      type: 'Builder',    contactPerson: 'Meera Subramaniam', email: 'meera.s@casagrand.example', phone: '+91 98401 22222', gstin: '33AABCC2345B1Z6' },
    { id: 'CUST-003', name: 'KMRL',           type: 'Government', contactPerson: 'Anil Kumar',    email: 'anil.k@kmrl.example',          phone: '+91 98470 33333', gstin: '32AAACK3456C1Z7' },
    { id: 'CUST-004', name: 'Technopark',     type: 'Government', contactPerson: 'Suja Nair',     email: 'suja.n@technopark.example',    phone: '+91 99470 44444', gstin: '32AAATC4567D1Z8' },
    { id: 'CUST-005', name: 'Brigade Enterprises', type: 'Builder',   contactPerson: 'Vinod Reddy', email: 'vinod.r@brigade.example',   phone: '+91 98860 55555', gstin: '29AABCB5678E1Z9' },
    { id: 'CUST-006', name: 'Larsen & Toubro Realty', type: 'Corporate', contactPerson: 'Sunita Pillai', email: 'sunita.p@lntrealty.example', phone: '+91 98200 66666', gstin: '27AABCL6789F1Z0' },
  ],

  user: {
    id: 'USR-001',
    name: 'Admin User',
    email: 'admin@buildsuite.local',
    role: 'System Manager',
    initials: 'AD',
  },
  team: [
    { id: 'USR-001', name: 'Admin User',     role: 'System Manager',    initials: 'AD', color: 'bg-brand-600' },
    { id: 'USR-002', name: 'Hemanth M.',     role: 'Project Manager',   initials: 'HM', color: 'bg-blue-600' },
    { id: 'USR-003', name: 'Aadith P.',      role: 'Lead Engineer',     initials: 'AP', color: 'bg-violet-600' },
    { id: 'USR-004', name: 'Rugma R.',       role: 'Quantity Surveyor', initials: 'RR', color: 'bg-amber-600' },
    { id: 'USR-005', name: 'Ravi Kumar',     role: 'Site Engineer',     initials: 'RK', color: 'bg-emerald-600' },
    { id: 'USR-006', name: 'Priya M.',       role: 'Site Engineer',     initials: 'PM', color: 'bg-rose-600' },
    { id: 'USR-007', name: 'Suresh N.',      role: 'Procurement',       initials: 'SN', color: 'bg-cyan-600' },
  ],
  projects: [
    {
      id: 'PROJ-2026-001',
      code: 'BTP-P2',
      name: 'Bangalore Tech Park — Phase 2',
      client: 'Prestige Group',
      status: 'Active',
      priority: 'High',
      type: 'Commercial',
      company: 'ACME-COM',
      startDate: '2026-02-15',
      endDate: '2026-10-10',
      budget: 45000000,
      progress: 62,
      pm: 'USR-002',
      location: 'Outer Ring Road, Bangalore',
      description: 'Phase 2 of the Prestige Tech Park — Block A (G+8) and Block B (G+6) with shared basement parking.',
      parentId: null,
      createdAt: '2026-02-10',
    },
    {
      id: 'PROJ-2026-001-A',
      code: 'BTP-P2-A',
      name: 'Block A — Office Tower',
      client: 'Prestige Group',
      status: 'Active',
      priority: 'High',
      type: 'Commercial',
      company: 'ACME-COM',
      startDate: '2026-02-15',
      endDate: '2026-09-15',
      budget: 26000000,
      progress: 68,
      pm: 'USR-002',
      location: 'Block A · Outer Ring Road',
      description: 'G+8 office tower with 4-level basement. Curtain glazing façade.',
      parentId: 'PROJ-2026-001',
      createdAt: '2026-02-10',
    },
    {
      id: 'PROJ-2026-001-B',
      code: 'BTP-P2-B',
      name: 'Block B — Annex',
      client: 'Prestige Group',
      status: 'Active',
      priority: 'Medium',
      type: 'Commercial',
      company: 'ACME-COM',
      startDate: '2026-03-20',
      endDate: '2026-10-10',
      budget: 19000000,
      progress: 54,
      pm: 'USR-003',
      location: 'Block B · Outer Ring Road',
      description: 'G+6 annex with cafeteria, meeting suites, and shared services.',
      parentId: 'PROJ-2026-001',
      createdAt: '2026-03-15',
    },
    {
      id: 'PROJ-2026-002',
      code: 'CHN-RT',
      name: 'Chennai Residential Towers',
      client: 'Casagrand',
      status: 'Active',
      priority: 'High',
      type: 'Residential',
      company: 'ACME-RES',
      startDate: '2026-03-01',
      endDate: '2027-04-15',
      budget: 82000000,
      progress: 34,
      pm: 'USR-003',
      location: 'OMR, Chennai',
      description: 'Three G+15 residential towers · 360 units · clubhouse and amenities.',
      parentId: null,
      createdAt: '2026-02-25',
    },
    {
      id: 'PROJ-2025-014',
      code: 'KMS-ALV',
      name: 'Kochi Metro Station — Aluva',
      client: 'KMRL',
      status: 'Active',
      priority: 'High',
      type: 'Infrastructure',
      company: 'ACME-INF',
      startDate: '2025-05-10',
      endDate: '2026-06-30',
      budget: 62000000,
      progress: 88,
      pm: 'USR-004',
      location: 'Aluva, Kochi',
      description: 'Elevated metro station with two platforms and concourse level.',
      parentId: null,
      createdAt: '2025-05-01',
    },
    {
      id: 'PROJ-2025-022',
      code: 'TTC-C',
      name: 'Trivandrum Tech City — Block C',
      client: 'Technopark',
      status: 'On Hold',
      priority: 'Medium',
      type: 'Commercial',
      company: 'ACME-COM',
      startDate: '2025-09-15',
      endDate: '2026-12-20',
      budget: 38000000,
      progress: 24,
      pm: 'USR-002',
      location: 'Technopark, Trivandrum',
      description: 'IT building shell-and-core construction. Currently paused — pending client clearance.',
      parentId: null,
      createdAt: '2025-09-10',
    },
  ],
  workPackages: [
    { id:'WP-001', projectId:'PROJ-2026-001-A', code:'WP-A-EW', name:'Earthwork & Foundation',     status:'Completed',   progress:100, budget:3800000, startDate:'2026-02-15', endDate:'2026-04-10', owner:'USR-003' },
    { id:'WP-002', projectId:'PROJ-2026-001-A', code:'WP-A-SU', name:'Substructure RCC',            status:'Completed',   progress:100, budget:5200000, startDate:'2026-03-20', endDate:'2026-05-30', owner:'USR-003' },
    { id:'WP-003', projectId:'PROJ-2026-001-A', code:'WP-A-SP', name:'Superstructure RCC',          status:'In Progress', progress:72,  budget:8400000, startDate:'2026-05-15', endDate:'2026-07-30', owner:'USR-003' },
    { id:'WP-004', projectId:'PROJ-2026-001-A', code:'WP-A-MA', name:'Masonry & Plaster',           status:'In Progress', progress:35,  budget:3200000, startDate:'2026-06-10', endDate:'2026-08-20', owner:'USR-002' },
    { id:'WP-005', projectId:'PROJ-2026-001-A', code:'WP-A-MP', name:'MEP — Mechanical & Plumbing', status:'Planned',     progress:8,   budget:2900000, startDate:'2026-07-15', endDate:'2026-09-01', owner:'USR-007' },
    { id:'WP-006', projectId:'PROJ-2026-001-A', code:'WP-A-FN', name:'Finishing & Façade',           status:'Planned',     progress:0,   budget:2500000, startDate:'2026-08-15', endDate:'2026-09-15', owner:'USR-002' },

    { id:'WP-007', projectId:'PROJ-2026-001-B', code:'WP-B-EW', name:'Earthwork & Foundation',     status:'Completed',   progress:100, budget:2800000, startDate:'2026-03-20', endDate:'2026-05-15', owner:'USR-003' },
    { id:'WP-008', projectId:'PROJ-2026-001-B', code:'WP-B-SP', name:'Superstructure',              status:'In Progress', progress:55,  budget:6200000, startDate:'2026-05-01', endDate:'2026-08-15', owner:'USR-003' },
    { id:'WP-009', projectId:'PROJ-2026-001-B', code:'WP-B-MA', name:'Masonry',                      status:'In Progress', progress:20,  budget:2400000, startDate:'2026-07-01', endDate:'2026-09-15', owner:'USR-003' },

    { id:'WP-010', projectId:'PROJ-2026-002', code:'WP-CHN-EW', name:'Site Prep & Excavation',     status:'In Progress', progress:80,  budget:5800000, startDate:'2026-03-01', endDate:'2026-06-30', owner:'USR-003' },
    { id:'WP-011', projectId:'PROJ-2026-002', code:'WP-CHN-T1', name:'Tower 1 — Foundation',        status:'In Progress', progress:42,  budget:8200000, startDate:'2026-04-15', endDate:'2026-09-30', owner:'USR-003' },
  ],
  tasks: [
    // task_type per proposal §M2 — Select(Activity / Milestone / Inspection).
    // 'Activity' is the default for everyday work driven by Progress Entries.
    // 'Milestone' marks stage-completion checkpoints (here: TSK-1009 + TSK-1012
    // as the last tasks of Block A and Block B's seed sets — no explicit handover
    // tasks existed, so fell back to "last task per project" per the prompt).
    // 'Inspection' marks QC gates (TSK-1013 + TSK-1014 added below).
    // activityType is the optional Link to the Activity Type master (RCC Column
    // Casting / Brick Masonry / etc.) — provides default labour mix + productivity.
    //
    // Block A - Superstructure WP
    { id:'TSK-1001', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Activity',   activityType:'AT-001', name:'Block A — Level 5 column casting (Grid 1-4)',  status:'Completed',   priority:'High',  assignee:'USR-005', startDate:'2026-04-20', endDate:'2026-04-28', progress:100, estimatedHours:120, actualHours:115, description:'M30 concrete columns for grid lines 1 to 4.' },
    { id:'TSK-1002', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Activity',   activityType:'AT-001', name:'Block A — Level 5 column casting (Grid 5-8)',  status:'Completed',   priority:'High',  assignee:'USR-005', startDate:'2026-04-29', endDate:'2026-05-05', progress:100, estimatedHours:120, actualHours:118, description:'M30 concrete columns for grid lines 5 to 8.' },
    { id:'TSK-1003', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Activity',                          name:'Block A — Level 5 slab reinforcement',          status:'Completed',   priority:'High',  assignee:'USR-005', startDate:'2026-05-06', endDate:'2026-05-14', progress:100, estimatedHours:160, actualHours:156, description:'Reinforcement tying and form-work for level 5 slab.' },
    { id:'TSK-1004', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Activity',   activityType:'AT-002', name:'Block A — Level 5 slab casting',                 status:'In Progress', priority:'High',  assignee:'USR-005', startDate:'2026-05-15', endDate:'2026-05-18', progress:75,  estimatedHours:48,  actualHours:36,  description:'M30 concrete slab pour — 380 m².' },
    { id:'TSK-1005', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Activity',                          name:'Block A — Level 6 column starter bars',           status:'In Progress', priority:'Medium',assignee:'USR-005', startDate:'2026-05-16', endDate:'2026-05-22', progress:30,  estimatedHours:80,  actualHours:24,  description:'Starter bar installation for level 6 columns.' },
    { id:'TSK-1006', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Activity',   activityType:'AT-001', name:'Block A — Level 6 column casting (Grid 1-4)',    status:'Open',         priority:'High',  assignee:'USR-005', startDate:'2026-05-25', endDate:'2026-06-02', progress:0,   estimatedHours:120, actualHours:0,   description:'M30 concrete columns for grid lines 1 to 4 on level 6.' },
    { id:'TSK-1007', projectId:'PROJ-2026-001-A', workPackageId:'WP-004', task_type:'Activity',   activityType:'AT-003', name:'Block A — Level 3 partition walls (East wing)', status:'In Progress', priority:'Medium',assignee:'USR-006', startDate:'2026-05-10', endDate:'2026-05-30', progress:55,  estimatedHours:200, actualHours:110, description:'230mm brick partition walls — east wing of level 3.' },
    { id:'TSK-1008', projectId:'PROJ-2026-001-A', workPackageId:'WP-004', task_type:'Activity',                          name:'Block A — Level 4 partition walls (East wing)', status:'Open',         priority:'Medium',assignee:'USR-006', startDate:'2026-05-25', endDate:'2026-06-15', progress:0,   estimatedHours:200, actualHours:0,   description:'230mm brick partition walls — east wing of level 4.' },
    { id:'TSK-1009', projectId:'PROJ-2026-001-A', workPackageId:'WP-005', task_type:'Milestone',                         name:'Block A — Sleeve & insert layout for MEP',       status:'Open',         priority:'Medium',assignee:'USR-007', startDate:'2026-06-01', endDate:'2026-06-20', progress:0,   estimatedHours:160, actualHours:0,   description:'MEP sleeve and insert layout drawings to be finalised before slab casting.' },

    // Block A — Inspection seed (TSK-1013, added in Session 31 to demo the QC gate task_type)
    { id:'TSK-1013', projectId:'PROJ-2026-001-A', workPackageId:'WP-003', task_type:'Inspection',                        name:'Block A — Level 5 slab pour QC inspection',      status:'Completed',   priority:'High',  assignee:'USR-004', startDate:'2026-05-15', endDate:'2026-05-18', progress:100, estimatedHours:8,   actualHours:6,   description:'Quality-control sign-off on M30 slab pour — cube test sample, vibration check, finish acceptance.' },

    // Block B tasks
    { id:'TSK-1010', projectId:'PROJ-2026-001-B', workPackageId:'WP-008', task_type:'Activity',   activityType:'AT-002', name:'Block B — Level 3 slab casting',                  status:'Completed',    priority:'High',  assignee:'USR-006', startDate:'2026-05-02', endDate:'2026-05-06', progress:100, estimatedHours:40,  actualHours:38,  description:'M30 slab casting for level 3.' },
    { id:'TSK-1011', projectId:'PROJ-2026-001-B', workPackageId:'WP-008', task_type:'Activity',   activityType:'AT-001', name:'Block B — Level 4 column casting',                status:'In Progress',  priority:'High',  assignee:'USR-006', startDate:'2026-05-10', endDate:'2026-05-20', progress:60,  estimatedHours:100, actualHours:60,  description:'M30 columns for level 4.' },
    { id:'TSK-1012', projectId:'PROJ-2026-001-B', workPackageId:'WP-009', task_type:'Milestone',  activityType:'AT-003', name:'Block B — Level 1 partition walls',               status:'In Progress',  priority:'Medium',assignee:'USR-006', startDate:'2026-05-12', endDate:'2026-06-05', progress:40,  estimatedHours:180, actualHours:72,  description:'230mm brick partition walls — level 1.' },

    // Block B — Inspection seed (TSK-1014, added in Session 31)
    { id:'TSK-1014', projectId:'PROJ-2026-001-B', workPackageId:'WP-008', task_type:'Inspection',                        name:'Block B — Level 4 column rebar QC inspection',   status:'Completed',   priority:'High',  assignee:'USR-004', startDate:'2026-05-09', endDate:'2026-05-10', progress:100, estimatedHours:4,   actualHours:3,   description:'Pre-pour rebar inspection — bar diameter, spacing, cover, stirrup configuration.' },

    // Chennai tasks
    { id:'TSK-2001', projectId:'PROJ-2026-002', workPackageId:'WP-010', task_type:'Activity',   activityType:'AT-008', name:'CHN — Site grading & retaining wall layout',       status:'Completed',    priority:'High',  assignee:'USR-003', startDate:'2026-03-05', endDate:'2026-04-15', progress:100, estimatedHours:240, actualHours:235, description:'Initial site grading and retaining wall layout.' },
    { id:'TSK-2002', projectId:'PROJ-2026-002', workPackageId:'WP-011', task_type:'Activity',                          name:'CHN — Tower 1 raft foundation reinforcement',      status:'In Progress',  priority:'High',  assignee:'USR-003', startDate:'2026-05-01', endDate:'2026-06-15', progress:55,  estimatedHours:320, actualHours:176, description:'Tower 1 raft foundation steel work.' },
  ],

  // ===== Activity Type (master, CLAUDE.md §13.3 item 16) =====
  // RENAMED in Session 31 from "Task Type" to align with proposal §M2 — proposal
  // reserves task_type as a Select field on Task (Activity / Milestone / Inspection).
  // The master here is now Activity Type: construction activity templates with
  // default checklist, labour mix (skilled/unskilled ratio), and expected
  // productivity. Tasks link to an Activity Type via `activityType` (optional).
  // `applicableProjectTypes` is the Project Type → Activity Type mapping that
  // enables template-based task creation. ID prefix changed TT- → AT-.
  activityTypes: [
    { id:'AT-001', name:'RCC Column Casting', category:'Structural',
      description:'Casting reinforced concrete columns. Typically uses M25-M40 grade concrete.',
      defaultChecklist:[
        { item:'Formwork inspection complete' },
        { item:'Reinforcement check by QS' },
        { item:'Concrete grade verified' },
        { item:'Curing plan in place' },
      ],
      defaultSkilledRatio:0.3, defaultUnskilledRatio:0.7,
      expectedProductivityPerManDay:0.8, productivityUnit:'m³',
      applicableProjectTypes:['Commercial','Residential','Infrastructure','Industrial'] },
    { id:'AT-002', name:'RCC Slab Casting', category:'Structural',
      description:'Casting reinforced concrete slabs. Continuous pour discipline required.',
      defaultChecklist:[
        { item:'Formwork and propping checked' },
        { item:'Reinforcement BBS verified' },
        { item:'MEP sleeves and inserts placed' },
        { item:'Concrete grade verified' },
        { item:'Vibration and curing plan ready' },
      ],
      defaultSkilledRatio:0.25, defaultUnskilledRatio:0.75,
      expectedProductivityPerManDay:2.5, productivityUnit:'m³',
      applicableProjectTypes:['Commercial','Residential','Infrastructure','Industrial'] },
    { id:'AT-003', name:'Brick Masonry — 230mm', category:'Finishing',
      description:'230mm thick brick partition walls — burnt clay brick + cement mortar.',
      defaultChecklist:[
        { item:'Wall layout marked on slab' },
        { item:'First course aligned and plumbed' },
        { item:'Mortar mix ratio verified' },
        { item:'Brick soaking done' },
      ],
      defaultSkilledRatio:0.5, defaultUnskilledRatio:0.5,
      expectedProductivityPerManDay:4.0, productivityUnit:'m²',
      applicableProjectTypes:['Commercial','Residential'] },
    { id:'AT-004', name:'Plastering — Internal', category:'Finishing',
      description:'Cement plaster — internal walls and ceilings, 12-15mm thick.',
      defaultChecklist:[
        { item:'Surface preparation done' },
        { item:'Substrate dampened' },
        { item:'Mortar mix ratio verified' },
        { item:'Curing plan in place' },
      ],
      defaultSkilledRatio:0.5, defaultUnskilledRatio:0.5,
      expectedProductivityPerManDay:10.0, productivityUnit:'m²',
      applicableProjectTypes:['Commercial','Residential'] },
    { id:'AT-005', name:'Floor Tiling', category:'Finishing',
      description:'Vitrified / ceramic floor tile laying with adhesive or mortar bed.',
      defaultChecklist:[
        { item:'Base level and slope verified' },
        { item:'Tile layout marked' },
        { item:'Adhesive grade verified' },
        { item:'Grouting plan in place' },
      ],
      defaultSkilledRatio:0.7, defaultUnskilledRatio:0.3,
      expectedProductivityPerManDay:6.0, productivityUnit:'m²',
      applicableProjectTypes:['Commercial','Residential'] },
    { id:'AT-006', name:'Electrical Conduit Laying', category:'MEP',
      description:'Concealed PVC/MS conduit laying in walls and slabs prior to plaster.',
      defaultChecklist:[
        { item:'Conduit route marked per drawing' },
        { item:'Drilling locations approved' },
        { item:'Conduit grade verified' },
        { item:'Pull wires inserted' },
      ],
      defaultSkilledRatio:0.8, defaultUnskilledRatio:0.2,
      expectedProductivityPerManDay:12.0, productivityUnit:'m',
      applicableProjectTypes:['Commercial','Residential','Industrial'] },
    { id:'AT-007', name:'Plumbing Rough-in', category:'MEP',
      description:'Rough-in of water supply and drainage piping before wall closure.',
      defaultChecklist:[
        { item:'Plumbing layout marked per drawing' },
        { item:'Pipe grade and ratings verified' },
        { item:'Slopes verified' },
        { item:'Pressure test scheduled' },
      ],
      defaultSkilledRatio:0.7, defaultUnskilledRatio:0.3,
      expectedProductivityPerManDay:8.0, productivityUnit:'m',
      applicableProjectTypes:['Commercial','Residential','Industrial'] },
    { id:'AT-008', name:'Excavation in Ordinary Soil', category:'Earthwork',
      description:'Excavation in ordinary soil up to 1.5m depth, including disposal.',
      defaultChecklist:[
        { item:'Service clearance certificate received' },
        { item:'Excavation depth marked' },
        { item:'Shoring plan in place' },
        { item:'Dewatering plan ready' },
      ],
      defaultSkilledRatio:0.1, defaultUnskilledRatio:0.9,
      expectedProductivityPerManDay:3.5, productivityUnit:'m³',
      applicableProjectTypes:['Infrastructure','Commercial','Residential','Industrial'] },
  ],

  // ===== Stage Planning (CLAUDE.md §13.3 item 18) =====
  // Stages-as-structure only. Each stage groups tasks under a date-bounded phase
  // and captures planned targets. Stage Review (the aggregate scorecard that rolls
  // up labour / procurement / GL data) is deferred to M3+ per §13.3 — DO NOT
  // build a review UI here. `stagePlanningTasks` is a CHILD TABLE embedded inside
  // each stage record (not a separate slice). `dependencies` is an array of
  // sibling stage IDs this stage waits on.
  stagePlannings: [
    // ----- Block A — Office Tower (PROJ-2026-001-A) -----
    { id:'STG-001', stageName:'Foundation Stage', project:'PROJ-2026-001-A',
      plannedStart:'2026-02-15', plannedEnd:'2026-04-10',
      plannedTaskCount:8, plannedCompletionPct:100,
      description:'Earthwork, excavation, PCC, and raft foundation casting for Block A.',
      dependencies:[],
      stagePlanningTasks:[] },
    { id:'STG-002', stageName:'Substructure Stage', project:'PROJ-2026-001-A',
      plannedStart:'2026-03-20', plannedEnd:'2026-05-30',
      plannedTaskCount:6, plannedCompletionPct:100,
      description:'Basement walls, raft cap, and ground-floor slab.',
      dependencies:['STG-001'],
      stagePlanningTasks:[] },
    { id:'STG-003', stageName:'Superstructure Stage', project:'PROJ-2026-001-A',
      plannedStart:'2026-05-15', plannedEnd:'2026-07-30',
      plannedTaskCount:12, plannedCompletionPct:100,
      description:'RCC frame — columns, beams, slabs for levels 5-8.',
      dependencies:['STG-002'],
      stagePlanningTasks:[
        { id:'SPT-0001', task:'TSK-1001', plannedStart:'2026-04-20', plannedEnd:'2026-04-28', plannedQty:24,  qtyUnit:'m³' },
        { id:'SPT-0002', task:'TSK-1002', plannedStart:'2026-04-29', plannedEnd:'2026-05-05', plannedQty:24,  qtyUnit:'m³' },
        { id:'SPT-0003', task:'TSK-1003', plannedStart:'2026-05-06', plannedEnd:'2026-05-14', plannedQty:380, qtyUnit:'m²' },
        { id:'SPT-0004', task:'TSK-1004', plannedStart:'2026-05-15', plannedEnd:'2026-05-18', plannedQty:380, qtyUnit:'m²' },
        { id:'SPT-0005', task:'TSK-1005', plannedStart:'2026-05-16', plannedEnd:'2026-05-22', plannedQty:48,  qtyUnit:'nos' },
        { id:'SPT-0006', task:'TSK-1006', plannedStart:'2026-05-25', plannedEnd:'2026-06-02', plannedQty:24,  qtyUnit:'m³' },
      ] },
    { id:'STG-004', stageName:'Finishing Stage', project:'PROJ-2026-001-A',
      plannedStart:'2026-06-10', plannedEnd:'2026-09-15',
      plannedTaskCount:18, plannedCompletionPct:100,
      description:'Masonry, plaster, MEP rough-in, flooring, façade.',
      dependencies:['STG-003'],
      stagePlanningTasks:[
        { id:'SPT-0007', task:'TSK-1007', plannedStart:'2026-05-10', plannedEnd:'2026-05-30', plannedQty:420, qtyUnit:'m²' },
        { id:'SPT-0008', task:'TSK-1008', plannedStart:'2026-05-25', plannedEnd:'2026-06-15', plannedQty:420, qtyUnit:'m²' },
        { id:'SPT-0009', task:'TSK-1009', plannedStart:'2026-06-01', plannedEnd:'2026-06-20', plannedQty:1,   qtyUnit:'set' },
      ] },

    // ----- Block B — Annex (PROJ-2026-001-B) -----
    { id:'STG-005', stageName:'Foundation Stage', project:'PROJ-2026-001-B',
      plannedStart:'2026-03-20', plannedEnd:'2026-05-15',
      plannedTaskCount:6, plannedCompletionPct:100,
      description:'Earthwork and raft foundation casting for Block B.',
      dependencies:[],
      stagePlanningTasks:[] },
    { id:'STG-006', stageName:'Superstructure Stage', project:'PROJ-2026-001-B',
      plannedStart:'2026-05-01', plannedEnd:'2026-08-15',
      plannedTaskCount:10, plannedCompletionPct:100,
      description:'RCC frame for Block B — columns, beams, slabs.',
      dependencies:['STG-005'],
      stagePlanningTasks:[
        { id:'SPT-0010', task:'TSK-1010', plannedStart:'2026-05-02', plannedEnd:'2026-05-06', plannedQty:240, qtyUnit:'m²' },
        { id:'SPT-0011', task:'TSK-1011', plannedStart:'2026-05-10', plannedEnd:'2026-05-20', plannedQty:20,  qtyUnit:'m³' },
      ] },
    { id:'STG-007', stageName:'Finishing Stage', project:'PROJ-2026-001-B',
      plannedStart:'2026-07-01', plannedEnd:'2026-09-15',
      plannedTaskCount:14, plannedCompletionPct:100,
      description:'Masonry, plaster, flooring for Block B.',
      dependencies:['STG-006'],
      stagePlanningTasks:[
        { id:'SPT-0012', task:'TSK-1012', plannedStart:'2026-05-12', plannedEnd:'2026-06-05', plannedQty:340, qtyUnit:'m²' },
      ] },

    // ----- Chennai Residential Towers (PROJ-2026-002) -----
    { id:'STG-008', stageName:'Site Prep & Excavation', project:'PROJ-2026-002',
      plannedStart:'2026-03-01', plannedEnd:'2026-06-30',
      plannedTaskCount:5, plannedCompletionPct:100,
      description:'Site grading, retaining wall layout, mass excavation for raft foundations.',
      dependencies:[],
      stagePlanningTasks:[
        { id:'SPT-0013', task:'TSK-2001', plannedStart:'2026-03-05', plannedEnd:'2026-04-15', plannedQty:2400, qtyUnit:'m³' },
      ] },
    { id:'STG-009', stageName:'Tower Foundations', project:'PROJ-2026-002',
      plannedStart:'2026-04-15', plannedEnd:'2026-09-30',
      plannedTaskCount:9, plannedCompletionPct:100,
      description:'Raft foundations for the three residential towers.',
      dependencies:['STG-008'],
      stagePlanningTasks:[
        { id:'SPT-0014', task:'TSK-2002', plannedStart:'2026-05-01', plannedEnd:'2026-06-15', plannedQty:180, qtyUnit:'ton' },
      ] },
    { id:'STG-010', stageName:'Superstructure', project:'PROJ-2026-002',
      plannedStart:'2026-09-01', plannedEnd:'2027-02-28',
      plannedTaskCount:48, plannedCompletionPct:100,
      description:'G+15 RCC frame for Towers 1-3.',
      dependencies:['STG-009'],
      stagePlanningTasks:[] },
  ],

  // ===== Attachments (CLAUDE.md §13.3 items 13 + 26) =====
  // Frappe-native mirror — `parentDoctype` + `parentId` form the polymorphic
  // back-reference. M1 prototype only surfaces Project attachments; the slice
  // is doctype-aware so future Task / WP / TPE attachment UIs slot in without
  // store changes. **Seed entries have url=null on purpose** — they're metadata-
  // only, since we can't ship binary fixtures through localStorage. The UI
  // shows "(seed sample · no file)" on these rows. Real uploads via the UI's
  // file picker create blob URLs via URL.createObjectURL.
  attachments: [
    { id:'ATT-001', parentDoctype:'Project', parentId:'PROJ-2026-001-A', fileName:'foundation_drawing_rev3.pdf', mime:'application/pdf',           size:845231,  url:null, uploadedAt:'2026-02-12T10:30:00', uploadedBy:'USR-003' },
    { id:'ATT-002', parentDoctype:'Project', parentId:'PROJ-2026-001-A', fileName:'structural_calcs_v2.pdf',     mime:'application/pdf',           size:1382440, url:null, uploadedAt:'2026-02-18T14:22:00', uploadedBy:'USR-003' },
    { id:'ATT-003', parentDoctype:'Project', parentId:'PROJ-2026-001-A', fileName:'sanctioned_plan_blockA.pdf',  mime:'application/pdf',           size:2188504, url:null, uploadedAt:'2026-02-08T09:15:00', uploadedBy:'USR-002' },
    { id:'ATT-004', parentDoctype:'Project', parentId:'PROJ-2026-001-A', fileName:'site_photo_level5_pour.jpg',  mime:'image/jpeg',                size:512300,  url:null, uploadedAt:'2026-05-16T17:45:00', uploadedBy:'USR-005' },
    { id:'ATT-005', parentDoctype:'Project', parentId:'PROJ-2026-001-B', fileName:'substructure_layout.pdf',     mime:'application/pdf',           size:632100,  url:null, uploadedAt:'2026-03-22T11:00:00', uploadedBy:'USR-003' },
    { id:'ATT-006', parentDoctype:'Project', parentId:'PROJ-2026-001-B', fileName:'hvac_layout_floor1-4.dwg',    mime:'application/acad',          size:1922800, url:null, uploadedAt:'2026-04-05T13:10:00', uploadedBy:'USR-007' },
    { id:'ATT-007', parentDoctype:'Project', parentId:'PROJ-2026-002',   fileName:'chennai_grading_plan.pdf',    mime:'application/pdf',           size:982310,  url:null, uploadedAt:'2026-03-02T10:00:00', uploadedBy:'USR-003' },
    { id:'ATT-008', parentDoctype:'Project', parentId:'PROJ-2026-002',   fileName:'casagrand_contract_main.pdf', mime:'application/pdf',           size:3204888, url:null, uploadedAt:'2026-02-26T16:30:00', uploadedBy:'USR-002' },
    { id:'ATT-009', parentDoctype:'Project', parentId:'PROJ-2026-002',   fileName:'soil_report_omr.pdf',         mime:'application/pdf',           size:1284600, url:null, uploadedAt:'2026-02-28T12:00:00', uploadedBy:'USR-004' },
    { id:'ATT-010', parentDoctype:'Project', parentId:'PROJ-2025-014',   fileName:'aluva_station_elevation.dwg', mime:'application/acad',          size:2480420, url:null, uploadedAt:'2025-05-12T11:20:00', uploadedBy:'USR-004' },
    { id:'ATT-011', parentDoctype:'Project', parentId:'PROJ-2025-014',   fileName:'metro_alignment_sheet01.pdf', mime:'application/pdf',           size:1620100, url:null, uploadedAt:'2025-05-08T15:45:00', uploadedBy:'USR-004' },
  ],

  // ===== Settings DocTypes (Session 34 — new for M1) =====
  // Three Single DocTypes that ship in M1 per the Block-B decisions:
  // - BuildSuite Core Settings: org-wide toggles
  // - Site Execution Settings: module operational defaults
  // - Workspace Structure Settings: BSA-driven workspace + shortcut config
  //   (drives the Site Execution landing's shortcut grid — replaces the
  //    hardcoded router.js `links` array)

  coreSettings: {
    enable_company_segregation: true,
    default_project_type: 'Commercial',
    default_company: 'ACME-COM',
    prototype_demo_mode: true,
  },

  siteExecutionSettings: {
    default_task_type: 'Activity',
    auto_propagate_company: true,
    tpe_attachment_required: false,
    cascade_delete_confirmation: true,
  },

  // Workspace Structure — nested child tables. `workspace_definitions` is the
  // parent slice (one row per workspace); `shortcuts` is a child array embedded
  // on each definition (mirrors Frappe child-table pattern, same as
  // stagePlanningTasks on stagePlannings).
  //
  // M1 seeds the Site Execution workspace only. Other workspaces from §12.2 are
  // addable rows as their modules ship in M2+. visible_to_roles is the
  // BSA-controllable role filter; null = visible to all roles with workspace
  // access per the §12.3 visibility matrix.
  workspaceStructure: {
    workspace_definitions: [
      {
        id: 'WSDEF-SITE-EXEC',
        workspace_slug: 'site-execution',
        display_name: 'Site Execution',
        enabled: true,
        visible_to_roles: null, // null = inherit from §12.3 matrix
        shortcuts: [
          // Trimmed shortcut set — WSST-002 (Work Packages), WSST-004 (Stage Planning),
          // and WSST-006 (Scope Change Orders) removed per user direction. The
          // underlying DocTypes still exist and are reachable via direct URL or as
          // tabs inside Project Detail (Work Packages tab, Stage Planning tab, Scope
          // Changes tab). BSA can re-surface any of them via Workspace Structure
          // Settings without code changes.
          { id: 'WSST-001', label: 'Projects',             icon: '📋', route_path: '/app/projects',          visible_to_roles: null,                       sort_order: 1 },
          { id: 'WSST-003', label: 'Tasks',                icon: '✓',  route_path: '/app/tasks',             visible_to_roles: null,                       sort_order: 3 },
          { id: 'WSST-005', label: 'Progress Entries',     icon: '📝', route_path: '/app/progress-entries',  visible_to_roles: ['admin','bsa','director','pm','site-engineer','foreman'], sort_order: 5 },
          { id: 'WSST-007', label: 'Schedule',             icon: '📅', route_path: '/app/schedule',          visible_to_roles: null,                       sort_order: 7 },
        ],
      },
    ],
  },

  // ===== Project Type Settings (Session 39 — exploratory) =====
  // Configurable wrapper around Project Type. The `name` is still the join
  // key onto project.type. `workPackageLabel` (+ plural) overrides the
  // sidebar label / page titles / "+ New X" button text wherever a Project
  // is in context. `defaultTemplate` is the template fixture key (currently
  // same as name in most cases).
  //
  // NOTE: bringing forward two locked-deferred items per the Session 39
  // entry — §13.3 item 19 "Heavy" interpretation (admin UI for Project Type)
  // and Session 36 (configurable WP label, originally deferred to M2).
  // Framed as exploratory prototype visualisation; production design TBD.
  projectTypes: [
    { id: 'PT-001', name: 'Commercial',     workPackageLabel: 'Block',            workPackageLabelPlural: 'Blocks',            defaultTemplate: 'Commercial',     enabled: true, sort_order: 1 },
    { id: 'PT-002', name: 'Residential',    workPackageLabel: 'Tower',            workPackageLabelPlural: 'Towers',            defaultTemplate: 'Residential',    enabled: true, sort_order: 2 },
    { id: 'PT-003', name: 'Infrastructure', workPackageLabel: 'Chainage Segment', workPackageLabelPlural: 'Chainage Segments', defaultTemplate: 'Infrastructure', enabled: true, sort_order: 3 },
    { id: 'PT-004', name: 'Industrial',     workPackageLabel: 'Plant Block',      workPackageLabelPlural: 'Plant Blocks',      defaultTemplate: '',               enabled: true, sort_order: 4 },
    { id: 'PT-005', name: 'Renovation',     workPackageLabel: 'Phase',            workPackageLabelPlural: 'Phases',            defaultTemplate: '',               enabled: true, sort_order: 5 },
  ],

  // ===== M2 — Task Progress Entry (locked DocType, CLAUDE.md §13.3 item 17) =====
  // Canonical M2 progress-update record. The field names below are the locked API
  // surface for Workforce v2 integration — no renames post-M1 launch.
  // progressPct is the NEW CUMULATIVE % after this entry (not a delta).
  // In production a server hook recomputes the parent Task's progress + status
  // from the latest entry — the prototype's store actions simulate that hook.
  taskProgressEntries: [
    // TSK-1001 — Block A Level 5 column casting (Grid 1-4) · Completed
    { id:'TPE-2026-0001', taskId:'TSK-1001', entryDate:'2026-04-28', enteredBy:'USR-005', progressPct:100, narrative:'Final pour complete on grid 1-4. Vibration done; curing started.',                                     attachments:[], skilledLabour:6, unskilledLabour:12, weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1002 — Block A Level 5 column casting (Grid 5-8) · Completed
    { id:'TPE-2026-0002', taskId:'TSK-1002', entryDate:'2026-05-05', enteredBy:'USR-005', progressPct:100, narrative:'All 4 columns cast for grid 5-8. Within estimated hours.',                                              attachments:[], skilledLabour:5, unskilledLabour:10, weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1003 — Block A Level 5 slab reinforcement · Completed (multi-entry)
    { id:'TPE-2026-0003', taskId:'TSK-1003', entryDate:'2026-05-09', enteredBy:'USR-005', progressPct:50,  narrative:'Bottom reinforcement mat tied; top mat starts tomorrow.',                                                attachments:[], skilledLabour:4, unskilledLabour:8,  weather:'Hot',   blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0004', taskId:'TSK-1003', entryDate:'2026-05-14', enteredBy:'USR-005', progressPct:100, narrative:'Top mat done, form-work complete. Ready for slab casting.',                                              attachments:[], skilledLabour:6, unskilledLabour:10, weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1004 — Block A Level 5 slab casting · In Progress 75 (multi-entry)
    { id:'TPE-2026-0005', taskId:'TSK-1004', entryDate:'2026-05-14', enteredBy:'USR-005', progressPct:25,  narrative:'First pour bay (Grid A-D) completed; 95 m³ placed.',                                                     attachments:[], skilledLabour:8, unskilledLabour:14, weather:'Clear', blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0006', taskId:'TSK-1004', entryDate:'2026-05-15', enteredBy:'USR-005', progressPct:50,  narrative:'Bay 2 cast in morning. Bay 3 started in afternoon.',                                                     attachments:[], skilledLabour:8, unskilledLabour:14, weather:'Hot',   blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0007', taskId:'TSK-1004', entryDate:'2026-05-16', enteredBy:'USR-005', progressPct:75,  narrative:'Bays 3-4 complete; 285 of 380 m² done. Afternoon shower delayed final bay; vibrating finished under cover.', attachments:[], skilledLabour:7, unskilledLabour:14, weather:'Rainy', blockerFlag:true,  blockerNote:'Afternoon shower delayed final bay by ~2 hours; production loss compensable.' },

    // TSK-1005 — Block A Level 6 column starter bars · In Progress 30
    { id:'TPE-2026-0008', taskId:'TSK-1005', entryDate:'2026-05-16', enteredBy:'USR-005', progressPct:30,  narrative:'Starter bars set for grid 1-3. Survey rechecked; on alignment.',                                         attachments:[], skilledLabour:3, unskilledLabour:5,  weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1007 — Block A Level 3 partition walls (East wing) · In Progress 55 (multi-entry, USR-006)
    { id:'TPE-2026-0009', taskId:'TSK-1007', entryDate:'2026-05-12', enteredBy:'USR-006', progressPct:30,  narrative:'Rooms 301-303 partitions up to lintel level.',                                                           attachments:[], skilledLabour:5, unskilledLabour:8,  weather:'Clear', blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0010', taskId:'TSK-1007', entryDate:'2026-05-15', enteredBy:'USR-006', progressPct:55,  narrative:'Rooms 304-306 partitions raised; plaster team scheduled next week.',                                     attachments:[], skilledLabour:5, unskilledLabour:9,  weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1010 — Block B Level 3 slab casting · Completed (USR-006)
    { id:'TPE-2026-0011', taskId:'TSK-1010', entryDate:'2026-05-06', enteredBy:'USR-006', progressPct:100, narrative:'Block B Level 3 slab cast in single pour. Cube test sample taken.',                                      attachments:[], skilledLabour:7, unskilledLabour:14, weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1011 — Block B Level 4 column casting · In Progress 60 (USR-006)
    { id:'TPE-2026-0012', taskId:'TSK-1011', entryDate:'2026-05-12', enteredBy:'USR-006', progressPct:30,  narrative:'Grid A-B columns cast. Form removal in 2 days.',                                                         attachments:[], skilledLabour:5, unskilledLabour:9,  weather:'Hot',   blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0013', taskId:'TSK-1011', entryDate:'2026-05-16', enteredBy:'USR-006', progressPct:60,  narrative:'Grid C-D columns cast; full grid complete by end of day.',                                                attachments:[], skilledLabour:5, unskilledLabour:8,  weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-1012 — Block B Level 1 partition walls · In Progress 40 (USR-006)
    { id:'TPE-2026-0014', taskId:'TSK-1012', entryDate:'2026-05-15', enteredBy:'USR-006', progressPct:40,  narrative:'Level 1 East partitions at lintel level; West side started.',                                            attachments:[], skilledLabour:6, unskilledLabour:8,  weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-2001 — Chennai site grading · Completed (USR-003)
    { id:'TPE-2026-0015', taskId:'TSK-2001', entryDate:'2026-04-15', enteredBy:'USR-003', progressPct:100, narrative:'Final grading complete; retaining wall layout marked for excavation team.',                              attachments:[], skilledLabour:4, unskilledLabour:18, weather:'Clear', blockerFlag:false, blockerNote:'' },

    // TSK-2002 — Chennai Tower 1 raft reinforcement · In Progress 55 (multi-entry, USR-003)
    { id:'TPE-2026-0016', taskId:'TSK-2002', entryDate:'2026-05-08', enteredBy:'USR-003', progressPct:25,  narrative:'Bottom raft mat tied for Tower 1.',                                                                       attachments:[], skilledLabour:6, unskilledLabour:14, weather:'Hot',   blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0017', taskId:'TSK-2002', entryDate:'2026-05-12', enteredBy:'USR-003', progressPct:40,  narrative:'Top mat 60% done; continuing into next week.',                                                            attachments:[], skilledLabour:6, unskilledLabour:14, weather:'Clear', blockerFlag:false, blockerNote:'' },
    { id:'TPE-2026-0018', taskId:'TSK-2002', entryDate:'2026-05-16', enteredBy:'USR-003', progressPct:55,  narrative:'Top mat complete; chairs and dowels going in. Ready for inspection.',                                    attachments:[], skilledLabour:7, unskilledLabour:14, weather:'Clear', blockerFlag:false, blockerNote:'' },
  ],

  scos: [
    { id:'SCO-2026-0008', projectId:'PROJ-2026-001-A', title:'Foundation depth revision — soil report', type:'Design Change',   impact:2840000,  recoverable:true,  status:'Pending Approval', raisedBy:'USR-002', raisedDate:'2026-05-12', reason:'Updated soil bearing test requires foundation depth increased from 2.5m to 3.2m in Block A.', boqRevisionRef:null },
    { id:'SCO-2026-0007', projectId:'PROJ-2026-001-A', title:'Façade material upgrade — client request',  type:'Client Request', impact:1620000, recoverable:true,  status:'Approved',         raisedBy:'USR-004', raisedDate:'2026-04-22', reason:'Client requested upgrade from ACP to glass curtain wall on north elevation.', boqRevisionRef:'BOQ-A-R2' },
    { id:'SCO-2026-0006', projectId:'PROJ-2026-002', title:'Plumbing rerouting — design clash',           type:'Design Change',   impact:480000,  recoverable:false, status:'Approved',         raisedBy:'USR-003', raisedDate:'2026-04-15', reason:'MEP coordination identified clashes; rerouting needed in service shaft.', boqRevisionRef:null },
    { id:'SCO-2026-0005', projectId:'PROJ-2025-014', title:'Additional rain water harvesting tank',      type:'Statutory',       impact:185000,  recoverable:true,  status:'Pending Approval', raisedBy:'USR-004', raisedDate:'2026-05-01', reason:'New municipal byelaw requires additional 30 kL RWH tank.', boqRevisionRef:null },
  ],

  // ===== M3 — Construction Rate Master =====
  // QS-maintained price book for all standard components. Sub-items in BOQs auto-fetch rate from here.
  // Updated automatically when a Purchase Order is approved at a different rate (simulated via 'source').
  rateMaster: [
    // Materials
    { id:'RM-MAT-001', code:'CEM-OPC53', category:'Material', description:'Cement — OPC 53 Grade',              unit:'bag (50 kg)', currentRate:425,   updatedAt:'2026-04-12', source:'PO-2026-0142', updatedBy:'USR-004' },
    { id:'RM-MAT-002', code:'SAND-RIV',  category:'Material', description:'River Sand — washed, plaster grade', unit:'m³',          currentRate:2100,  updatedAt:'2026-03-28', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-MAT-003', code:'AGG-20MM',  category:'Material', description:'Aggregate — 20mm crushed stone',     unit:'m³',          currentRate:1450,  updatedAt:'2026-04-02', source:'PO-2026-0156', updatedBy:'USR-004' },
    { id:'RM-MAT-004', code:'TMT-FE500', category:'Material', description:'TMT Rebar — Fe500 grade',            unit:'kg',          currentRate:68,    updatedAt:'2026-05-08', source:'PO-2026-0188', updatedBy:'USR-004' },
    { id:'RM-MAT-005', code:'BRK-CMN',   category:'Material', description:'Common burnt brick — 230×110×75',    unit:'piece',       currentRate:9.5,   updatedAt:'2026-03-15', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-MAT-006', code:'RMC-M25',   category:'Material', description:'Ready-mix concrete — M25 grade',     unit:'m³',          currentRate:6500,  updatedAt:'2026-04-22', source:'PO-2026-0171', updatedBy:'USR-004' },
    { id:'RM-MAT-007', code:'RMC-M30',   category:'Material', description:'Ready-mix concrete — M30 grade',     unit:'m³',          currentRate:7200,  updatedAt:'2026-04-22', source:'PO-2026-0171', updatedBy:'USR-004' },
    { id:'RM-MAT-008', code:'PLY-18MM',  category:'Material', description:'Plywood shuttering — 18mm BWP',      unit:'m²',          currentRate:520,   updatedAt:'2026-02-18', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-MAT-009', code:'WPF-CMB',   category:'Material', description:'Waterproofing compound — crystalline',unit:'kg',          currentRate:185,   updatedAt:'2026-03-08', source:'PO-2026-0098', updatedBy:'USR-004' },
    // Labour
    { id:'RM-LAB-001', code:'LAB-MSN-S', category:'Labour',   description:'Mason — skilled (1st class)',         unit:'day',         currentRate:950,   updatedAt:'2026-04-01', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-LAB-002', code:'LAB-BAR',   category:'Labour',   description:'Bar bender / steel fixer',            unit:'day',         currentRate:880,   updatedAt:'2026-04-01', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-LAB-003', code:'LAB-HLP',   category:'Labour',   description:'Helper / unskilled labourer',         unit:'day',         currentRate:620,   updatedAt:'2026-04-01', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-LAB-004', code:'LAB-CRP',   category:'Labour',   description:'Carpenter — shuttering',              unit:'day',         currentRate:920,   updatedAt:'2026-04-01', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-LAB-005', code:'LAB-PLM',   category:'Labour',   description:'Plumber — certified',                 unit:'day',         currentRate:1050,  updatedAt:'2026-04-15', source:'Manual',         updatedBy:'USR-004' },
    // Equipment
    { id:'RM-EQP-001', code:'EQP-MIX',   category:'Equipment',description:'Concrete mixer — 10/7 cu.ft',         unit:'day',         currentRate:1800,  updatedAt:'2026-02-10', source:'Manual',         updatedBy:'USR-004' },
    { id:'RM-EQP-002', code:'EQP-TC',    category:'Equipment',description:'Tower crane — 8T (hire)',             unit:'day',         currentRate:14500, updatedAt:'2026-02-10', source:'PO-2026-0034', updatedBy:'USR-004' },
    { id:'RM-EQP-003', code:'EQP-VIB',   category:'Equipment',description:'Vibrator needle — 50mm',              unit:'day',         currentRate:450,   updatedAt:'2026-02-10', source:'Manual',         updatedBy:'USR-004' },
  ],

  // Rate change history — used to show the rate sparkline / audit trail on Rate Master.
  rateHistory: [
    { id:'RH-001', rateMasterId:'RM-MAT-001', rate:395, effectiveDate:'2025-12-05', source:'Manual',         updatedBy:'USR-004' },
    { id:'RH-002', rateMasterId:'RM-MAT-001', rate:410, effectiveDate:'2026-02-18', source:'PO-2026-0089', updatedBy:'USR-007' },
    { id:'RH-003', rateMasterId:'RM-MAT-001', rate:425, effectiveDate:'2026-04-12', source:'PO-2026-0142', updatedBy:'USR-007' },
    { id:'RH-004', rateMasterId:'RM-MAT-004', rate:62,  effectiveDate:'2026-01-20', source:'Manual',         updatedBy:'USR-004' },
    { id:'RH-005', rateMasterId:'RM-MAT-004', rate:65,  effectiveDate:'2026-03-15', source:'PO-2026-0124', updatedBy:'USR-007' },
    { id:'RH-006', rateMasterId:'RM-MAT-004', rate:68,  effectiveDate:'2026-05-08', source:'PO-2026-0188', updatedBy:'USR-007' },
    { id:'RH-007', rateMasterId:'RM-MAT-006', rate:6200, effectiveDate:'2026-02-22', source:'Manual',        updatedBy:'USR-004' },
    { id:'RH-008', rateMasterId:'RM-MAT-006', rate:6500, effectiveDate:'2026-04-22', source:'PO-2026-0171', updatedBy:'USR-007' },
    { id:'RH-009', rateMasterId:'RM-MAT-007', rate:6900, effectiveDate:'2026-02-22', source:'Manual',        updatedBy:'USR-004' },
    { id:'RH-010', rateMasterId:'RM-MAT-007', rate:7200, effectiveDate:'2026-04-22', source:'PO-2026-0171', updatedBy:'USR-007' },
  ],

  // ===== M3 — Bills of Quantities (BOQs) =====
  // BOQ has revisions. Each BOQ row is a single revision snapshot.
  // - 'revision' = revision number; baseRevisionId points to predecessor.
  // - 'status': Draft / Submitted / Approved / Superseded.
  // - Only one Approved revision is "active" per project at a time; others are Superseded.
  // - Linked via sourceScoId when a revision was triggered by an approved SCO.
  boqs: [
    // Block A — Revision 1 (original, now Superseded by R2 after façade SCO)
    { id:'BOQ-A-R1', projectId:'PROJ-2026-001-A', revision:1, baseRevisionId:null,       status:'Superseded', sourceScoId:null,           title:'Block A — Original BOQ', preparedBy:'USR-004', preparedDate:'2026-02-12', approvedBy:'USR-002', approvedDate:'2026-02-14' },
    // Block A — Revision 2 (active, triggered by approved SCO-2026-0007 façade upgrade)
    { id:'BOQ-A-R2', projectId:'PROJ-2026-001-A', revision:2, baseRevisionId:'BOQ-A-R1', status:'Approved',   sourceScoId:'SCO-2026-0007', title:'Block A — Revision 2 (post façade upgrade)', preparedBy:'USR-004', preparedDate:'2026-04-23', approvedBy:'USR-002', approvedDate:'2026-04-25' },
    // Block B — single revision, approved
    { id:'BOQ-B-R1', projectId:'PROJ-2026-001-B', revision:1, baseRevisionId:null,       status:'Approved',   sourceScoId:null,           title:'Block B — Original BOQ', preparedBy:'USR-004', preparedDate:'2026-03-18', approvedBy:'USR-003', approvedDate:'2026-03-20' },
    // Chennai — draft, not yet submitted
    { id:'BOQ-CHN-R1', projectId:'PROJ-2026-002', revision:1, baseRevisionId:null,       status:'Draft',      sourceScoId:null,           title:'Chennai Towers — Draft BOQ', preparedBy:'USR-004', preparedDate:'2026-04-30', approvedBy:null, approvedDate:null },
  ],

  // BOQ Groups (Level 1 of 3) — top-level trade / work-package grouping.
  boqGroups: [
    // Block A R2 (active)
    { id:'BG-A2-1', boqId:'BOQ-A-R2', code:'A', name:'Civil Works — RCC',          order:1 },
    { id:'BG-A2-2', boqId:'BOQ-A-R2', code:'B', name:'Masonry & Plaster',          order:2 },
    { id:'BG-A2-3', boqId:'BOQ-A-R2', code:'C', name:'MEP — Mechanical & Plumbing',order:3 },
    { id:'BG-A2-4', boqId:'BOQ-A-R2', code:'D', name:'Finishing & Façade',         order:4 },
    // Block A R1 (superseded) — same group structure for compare
    { id:'BG-A1-1', boqId:'BOQ-A-R1', code:'A', name:'Civil Works — RCC',          order:1 },
    { id:'BG-A1-2', boqId:'BOQ-A-R1', code:'B', name:'Masonry & Plaster',          order:2 },
    { id:'BG-A1-3', boqId:'BOQ-A-R1', code:'C', name:'MEP — Mechanical & Plumbing',order:3 },
    { id:'BG-A1-4', boqId:'BOQ-A-R1', code:'D', name:'Finishing & Façade',         order:4 },
    // Block B
    { id:'BG-B1-1', boqId:'BOQ-B-R1', code:'A', name:'Civil Works — RCC',          order:1 },
    { id:'BG-B1-2', boqId:'BOQ-B-R1', code:'B', name:'Masonry & Plaster',          order:2 },
    // Chennai draft
    { id:'BG-C1-1', boqId:'BOQ-CHN-R1', code:'A', name:'Site Works',               order:1 },
    { id:'BG-C1-2', boqId:'BOQ-CHN-R1', code:'B', name:'Civil Works — RCC',        order:2 },
  ],

  // BOQ Items (Level 2 of 3) — measurable work items with qty, rate, unit.
  // 'taskId' links to a WBS task for actual-progress rollup.
  // actualQty / actualAmount populated from task progress on demand (recalculateActuals).
  boqItems: [
    // ---------- BOQ-A-R2 (Block A — active revision) ----------
    // Civil Works
    { id:'BI-A2-A01', boqId:'BOQ-A-R2', groupId:'BG-A2-1', code:'A.01', description:'RCC M30 — columns (incl. shuttering, vibrating, curing)',        unit:'m³',  plannedQty:240,  rate:7200, plannedAmount:1728000, actualQty:175, actualAmount:1260000, taskId:'TSK-1001' },
    { id:'BI-A2-A02', boqId:'BOQ-A-R2', groupId:'BG-A2-1', code:'A.02', description:'RCC M30 — slab including formwork & curing',                       unit:'m³',  plannedQty:380,  rate:7200, plannedAmount:2736000, actualQty:255, actualAmount:1836000, taskId:'TSK-1004' },
    { id:'BI-A2-A03', boqId:'BOQ-A-R2', groupId:'BG-A2-1', code:'A.03', description:'Reinforcement — Fe500 TMT bars, cut, bent, placed and tied',     unit:'kg',  plannedQty:48000,rate:75,   plannedAmount:3600000, actualQty:32400,actualAmount:2430000, taskId:'TSK-1003' },
    { id:'BI-A2-A04', boqId:'BOQ-A-R2', groupId:'BG-A2-1', code:'A.04', description:'Formwork — plywood shuttering for slab and beams',                unit:'m²',  plannedQty:1620, rate:380,  plannedAmount:615600,  actualQty:1095, actualAmount:416100, taskId:'TSK-1003' },
    // Masonry
    { id:'BI-A2-B01', boqId:'BOQ-A-R2', groupId:'BG-A2-2', code:'B.01', description:'Brick masonry — 230mm thick partition wall in CM 1:6',           unit:'m³',  plannedQty:520,  rate:6850, plannedAmount:3562000, actualQty:198, actualAmount:1356300, taskId:'TSK-1007' },
    { id:'BI-A2-B02', boqId:'BOQ-A-R2', groupId:'BG-A2-2', code:'B.02', description:'Internal plaster — 12mm thick in CM 1:6',                          unit:'m²',  plannedQty:3800, rate:215,  plannedAmount:817000,  actualQty:0,    actualAmount:0,       taskId:null },
    // MEP
    { id:'BI-A2-C01', boqId:'BOQ-A-R2', groupId:'BG-A2-3', code:'C.01', description:'MEP sleeve & embed layout and casting',                            unit:'lot', plannedQty:1,    rate:680000,plannedAmount:680000, actualQty:0.2,  actualAmount:136000,  taskId:'TSK-1009' },
    { id:'BI-A2-C02', boqId:'BOQ-A-R2', groupId:'BG-A2-3', code:'C.02', description:'Plumbing rough-in — drainage and water supply stacks',            unit:'lot', plannedQty:1,    rate:1450000,plannedAmount:1450000,actualQty:0,    actualAmount:0,       taskId:null },
    // Finishing — façade upgraded from ACP to curtain glass in R2 (SCO-2026-0007)
    { id:'BI-A2-D01', boqId:'BOQ-A-R2', groupId:'BG-A2-4', code:'D.01', description:'Glass curtain wall — unitised, structurally glazed (north elev.)', unit:'m²', plannedQty:820,  rate:8500, plannedAmount:6970000, actualQty:0,    actualAmount:0,       taskId:null },
    { id:'BI-A2-D02', boqId:'BOQ-A-R2', groupId:'BG-A2-4', code:'D.02', description:'Vitrified tile flooring — 600×600 double-charged',                unit:'m²',  plannedQty:2400, rate:1250, plannedAmount:3000000, actualQty:0,    actualAmount:0,       taskId:null },

    // ---------- BOQ-A-R1 (Block A — superseded original) ----------
    // Same line items except D.01 was ACP cladding at lower rate
    { id:'BI-A1-A01', boqId:'BOQ-A-R1', groupId:'BG-A1-1', code:'A.01', description:'RCC M30 — columns (incl. shuttering, vibrating, curing)',        unit:'m³',  plannedQty:240,  rate:7200, plannedAmount:1728000, actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-A02', boqId:'BOQ-A-R1', groupId:'BG-A1-1', code:'A.02', description:'RCC M30 — slab including formwork & curing',                       unit:'m³',  plannedQty:380,  rate:7200, plannedAmount:2736000, actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-A03', boqId:'BOQ-A-R1', groupId:'BG-A1-1', code:'A.03', description:'Reinforcement — Fe500 TMT bars, cut, bent, placed and tied',     unit:'kg',  plannedQty:48000,rate:75,   plannedAmount:3600000, actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-A04', boqId:'BOQ-A-R1', groupId:'BG-A1-1', code:'A.04', description:'Formwork — plywood shuttering for slab and beams',                unit:'m²',  plannedQty:1620, rate:380,  plannedAmount:615600,  actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-B01', boqId:'BOQ-A-R1', groupId:'BG-A1-2', code:'B.01', description:'Brick masonry — 230mm thick partition wall in CM 1:6',           unit:'m³',  plannedQty:520,  rate:6850, plannedAmount:3562000, actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-B02', boqId:'BOQ-A-R1', groupId:'BG-A1-2', code:'B.02', description:'Internal plaster — 12mm thick in CM 1:6',                          unit:'m²',  plannedQty:3800, rate:215,  plannedAmount:817000,  actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-C01', boqId:'BOQ-A-R1', groupId:'BG-A1-3', code:'C.01', description:'MEP sleeve & embed layout and casting',                            unit:'lot', plannedQty:1,    rate:680000,plannedAmount:680000, actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-C02', boqId:'BOQ-A-R1', groupId:'BG-A1-3', code:'C.02', description:'Plumbing rough-in — drainage and water supply stacks',            unit:'lot', plannedQty:1,    rate:1450000,plannedAmount:1450000,actualQty:0,actualAmount:0, taskId:null },
    { id:'BI-A1-D01', boqId:'BOQ-A-R1', groupId:'BG-A1-4', code:'D.01', description:'ACP cladding — 4mm aluminium composite panel (north elev.)',      unit:'m²',  plannedQty:820,  rate:2850, plannedAmount:2337000, actualQty:0, actualAmount:0, taskId:null },
    { id:'BI-A1-D02', boqId:'BOQ-A-R1', groupId:'BG-A1-4', code:'D.02', description:'Vitrified tile flooring — 600×600 double-charged',                unit:'m²',  plannedQty:2400, rate:1250, plannedAmount:3000000, actualQty:0, actualAmount:0, taskId:null },

    // ---------- BOQ-B-R1 (Block B — approved) ----------
    { id:'BI-B1-A01', boqId:'BOQ-B-R1', groupId:'BG-B1-1', code:'A.01', description:'RCC M30 — columns',                                                unit:'m³',  plannedQty:180,  rate:7200, plannedAmount:1296000, actualQty:110, actualAmount:792000, taskId:'TSK-1011' },
    { id:'BI-B1-A02', boqId:'BOQ-B-R1', groupId:'BG-B1-1', code:'A.02', description:'RCC M30 — slab',                                                    unit:'m³',  plannedQty:260,  rate:7200, plannedAmount:1872000, actualQty:260, actualAmount:1872000, taskId:'TSK-1010' },
    { id:'BI-B1-A03', boqId:'BOQ-B-R1', groupId:'BG-B1-1', code:'A.03', description:'Reinforcement — Fe500 TMT',                                        unit:'kg',  plannedQty:32000,rate:75,   plannedAmount:2400000, actualQty:21500,actualAmount:1612500, taskId:null },
    { id:'BI-B1-B01', boqId:'BOQ-B-R1', groupId:'BG-B1-2', code:'B.01', description:'Brick masonry — 230mm partition wall',                             unit:'m³',  plannedQty:380,  rate:6850, plannedAmount:2603000, actualQty:152, actualAmount:1041200, taskId:'TSK-1012' },

    // ---------- BOQ-CHN-R1 (Chennai — draft) ----------
    { id:'BI-C1-A01', boqId:'BOQ-CHN-R1', groupId:'BG-C1-1', code:'A.01', description:'Site grading, levelling & retaining wall layout',                unit:'m²',  plannedQty:8500, rate:185,  plannedAmount:1572500, actualQty:8500, actualAmount:1572500, taskId:'TSK-2001' },
    { id:'BI-C1-A02', boqId:'BOQ-CHN-R1', groupId:'BG-C1-2', code:'B.01', description:'Tower 1 raft — RCC M30',                                          unit:'m³',  plannedQty:480,  rate:7200, plannedAmount:3456000, actualQty:264, actualAmount:1900800, taskId:'TSK-2002' },
    { id:'BI-C1-A03', boqId:'BOQ-CHN-R1', groupId:'BG-C1-2', code:'B.02', description:'Tower 1 raft — Fe500 reinforcement',                              unit:'kg',  plannedQty:64000,rate:75,   plannedAmount:4800000, actualQty:35200,actualAmount:2640000, taskId:'TSK-2002' },
  ],

  // BOQ Sub-items (Level 3 of 3) — optional rate-analysis breakdown.
  // 'qtyPerUnit' is consumption per unit of parent item (e.g. 7.5 bags of cement per m³ of M30 concrete).
  // 'rateMasterId' enables auto-rate fetch from Construction Rate Master.
  boqSubItems: [
    // Rate analysis for BI-A2-A01 / BI-A2-A02 (RCC M30) — per m³
    { id:'BS-A2-A01-1', boqId:'BOQ-A-R2', itemId:'BI-A2-A01', rateMasterId:'RM-MAT-007', description:'Ready-mix M30',           qtyPerUnit:1.02,  rate:7200, amount:7344.00 },
    { id:'BS-A2-A01-2', boqId:'BOQ-A-R2', itemId:'BI-A2-A01', rateMasterId:'RM-EQP-003', description:'Vibrator needle',          qtyPerUnit:0.10,  rate:450,  amount:45.00 },
    { id:'BS-A2-A01-3', boqId:'BOQ-A-R2', itemId:'BI-A2-A01', rateMasterId:'RM-LAB-001', description:'Mason (skilled)',           qtyPerUnit:0.40,  rate:950,  amount:380.00 },
    { id:'BS-A2-A01-4', boqId:'BOQ-A-R2', itemId:'BI-A2-A01', rateMasterId:'RM-LAB-003', description:'Helper / unskilled',        qtyPerUnit:1.20,  rate:620,  amount:744.00 },
    // Rate analysis for BI-A2-A03 (Reinforcement) — per kg
    { id:'BS-A2-A03-1', boqId:'BOQ-A-R2', itemId:'BI-A2-A03', rateMasterId:'RM-MAT-004', description:'TMT Fe500 rebar',          qtyPerUnit:1.05,  rate:68,   amount:71.40 },
    { id:'BS-A2-A03-2', boqId:'BOQ-A-R2', itemId:'BI-A2-A03', rateMasterId:'RM-LAB-002', description:'Bar bender',                qtyPerUnit:0.012, rate:880,  amount:10.56 },
    // Rate analysis for BI-A2-B01 (Brick masonry) — per m³
    { id:'BS-A2-B01-1', boqId:'BOQ-A-R2', itemId:'BI-A2-B01', rateMasterId:'RM-MAT-005', description:'Brick (230×110×75)',       qtyPerUnit:500,   rate:9.5,  amount:4750.00 },
    { id:'BS-A2-B01-2', boqId:'BOQ-A-R2', itemId:'BI-A2-B01', rateMasterId:'RM-MAT-001', description:'Cement — OPC 53',          qtyPerUnit:2.5,   rate:425,  amount:1062.50 },
    { id:'BS-A2-B01-3', boqId:'BOQ-A-R2', itemId:'BI-A2-B01', rateMasterId:'RM-MAT-002', description:'River sand',                qtyPerUnit:0.27,  rate:2100, amount:567.00 },
    { id:'BS-A2-B01-4', boqId:'BOQ-A-R2', itemId:'BI-A2-B01', rateMasterId:'RM-LAB-001', description:'Mason (skilled)',           qtyPerUnit:0.45,  rate:950,  amount:427.50 },
  ],
}
