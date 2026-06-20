/**
 * Minimal app-level toast notifications.
 *
 * Usage:
 *   import { showToast } from '@/utils/appToast'
 *   showToast('Project saved')           // success (default)
 *   showToast('Failed to save', 'error')
 *
 * The reactive `toasts` array is consumed by the AppToastContainer rendered
 * in App.vue. Each entry is auto-removed after `duration` ms.
 */
import { ref } from "vue";

export const toasts = ref([]);
let _id = 0;

/**
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} [type='success']
 * @param {number} [duration=4000] ms before auto-dismiss
 */
export function showToast(message, type = "success", duration = 4000) {
	const id = _id++;
	toasts.value.push({ id, message, type });
	setTimeout(() => {
		toasts.value = toasts.value.filter((t) => t.id !== id);
	}, duration);
}
