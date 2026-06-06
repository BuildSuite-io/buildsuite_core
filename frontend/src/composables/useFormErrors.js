import { ref } from 'vue'
import { parseFrappeError } from '@/utils/frappeError'

/**
 * Manages form field errors for both client-side validation and server-side
 * Frappe error responses.
 *
 * Usage:
 *   const { errors, applyServerErrors, clearError, reset } = useFormErrors({
 *     company:      'company',   // backendFieldName: formFieldKey
 *     project_name: 'name',
 *   })
 *
 *   // In save():
 *   } catch (err) {
 *     const summary = applyServerErrors(err)
 *     showToast(summary ?? 'Failed to save', 'error')
 *   }
 *
 *   // In template — clear field error as soon as user fixes the value:
 *   @change="clearError('company')"
 *   @input="clearError('name')"
 */
export function useFormErrors(backendToFormField = {}) {
  const errors = ref({})

  /**
   * Parse a Frappe error response, map backend field names to form keys,
   * merge into errors, and return the human-readable summary string.
   */
  function applyServerErrors(err) {
    const { summary, fieldErrors } = parseFrappeError(err)
    const mapped = {}
    for (const [backendField, formField] of Object.entries(backendToFormField)) {
      if (fieldErrors[backendField]) mapped[formField] = fieldErrors[backendField]
    }
    if (Object.keys(mapped).length) {
      errors.value = { ...errors.value, ...mapped }
    }
    return summary ?? null
  }

  /** Replace errors wholesale — use from a client-side validate() function. */
  function setErrors(newErrors) {
    errors.value = newErrors ?? {}
  }

  /** Clear the error for one specific form field. */
  function clearError(key) {
    if (!errors.value[key]) return
    const next = { ...errors.value }
    delete next[key]
    errors.value = next
  }

  /** Reset all errors (e.g. on successful save or cancel). */
  function reset() {
    errors.value = {}
  }

  return { errors, applyServerErrors, setErrors, clearError, reset }
}
