// UI permission helper. Decides which create/edit/delete affordances to show
// for the active persona (store.role, set from the logged-in user on load).
// The backend (permissions/*.py) is the authoritative gate; this only hides
// buttons that would fail.
//
//   const { canCreate, canEdit, canDelete, canRead } = usePermissions()
//   v-if="canCreate('task')"   v-if="canEdit('stagePlanning')"
//
// Doctype keys: 'project' | 'workPackage' | 'task' | 'taskProgressEntry' | 'stagePlanning'.

import { computed } from 'vue'
import { useDataStore } from '@/stores'
import { PERSONA_CAPS } from '@/data/roles'

export function usePermissions() {
  const store = useDataStore()
  const caps = computed(() => PERSONA_CAPS[store.role] || null)

  function cap(doctype, action) {
    return caps.value?.[doctype]?.[action] ?? false
  }

  return {
    // Create is an unconditional persona capability (no record context).
    canCreate: (doctype) => cap(doctype, 'c') === true,
    canRead: (doctype) => cap(doctype, 'r') !== false,
    // Edit/Delete: show for full ('true') and own-scope ('own') personas; the
    // backend enforces the precise own-record rule. Hidden only for read-only.
    canEdit: (doctype) => cap(doctype, 'e') !== false,
    canDelete: (doctype) => cap(doctype, 'd') !== false,
  }
}
