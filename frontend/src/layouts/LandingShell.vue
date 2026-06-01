<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import LogoIcon from '@/components/LogoIcon.vue'
import RoleSwitcher from '@/components/RoleSwitcher.vue'

const store = useDataStore()

// "Browse all workspaces" sends the user into the desk shell at their first
// visible workspace — guaranteed to be a page they have access to. Falls back
// to /app/dashboard for safety (e.g., during hydration before visibleWorkspaces
// is populated).
const skipLink = computed(() => {
  const first = store.visibleWorkspaces?.[0]
  return first ? `/app/${first}` : '/app/dashboard'
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-ink-50 to-white flex flex-col">
    <header class="h-14 bg-white/90 backdrop-blur border-b border-ink-200 flex items-center px-6 sticky top-0 z-30">
      <RouterLink to="/" class="flex items-center gap-2.5">
        <LogoIcon :size="28" />
        <span class="font-semibold text-ink-900">BuildSuite</span>
        <span class="ml-2 text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600 rounded font-medium tracking-wide">PROTOTYPE</span>
      </RouterLink>
      <div class="ml-auto flex items-center gap-4">
        <RouterLink
          :to="skipLink"
          class="text-xs text-ink-500 hover:text-ink-900 hidden sm:inline-flex items-center gap-1"
        >
          Browse all workspaces
          <span aria-hidden="true">→</span>
        </RouterLink>
        <RoleSwitcher />
      </div>
    </header>

    <main class="flex-1 min-w-0">
      <slot />
    </main>

    <footer class="border-t border-ink-200 bg-white py-4 text-center text-[11px] text-ink-400">
      BuildSuite Core · Open Source MIT · Frappe v16 prototype · Browser storage backend
    </footer>
  </div>
</template>
