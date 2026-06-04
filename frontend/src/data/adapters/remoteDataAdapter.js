import { useDocTypeList } from '@/composables/useDocTypeList'
import { unref } from 'vue'

/**
 * Remote adapter — reads from the live Frappe backend via frappe-ui resources.
 *
 * Each list method returns a createListResource result:
 *   { data, loading, error, reload(), fetch() }
 *
 * The transform function maps Frappe field names → the view's expected field
 * shape so consumers are adapter-agnostic (same fields in local and remote mode).
 * Standard Frappe permissions and user-permissions are enforced server-side.
 */
export function createRemoteDataAdapter() {
  function list(doctype, options = {}) {
    return useDocTypeList(doctype, {
      fields: options.fields ?? ['name'],
      filters: options.filters,
      orFilters: options.orFilters,
      orderBy: options.orderBy,
      start: options.start ?? 0,
      pageLength: options.pageLength ?? 20,
      cache: options.cache,
      auto: options.auto !== false,
      transform: options.transform,
    })
  }

  function read(doctype, name, options = {}) {
    const resolvedName = unref(name)

    return list(doctype, {
      fields: options.fields ?? ['name'],
      filters: [[options.nameField || 'name', '=', resolvedName]],
      pageLength: 1,
      cache: options.cache,
      auto: options.auto !== false,
      transform(rows) {
        const data = options.transform ? options.transform(rows) : rows
        return Array.isArray(data) ? (data[0] || null) : data
      },
    })
  }

  async function create(doctype, values = {}) {
    const resource = list(doctype, { fields: ['name'], auto: false })
    return resource.insert.submit(values)
  }

  async function update(doctype, name, values = {}) {
    const resource = list(doctype, { fields: ['name'], auto: false })
    return resource.setValue.submit({ name, ...values })
  }

  async function remove(doctype, name) {
    const resource = list(doctype, { fields: ['name'], auto: false })
    return resource.delete.submit(name)
  }

  function linkSearch(doctype, options = {}) {
    const labelField = options.labelField || 'name'
    const valueField = options.valueField || 'name'
    const searchFields = Array.from(new Set(options.searchFields || [labelField, valueField, 'name']))
    const term = (options.query || '').trim()

    return list(doctype, {
      fields: Array.from(new Set([valueField, labelField, ...searchFields])),
      filters: options.filters,
      orFilters: term
        ? searchFields.map((fieldname) => [fieldname, 'like', `%${term}%`])
        : [],
      orderBy: options.orderBy || `${labelField} asc`,
      pageLength: options.pageLength ?? 10,
      cache: options.cache,
      auto: options.auto !== false,
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

  return {
    list,
    read,
    create,
    update,
    remove,
    linkSearch,

    getRootProjects() {
      return list('Project', {
        fields: [
          'name',
          'project_name',
          'custom_project_id',
          'status',
          'company',
          'percent_complete',
          'expected_start_date',
          'expected_end_date',
          'customer',
          'project_type',
          'estimated_costing',
          'owner',
        ],
        filters: [['is_group', '=', 1]],
        orderBy: 'creation desc',
        pageLength: 100,
        cache: 'buildsuite-root-projects',
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
        fields: ['name', 'abbr'],
        orderBy: 'name asc',
        cache: 'buildsuite-companies',
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
