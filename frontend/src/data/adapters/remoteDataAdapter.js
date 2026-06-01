import { useDocTypeList } from '@/composables/useDocTypeList'

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
  return {
    getRootProjects() {
      return useDocTypeList('Project', {
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
        filters: [['is_group', '=', 0]],
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
      return useDocTypeList('Company', {
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
