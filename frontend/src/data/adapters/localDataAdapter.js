import { reactive, computed, unref } from 'vue'

/**
 * Local adapter — wraps existing Pinia store getters in the shared
 * { data, loading, error } resource envelope so the view layer is
 * adapter-agnostic. No network calls; loading is always false.
 */
export function createLocalDataAdapter(store) {
  function toDocTypeRows(doctype) {
    if (doctype === 'Project') {
      return store.projects.map((p) => ({
        name: p.id,
        project_name: p.name,
        custom_project_id: p.code || '',
        parent_project: p.parentId || '',
        status: p.status || '',
        company: p.company || '',
        percent_complete: p.progress || 0,
        expected_start_date: p.startDate || null,
        expected_end_date: p.endDate || null,
        customer: p.client || '',
        project_type: p.type || '',
        estimated_costing: p.budget || 0,
        owner: p.pm || '',
        is_group: p.parentId ? 0 : 1,
      }))
    }

    if (doctype === 'Company') {
      return store.companies.map((c) => ({
        name: c.id,
        abbr: c.abbr || '',
      }))
    }

    if (doctype === 'Work Package') {
      return store.workPackages.map((wp) => ({
        name: wp.id,
        code: wp.code || '',
        work_package_name: wp.name || '',
        project: wp.projectId || '',
        status: wp.status || '',
        budget: wp.budget || 0,
        progress: wp.progress || 0,
        start_date: wp.startDate || null,
        end_date: wp.endDate || null,
        owner_user: wp.owner || '',
      }))
    }

    if (doctype === 'Task') {
      return store.tasks.map((task) => ({
        name: task.id,
        subject: task.name || '',
        project: task.projectId || '',
        work_package: task.workPackageId || '',
        status: task.status || 'Open',
        priority: task.priority || 'Medium',
        progress: task.progress || 0,
        owner: task.assignee || '',
        exp_start_date: task.startDate || null,
        exp_end_date: task.endDate || null,
        task_type: task.task_type || 'Activity',
        activity_type: task.activityType || null,
        description: task.description || '',
      }))
    }

    if (doctype === 'Task Progress Entry') {
      return store.taskProgressEntries.map((e) => ({
        name: e.id,
        task: e.taskId,
        entry_date: e.entryDate,
        owner: e.enteredBy,
        progress_pct: e.progressPct,
        skilled_labour: e.skilledLabour,
        unskilled_labour: e.unskilledLabour,
        narrative: e.narrative,
        weather: e.weather,
        blocker_flag: e.blockerFlag ? 1 : 0,
        blocker_note: e.blockerNote,
      }))
    }

    if (doctype === 'Attachment') {
      return store.attachments.map((a) => ({
        name: a.id,
        parent_doctype: a.parentDoctype,
        parent_name: a.parentId,
        file_name: a.fileName,
        file_url: a.url,
        file_size: a.size,
        owner: a.uploadedBy,
      }))
    }

    if (doctype === 'Stage Planning') {
      return store.stagePlannings.map((sp) => ({
        name: sp.id,
        stage_name: sp.stageName,
        project: sp.project,
        planned_start: sp.plannedStart || null,
        planned_end: sp.plannedEnd || null,
        planned_task_count: sp.plannedTaskCount || 0,
        planned_completion_pct: sp.plannedCompletionPct || 0,
        description: sp.description || '',
        dependencies: (sp.dependencies || []).map((stageId) => ({ stage: stageId })),
        stage_planning_tasks: (sp.stagePlanningTasks || []).map((row) => ({
          name: row.id,
          task: row.task,
          planned_start: row.plannedStart || null,
          planned_end: row.plannedEnd || null,
          planned_qty: row.plannedQty ?? 100,
          qty_unit: row.qtyUnit || '%',
        })),
      }))
    }

    return []
  }

  function matchesFilterValue(actual, operator, expected) {
    if (operator === '=') return actual === expected
    if (operator === 'like') {
      const needle = String(expected || '').replaceAll('%', '').toLowerCase()
      return String(actual || '').toLowerCase().includes(needle)
    }
    if (operator === 'in') {
      const candidates = Array.isArray(expected) ? expected : []
      return candidates.includes(actual)
    }
    return true
  }

  function applyFilters(rows, filters = []) {
    if (!filters || (Array.isArray(filters) && !filters.length)) return rows

    if (!Array.isArray(filters) && typeof filters === 'object') {
      return rows.filter((row) => {
        return Object.entries(filters).every(([fieldname, condition]) => {
          const actual = row?.[fieldname]
          if (Array.isArray(condition)) {
            const [operator = '=', expected] = condition
            return matchesFilterValue(actual, operator, expected)
          }
          return actual === condition
        })
      })
    }

    return rows.filter((row) => {
      return filters.every((f) => {
        const [fieldname, operator = '=', value] = f || []
        const actual = row?.[fieldname]
        return matchesFilterValue(actual, operator, value)
      })
    })
  }

  function applyOrFilters(rows, orFilters = []) {
    if (!orFilters || (Array.isArray(orFilters) && !orFilters.length)) return rows

    if (!Array.isArray(orFilters) && typeof orFilters === 'object') {
      return rows.filter((row) => {
        return Object.entries(orFilters).some(([fieldname, condition]) => {
          const actual = row?.[fieldname]
          if (Array.isArray(condition)) {
            const [operator = '=', expected] = condition
            return matchesFilterValue(actual, operator, expected)
          }
          return actual === condition
        })
      })
    }

    return rows.filter((row) => {
      return orFilters.some((f) => {
        const [fieldname, operator = '=', value] = f || []
        const actual = row?.[fieldname]
        return matchesFilterValue(actual, operator, value)
      })
    })
  }

  function applyOrder(rows, orderBy = '') {
    if (!orderBy) return rows
    const [field, direction = 'asc'] = orderBy.split(/\s+/)
    const sign = direction.toLowerCase() === 'desc' ? -1 : 1
    return [...rows].sort((a, b) => {
      const av = a?.[field]
      const bv = b?.[field]
      if (av === bv) return 0
      if (av == null) return 1
      if (bv == null) return -1
      return String(av).localeCompare(String(bv), undefined, { numeric: true }) * sign
    })
  }

  function unsupported(action) {
    throw new Error(`Local adapter does not support ${action} for this DocType.`)
  }

  function list(doctype, options = {}) {
    const data = computed(() => {
      let rows = toDocTypeRows(doctype)
      rows = applyFilters(rows, options.filters)
      rows = applyOrFilters(rows, options.orFilters)
      rows = applyOrder(rows, options.orderBy)
      const start = options.start || 0
      const pageLength = options.pageLength ?? rows.length
      rows = rows.slice(start, start + pageLength)
      return options.transform ? options.transform(rows) : rows
    })

    return reactive({
      data,
      loading: false,
      error: null,
      fetch: () => null,
      reload: () => null,
    })
  }

  function read(doctype, name, options = {}) {
    const resolvedName = unref(name)

    return list(doctype, {
      ...options,
      filters: [[options.nameField || 'name', '=', resolvedName]],
      pageLength: 1,
      transform(rows) {
        const data = options.transform ? options.transform(rows) : rows
        return Array.isArray(data) ? (data[0] || null) : data
      },
    })
  }

  function linkSearch(doctype, options = {}) {
    const labelField = options.labelField || 'name'
    const valueField = options.valueField || 'name'
    const searchFields = Array.from(new Set(options.searchFields || [labelField, valueField, 'name']))
    const term = (options.query || '').trim()

    return list(doctype, {
      filters: options.filters,
      orFilters: term
        ? searchFields.map((fieldname) => [fieldname, 'like', `%${term}%`])
        : [],
      orderBy: options.orderBy || `${labelField} asc`,
      pageLength: options.pageLength ?? 10,
      transform(rows) {
        const mapped = rows.map((row) => ({
          label: row?.[labelField] || row?.[valueField] || row?.name || '',
          value: row?.[valueField] || row?.name || '',
          row,
        }))
        return options.transform ? options.transform(mapped) : mapped
      },
    })
  }

  async function create(doctype, values = {}) {
    if (doctype === 'Project') {
      const data = {
        name: values.project_name,
        code: values.custom_project_id,
        parentId: values.parent_project,
        status: values.status,
        company: values.company,
        progress: values.percent_complete,
        startDate: values.expected_start_date,
        endDate: values.expected_end_date,
        client: values.customer,
        type: values.project_type,
        budget: values.estimated_costing,
        pm: values.owner,
        seedDefaultStages: values.seedDefaultStages,
        seedDefaultWorkPackagesAndTasks: values.seedDefaultWorkPackagesAndTasks,
      }
      const record = store.addProject(data)
      return { ...record, name: record.id }
    }

    if (doctype === 'Work Package') {
      const data = {
        projectId: values.project,
        code: values.code,
        name: values.work_package_name,
        description: values.description,
        status: values.status,
        budget: values.budget,
        startDate: values.start_date,
        endDate: values.end_date,
        owner: values.owner_user,
      }
      const record = store.addWorkPackage(data)
      return { ...record, name: record.id }
    }

    if (doctype === 'Task') {
      const data = {
        projectId: values.project,
        workPackageId: values.work_package,
        task_type: values.task_type || 'Activity',
        activityType: values.activity_type,
        name: values.subject,
        description: values.description,
        status: values.status,
        priority: values.priority,
        assignee: values.owner,
        startDate: values.exp_start_date,
        endDate: values.exp_end_date,
      }
      const record = store.addTask(data)
      return { ...record, name: record.id }
    }

    if (doctype === 'Task Progress Entry') {
      const data = {
        taskId: values.task,
        entryDate: values.entry_date,
        enteredBy: values.owner,
        progressPct: values.progress_pct,
        skilledLabour: values.skilled_labour,
        unskilledLabour: values.unskilled_labour,
        narrative: values.narrative,
        weather: values.weather,
        blockerFlag: !!values.blocker_flag,
        blockerNote: values.blocker_note,
      }
      const record = store.addTaskProgressEntry(data)
      return { ...record, name: record.id }
    }

    if (doctype === 'Attachment') {
      const data = {
        parentDoctype: values.parent_doctype,
        parentId: values.parent_name,
        fileName: values.file_name,
        url: values.file_url,
        size: values.file_size,
        uploadedBy: values.owner,
      }
      const record = store.addAttachment(data)
      return { ...record, name: record.id }
    }

    return unsupported(`create on ${doctype}`)
  }

  async function update(doctype, name, values = {}) {
    if (doctype === 'Project') {
      const patch = {}
      if (values.project_name !== undefined) patch.name = values.project_name
      if (values.custom_project_id !== undefined) patch.code = values.custom_project_id
      if (values.status !== undefined) patch.status = values.status
      if (values.percent_complete !== undefined) patch.progress = values.percent_complete
      if (values.expected_start_date !== undefined) patch.startDate = values.expected_start_date
      if (values.expected_end_date !== undefined) patch.endDate = values.expected_end_date
      if (values.customer !== undefined) patch.client = values.customer
      if (values.project_type !== undefined) patch.type = values.project_type
      if (values.estimated_costing !== undefined) patch.budget = values.estimated_costing
      if (values.owner !== undefined) patch.pm = values.owner

      const record = store.updateProject(name, patch)
      return { ...record, name: record.id }
    }

    if (doctype === 'Work Package') {
      const patch = {}
      if (values.work_package_name !== undefined) patch.name = values.work_package_name
      if (values.code !== undefined) patch.code = values.code
      if (values.description !== undefined) patch.description = values.description
      if (values.status !== undefined) patch.status = values.status
      if (values.budget !== undefined) patch.budget = values.budget
      if (values.start_date !== undefined) patch.startDate = values.start_date
      if (values.end_date !== undefined) patch.endDate = values.end_date
      if (values.owner_user !== undefined) patch.owner = values.owner_user

      const record = store.updateWorkPackage(name, patch)
      return { ...record, name: record.id }
    }

    if (doctype === 'Task') {
      const patch = {}
      if (values.subject !== undefined) patch.name = values.subject
      if (values.status !== undefined) patch.status = values.status
      if (values.priority !== undefined) patch.priority = values.priority
      if (values.task_type !== undefined) patch.task_type = values.task_type
      if (values.owner !== undefined) patch.assignee = values.owner
      if (values.exp_start_date !== undefined) patch.startDate = values.exp_start_date
      if (values.exp_end_date !== undefined) patch.endDate = values.exp_end_date
      if (values.description !== undefined) patch.description = values.description

      const record = store.updateTask(name, patch)
      return { ...record, name: record.id }
    }

    if (doctype === 'Task Progress Entry') {
      const patch = {}
      if (values.entry_date !== undefined) patch.entryDate = values.entry_date
      if (values.owner !== undefined) patch.enteredBy = values.owner
      if (values.progress_pct !== undefined) patch.progressPct = values.progress_pct
      if (values.skilled_labour !== undefined) patch.skilledLabour = values.skilled_labour
      if (values.unskilled_labour !== undefined) patch.unskilledLabour = values.unskilled_labour
      if (values.narrative !== undefined) patch.narrative = values.narrative
      if (values.weather !== undefined) patch.weather = values.weather
      if (values.blocker_flag !== undefined) patch.blockerFlag = !!values.blocker_flag
      if (values.blocker_note !== undefined) patch.blockerNote = values.blocker_note

      const record = store.updateTaskProgressEntry(name, patch)
      return { ...record, name: record.id }
    }

    return unsupported(`update on ${doctype}`)
  }

  async function remove(doctype, name) {
    if (doctype === 'Project') {
      store.deleteProject(name)
      return { ok: true }
    }

    if (doctype === 'Work Package') {
      store.deleteWorkPackage(name)
      return { ok: true }
    }

    if (doctype === 'Task') {
      store.deleteTask(name)
      return { ok: true }
    }

    if (doctype === 'Task Progress Entry') {
      store.deleteTaskProgressEntry(name)
      return { ok: true }
    }

    if (doctype === 'Attachment') {
      store.deleteAttachment(name)
      return { ok: true }
    }

    return unsupported(`remove on ${doctype}`)
  }

  return {
    list,
    read,
    linkSearch,
    create,
    update,
    remove,

    getRootProjects() {
      return list('Project', {
        filters: [['is_group', '=', 1]],
        transform(projects) {
          return projects.map((p) => ({
            id: p.name,
            code: p.custom_project_id || '',
            name: p.project_name || p.name,
            client: p.customer || '',
            status: p.status || '',
            type: p.project_type || '',
            company: p.company || '',
            startDate: p.expected_start_date || null,
            endDate: p.expected_end_date || null,
            budget: p.estimated_costing || 0,
            progress: p.percent_complete || 0,
            pm: p.owner || '',
            parentId: null,
          }))
        },
      })
    },

    getCompanies() {
      return list('Company', {
        orderBy: 'name asc',
        transform(companies) {
          return companies.map((c) => ({
            id: c.name,
            name: c.name,
            abbr: c.abbr || '',
          }))
        },
      })
    },
  }
}
