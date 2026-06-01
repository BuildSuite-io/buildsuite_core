import { createListResource } from 'frappe-ui'

/**
 * Generic composable for a read-only Frappe DocType list.
 *
 * Wraps createListResource so that standard Frappe permissions, user-permissions,
 * and server-side filters are enforced by the backend automatically.
 * Never add a bespoke /api/method endpoint for standard list reads — use this.
 *
 * @param {string} doctype      Frappe DocType name, e.g. 'Project'
 * @param {object} [options]
 *   @param {string[]} [options.fields]      Fields to fetch (default: ['name'])
 *   @param {Array|Object} [options.filters] Frappe-style list filters
 *   @param {string} [options.orderBy]       e.g. 'creation desc'
 *   @param {number} [options.pageLength]    Page size (default: 20)
 *   @param {string|Array} [options.cache]   frappe-ui cache key
 *   @param {boolean} [options.auto]         Fetch immediately (default: true)
 *   @param {function} [options.transform]   Post-process the data array
 *
 * @returns {import('frappe-ui').ListResource} Reactive resource with
 *   .data, .loading, .error, .reload(), .fetch()
 */
export function useDocTypeList(doctype, options = {}) {
  const resourceConfig = {
    doctype,
    fields: options.fields ?? ['name'],
    orderBy: options.orderBy,
    pageLength: options.pageLength ?? 20,
    auto: options.auto !== false,
  }

  if (options.filters !== undefined) resourceConfig.filters = options.filters
  if (options.cache !== undefined) resourceConfig.cache = options.cache
  if (options.transform !== undefined) resourceConfig.transform = options.transform

  return createListResource(resourceConfig)
}
