import { reactive, computed } from 'vue'

/**
 * Local adapter — wraps existing Pinia store getters in the shared
 * { data, loading, error } resource envelope so the view layer is
 * adapter-agnostic. No network calls; loading is always false.
 */
export function createLocalDataAdapter(store) {
  return {
    getRootProjects() {
      return reactive({
        data: computed(() => store.rootProjects),
        loading: false,
        error: null,
      })
    },
    getCompanies() {
      return reactive({
        data: computed(() => store.companies),
        loading: false,
        error: null,
      })
    },
  }
}
