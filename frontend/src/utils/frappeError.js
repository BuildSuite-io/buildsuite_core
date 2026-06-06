/**
 * Utilities for parsing Frappe HTTP error responses into user-friendly
 * messages and per-field error objects.
 *
 * Frappe error response shape (HTTP 417 / 409 / 500):
 *   {
 *     exc_type: "MandatoryError",
 *     exc: "...Traceback...\nfrappe.exceptions.MandatoryError: [Project, X]: company\nfield2",
 *     _server_messages: "[{\"message\": \"...\"}]"   ← double-encoded JSON
 *   }
 */

// Human-readable labels for common Frappe field names. Falls back to
// Title-Cased snake_case for anything not listed.
const FIELD_LABELS = {
  company:            'Company',
  project_name:       'Project Name',
  custom_project_id:  'Project ID',
  customer:           'Client',
  project_type:       'Project Type',
  expected_start_date:'Start Date',
  expected_end_date:  'End Date',
  estimated_costing:  'Budget',
  owner:              'Project Manager',
  task:               'Task',
  entry_date:         'Entry Date',
  cumulative_progress:'Progress',
  work_package:       'Work Package',
  work_package_name:  'Work Package Name',
  subject:            'Task Name',
  status:             'Status',
}

function fieldLabel(name) {
  return FIELD_LABELS[name]
    ?? name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/**
 * Frappe encodes _server_messages as a JSON string whose elements are
 * themselves JSON strings or objects. Unwrap both layers safely.
 */
function parseServerMessages(raw) {
  if (!raw) return []
  try {
    const arr = typeof raw === 'string' ? JSON.parse(raw) : (Array.isArray(raw) ? raw : [])
    return arr.map((item) => {
      if (typeof item === 'string') {
        try {
          const inner = JSON.parse(item)
          return typeof inner === 'object' ? (inner.message ?? '') : String(inner)
        } catch {
          return item
        }
      }
      return typeof item === 'object' ? (item.message ?? '') : String(item)
    }).filter(Boolean)
  } catch {
    return []
  }
}

/**
 * Parse a Frappe error (the rejected value from adapter calls) into:
 *   summary     – one-line human message suitable for a toast
 *   fieldErrors – { backendFieldName: "Field is required" } for field highlights
 *
 * Returns { summary: null, fieldErrors: {} } when nothing can be extracted.
 */
export function parseFrappeError(err) {
  if (!err) return { summary: null, fieldErrors: {} }

  const excType  = err.exc_type ?? ''
  const exc      = typeof err.exc === 'string' ? err.exc : ''
  // frappe-ui pre-parses _server_messages into err.messages (string[]).
  // Check that first; fall back to the raw _server_messages path for
  // non-frappe-ui callers that still carry the double-encoded JSON string.
  const messages = (Array.isArray(err.messages) && err.messages.length)
    ? err.messages
    : parseServerMessages(err._server_messages)

  const fieldErrors = {}

  if (excType === 'MandatoryError' || exc.includes('MandatoryError')) {
    // Extract field names from the traceback tail:
    //   MandatoryError: [DocType, Name]: field1\nfield2
    const tbMatch = exc.match(/MandatoryError:\s*\[.*?\]:\s*([\s\S]+)$/)
    if (tbMatch) {
      tbMatch[1].trim().split(/[\n,]+/).map((f) => f.trim()).filter(Boolean)
        .forEach((f) => { fieldErrors[f] = `${fieldLabel(f)} is required` })
    }

    // Also scan _server_messages for the same [DocType, Name]: field pattern
    for (const msg of messages) {
      const msgMatch = msg.match(/^\[.*?\]:\s*([\s\S]+)$/)
      if (msgMatch) {
        msgMatch[1].trim().split(/[\n,]+/).map((f) => f.trim()).filter(Boolean)
          .forEach((f) => { fieldErrors[f] ??= `${fieldLabel(f)} is required` })
      }
    }

    const labels = [...new Set(Object.values(fieldErrors).map((e) => e.replace(' is required', '')))]
    return {
      summary: labels.length
        ? `Required: ${labels.join(', ')}`
        : 'Some required fields are missing',
      fieldErrors,
    }
  }

  // For any other error type use the first server message, then err.message.
  return {
    summary: messages[0] ?? err.message ?? 'An unexpected error occurred',
    fieldErrors: {},
  }
}
