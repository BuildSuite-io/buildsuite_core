import { createListResource } from 'frappe-ui-list-resource'
import { useDataStore } from '@/stores'
import { createLocalDataAdapter } from '@/data/adapters/localDataAdapter'

/**
 * Generic composable for a read-only Frappe DocType list.
 *
 * In 'remote' mode (default), it wraps createListResource so that standard
 * Frappe permissions, user-permissions, and server-side filters are enforced.
 * In 'local' mode (VITE_DATA_MODE=local), it uses the LocalDataAdapter which
 * mocks list reads against the Pinia store's seed data.
 *
 * @param {string} doctype      Frappe DocType name, e.g. 'Project'
 * @param {object} [options]
 *   @param {string[]} [options.fields]      Fields to fetch (default: ['name'])
 *   @param {Array|Object} [options.filters] Frappe-style list filters
 *   @param {Array|Object} [options.orFilters] Frappe-style OR filters
 *   @param {string} [options.orderBy]       e.g. 'creation desc'
 *   @param {number} [options.start]         Start offset for server pagination
 *   @param {number} [options.pageLength]    Page size (default: 20)
 *   @param {string|Array} [options.cache]   frappe-ui cache key
 *   @param {boolean} [options.auto]         Fetch immediately (default: true)
 *   @param {function} [options.transform]   Post-process the data array
 *
 * @returns {import('frappe-ui').ListResource} Reactive resource
 */
export function useDocTypeList(doctype, options = {}) {
  const mode = import.meta.env.VITE_DATA_MODE || 'remote'

  if (mode === 'local') {
    const store = useDataStore()
    const adapter = createLocalDataAdapter(store)
    return adapter.list(doctype, options)
  }

  const resourceConfig = {
    doctype,
    fields: options.fields ?? ['name'],
    orderBy: options.orderBy,
    start: options.start ?? 0,
    pageLength: options.pageLength ?? 20,
    auto: options.auto !== false,
  }

  if (options.filters !== undefined) resourceConfig.filters = options.filters
  if (options.orFilters !== undefined) resourceConfig.orFilters = options.orFilters
  if (options.cache !== undefined) resourceConfig.cache = options.cache
  if (options.transform !== undefined) resourceConfig.transform = options.transform

  return createListResource(resourceConfig)
}
