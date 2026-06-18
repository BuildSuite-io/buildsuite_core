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
import { getSessionUser } from '@/utils/session'

// An 'own'-scope persona (Site Engineer / Foreman) may only edit or delete the
// records it created. We resolve the creator from the record's Frappe `owner`
// (kept on the detail read transforms). This mirrors the backend own-record
// gate, so the button only shows when the save/delete would actually succeed —
// fixes the "error after edit + save" UX for tasks a user didn't create.
function ownsRecord(record) {
  if (!record) return false
  const uid = getSessionUser()
  return record.owner === uid || record.createdBy === uid
}

export function usePermissions() {
  const store = useDataStore()
  const caps = computed(() => PERSONA_CAPS[store.role] || null)

  function cap(doctype, action) {
    return caps.value?.[doctype]?.[action] ?? false
  }

  // Record-aware gates: `true` cap → always; `false` → never; `'own'` → only when
  // the current user created the record. Prefer these on detail-page buttons.
  function canEditRecord(doctype, record) {
    const c = cap(doctype, 'e')
    if (c === true) return true
    if (c === 'own') return ownsRecord(record)
    return false
  }
  function canDeleteRecord(doctype, record) {
    const c = cap(doctype, 'd')
    if (c === true) return true
    if (c === 'own') return ownsRecord(record)
    return false
  }

  return {
    // Create is an unconditional persona capability (no record context).
    canCreate: (doctype) => cap(doctype, 'c') === true,
    canRead: (doctype) => cap(doctype, 'r') !== false,
    // Coarse (no record) — true for full + own-scope personas. Use for
    // list-level affordances; prefer the record-aware variants on detail pages.
    canEdit: (doctype) => cap(doctype, 'e') !== false,
    canDelete: (doctype) => cap(doctype, 'd') !== false,
    // Precise (record in hand) — own-scope resolves against the creator.
    canEditRecord,
    canDeleteRecord,
  }
}
