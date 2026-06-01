import { useDocTypeList } from '@/composables/useDocTypeList'

/**
 * Remote data adapter — reads from the live Frappe backend via frappe-ui resources.
 *
 * Each method returns a reactive createListResource result:
 *   { data, loading, error, reload(), fetch() }
 *
 * Callers must wait for .loading to be false before reading .data.
 * Standard Frappe permissions and user-permissions are enforced server-side.
 */
export function createRemoteDataAdapter() {
  return {
    /**
     * Generic list factory. Use this for any doctype not explicitly modelled below.
     * @param {string} doctype
     * @param {object} [options]  see useDocTypeList for option shape
     */
    createList(doctype, options) {
      return useDocTypeList(doctype, options)
    },

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
        ],
        filters: [['is_group', '=', 0]],
        orderBy: 'creation desc',
        cache: 'buildsuite-root-projects',
      })
    },

    getCompanies() {
      return useDocTypeList('Company', {
        fields: ['name', 'abbr'],
        orderBy: 'name asc',
        cache: 'buildsuite-companies',
      })
    },

    /**
     * Remote mode cannot determine multi-company synchronously.
     * Check companies.data.length after the companies resource loads.
     */
    isMultiCompany() {
      return null
    },

    /**
     * Remote mode cannot look up a company by id without a loaded list.
     * Use getCompanies() and filter .data client-side.
     */
    getCompanyById(_id) {
      return null
    },
  }
}
