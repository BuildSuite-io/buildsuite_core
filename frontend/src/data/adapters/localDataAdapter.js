import { reactive, computed } from 'vue'

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
    return list(doctype, {
      ...options,
      filters: [[options.nameField || 'name', '=', name]],
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

  async function create(doctype, _values = {}) {
    return unsupported(`create on ${doctype}`)
  }

  async function update(doctype, _name, _values = {}) {
    return unsupported(`update on ${doctype}`)
  }

  async function remove(doctype, _name) {
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
