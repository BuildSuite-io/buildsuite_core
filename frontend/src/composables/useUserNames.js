// Shared directory of real Frappe users → full_name. UserAvatar (and any caller
// that has only a user id/email) uses this to render a human name, since the
// prototype `store.team` only knows demo users, not real backend Users.
//
// One cached resource is shared across every caller (frappe-ui dedupes by the
// cache key + the module-level singleton), so mounting many avatars triggers a
// single User list fetch.

import { computed } from 'vue'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'

let _resource = null

function rows(resource) {
  const raw = resource?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
}

export function useUserNames() {
  if (!_resource) {
    const adapter = createDataAdapter(useDataStore())
    _resource = adapter.list('User', {
      fields: ['name', 'full_name'],
      filters: [['enabled', '=', 1]],
      pageLength: 0, // every enabled user — the map must resolve any assignee
      cache: 'buildsuite-user-directory',
    })
  }

  const userNamesMap = computed(() => {
    const map = {}
    rows(_resource).forEach((u) => { map[u.name] = u.full_name || u.name })
    return map
  })

  // Returns the full_name when known, else the id itself (email) as a sensible
  // placeholder until the directory resolves.
  function userName(id) {
    if (!id) return ''
    return userNamesMap.value[id] || id
  }

  return { userName, userNamesMap }
}
