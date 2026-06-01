<script setup>
// Role-aware landing dispatcher. The root route `/` lives outside DeskShell.
// HomeView itself renders nothing visible — it just picks the right landing
// component for the active role. Each landing wraps its own body in LandingShell.
//
// If the active role somehow has no mapped landing (defensive — all 11 should
// be covered), we fall through to a minimal generic tile grid of the role's
// visible workspaces, which is the pre-§12 HomeView behavior kept as a safety net.
//
// Landings are imported EAGERLY (not via defineAsyncComponent) so role switches
// are synchronous. The earlier lazy-loaded version caused a blank flash on first
// switch to a role whose chunk hadn't been fetched yet — Vue's <component :is>
// unmounted the old landing, then waited for the new chunk to download before
// rendering. All 11 landings together are ~60 kB unzipped / ~20 kB gzipped —
// smaller than the cost of one network round-trip, so lazy loading was the wrong
// trade-off. Eager import bundles them into the HomeView chunk and role swaps
// become instant.

import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import LandingShell from '@/layouts/LandingShell.vue'
import DirectorLanding from '@/views/landings/DirectorLanding.vue'
import PMLanding from '@/views/landings/PMLanding.vue'
import EstimatorLanding from '@/views/landings/EstimatorLanding.vue'
import QSLanding from '@/views/landings/QSLanding.vue'
import SiteEngineerLanding from '@/views/landings/SiteEngineerLanding.vue'
import ForemanLanding from '@/views/landings/ForemanLanding.vue'
import ProcurementLanding from '@/views/landings/ProcurementLanding.vue'
import StoreKeeperLanding from '@/views/landings/StoreKeeperLanding.vue'
import AccountantLanding from '@/views/landings/AccountantLanding.vue'
import HRManagerLanding from '@/views/landings/HRManagerLanding.vue'
import AdminLanding from '@/views/landings/AdminLanding.vue'

const store = useDataStore()

const LANDING_BY_ROLE = {
  director:        DirectorLanding,
  pm:              PMLanding,
  estimator:       EstimatorLanding,
  qs:              QSLanding,
  'site-engineer': SiteEngineerLanding,
  foreman:         ForemanLanding,
  procurement:     ProcurementLanding,
  'store-keeper':  StoreKeeperLanding,
  accountant:      AccountantLanding,
  'hr-manager':    HRManagerLanding,
  admin:           AdminLanding,
}

const landingComponent = computed(() => LANDING_BY_ROLE[store.role] || null)
const visibleWorkspaceTiles = computed(() =>
  store.visibleWorkspaces.map(slug => ({ slug, to: `/app/${slug}` }))
)
</script>

<template>
  <component :is="landingComponent" v-if="landingComponent" />

  <!-- Generic fallback (should never fire for the 11 mapped roles) -->
  <LandingShell v-else>
    <div class="max-w-4xl mx-auto px-6 py-12">
      <h1 class="text-2xl font-semibold text-ink-900 tracking-tight">Your workspaces</h1>
      <p class="text-sm text-ink-500 mt-1">No role-specific landing for "{{ store.role }}" — showing visible workspaces.</p>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mt-6">
        <RouterLink
          v-for="tile in visibleWorkspaceTiles"
          :key="tile.slug"
          :to="tile.to"
          class="bg-white border border-ink-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-fp-md transition-all text-sm font-medium text-ink-900"
        >{{ tile.slug }}</RouterLink>
      </div>
    </div>
  </LandingShell>
</template>
