<script setup>
import { computed, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import LogoIcon from '@/components/LogoIcon.vue'
import RoleSwitcher from '@/components/RoleSwitcher.vue'
import CompanySwitcher from '@/components/CompanySwitcher.vue'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const route = useRoute()
const store = useDataStore()
const searchOpen = ref(false)
// Mobile sidebar drawer state. The sidebar is always visible on lg+ and
// collapses to a slide-in drawer below that breakpoint.
const sidebarOpen = ref(false)
function closeSidebar() { sidebarOpen.value = false }
function toggleTheme() { store.toggleTheme() }

// Per-workspace UI metadata (label, route path, icon, group). The visibility matrix
// and per-role ordering live in src/data/roles.js (CLAUDE.md §12.2, §12.3) — this
// table is the UI-side mapping from slug → presentation.
const WORKSPACES = {
  'site-execution':  { name: 'Site Execution',  to: '/app/site-execution',  icon: '🏗️', group: 'buildsuite' },
  'estimation':      { name: 'Estimation',      to: '/app/estimation',      icon: '📐', group: 'buildsuite' },
  'procurement':     { name: 'Procurement',     to: '/app/procurement',     icon: '🛒', group: 'buildsuite' },
  'subcontract':     { name: 'Subcontract',     to: '/app/subcontract',     icon: '🤝', group: 'buildsuite' },
  'workforce':       { name: 'Workforce',       to: '/app/workforce',       icon: '👷', group: 'buildsuite' },
  // 'scope-change' removed Session 33 — merged into Site Execution. The
  // /app/scope-change route stays registered as a legacy redirect target but
  // doesn't appear in the sidebar anymore.
  'project-finance': { name: 'Project Finance', to: '/app/project-finance', icon: '💵', group: 'buildsuite' },
  'accounting':      { name: 'Accounting',      to: '/app/accounting',      icon: '📊', group: 'erpnext' },
  'buying':          { name: 'Buying',          to: '/app/buying',          icon: '📥', group: 'erpnext' },
  'stock':           { name: 'Stock',           to: '/app/stock',           icon: '📦', group: 'erpnext' },
  'assets':          { name: 'Assets',          to: '/app/assets',          icon: '🏭', group: 'erpnext' },
  'hr':              { name: 'HR',              to: '/app/hr',              icon: '👤', group: 'erpnext' },
}

// Access-level hint pills (CLAUDE.md §12.3). Shown next to a workspace link when
// the active role has restricted access (anything other than 'full').
const ACCESS_HINTS = {
  'read':         { label: 'R',  title: 'Read-only access' },
  'approve':      { label: 'A',  title: 'Approve-only access' },
  'create-own':   { label: 'C',  title: 'Create own work only' },
  'self-service': { label: 'SS', title: 'Self-service only' },
  'team-only':    { label: 'T',  title: 'Team-only (direct reports)' },
  'pay-only':     { label: 'P',  title: 'Pay-only view' },
  'mr-only':      { label: 'MR', title: 'Material-request raise only' },
}

// Sidebar groups for the active role.
// Home is synthesized as the first BuildSuite item and Site Execution is pinned
// second when visible because it is the highest-frequency workspace.
const navGroups = computed(() => {
  const HOME_ITEM = { slug: 'home', name: 'Home', to: '/app/home', group: 'buildsuite', hint: null }
  const buildsuiteItems = [HOME_ITEM]
  const erpnextItems = []
  const otherBuildsuiteItems = []
  for (const slug of store.visibleWorkspaces) {
    if (slug === 'site-execution') continue
    const meta = WORKSPACES[slug]
    if (!meta) continue
    const access = store.workspaceAccess(slug)
    const hint = access && access !== 'full' ? ACCESS_HINTS[access] : null
    const item = { slug, ...meta, hint }
    if (meta.group === 'buildsuite') otherBuildsuiteItems.push(item)
    else erpnextItems.push(item)
  }

  if (store.visibleWorkspaces.includes('site-execution')) {
    const meta = WORKSPACES['site-execution']
    if (meta) {
      const access = store.workspaceAccess('site-execution')
      const hint = access && access !== 'full' ? ACCESS_HINTS[access] : null
      buildsuiteItems.push({ slug: 'site-execution', ...meta, hint })
    }
  }
  buildsuiteItems.push(...otherBuildsuiteItems)

  const groups = []
  if (buildsuiteItems.length) {
    groups.push({ key: 'buildsuite', title: 'BuildSuite', muted: false, topSeparator: false, items: buildsuiteItems })
  }
  if (erpnextItems.length) {
    groups.push({
      key: 'erpnext',
      title: 'ERPNext',
      muted: true,
      // Only render the top-border separator when there's a BuildSuite group above it;
      // otherwise it looks like an orphan rule at the top of the nav.
      topSeparator: groups.length > 0,
      items: erpnextItems,
    })
  }
  return groups
})

// Topbar breadcrumb removed; each view already renders richer page breadcrumbs.
</script>

<template>
  <div class="min-h-screen flex bg-white">
    <!-- Mobile backdrop. Only visible when the drawer is open. -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-ink-900/40 z-40 lg:hidden"
      @click="closeSidebar"
    ></div>

    <!-- Sidebar — sticky on lg+; slide-in drawer below that breakpoint. -->
    <aside
      class="w-60 bg-white border-r border-ink-200 flex flex-col flex-shrink-0 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 fixed inset-y-0 left-0 z-50 transform transition-transform duration-200"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'"
    >
      <div class="h-14 px-3 border-b border-ink-200 flex items-center gap-2">
        <RouterLink to="/" class="flex items-center gap-2 group" title="Back to workspaces">
          <LogoIcon :size="26" />
          <span class="font-semibold text-ink-900 text-sm">BuildSuite</span>
        </RouterLink>
        <span class="ml-auto text-[10px] font-medium px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded">Core</span>
      </div>

      <div class="px-3 py-2">
        <button @click="searchOpen = true" class="w-full px-2.5 py-1.5 text-xs bg-ink-50 text-ink-600 rounded flex items-center gap-2 hover:bg-ink-100">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          Search or jump to...
          <span class="ml-auto text-[10px] text-ink-400 font-mono bg-white px-1.5 py-0.5 rounded border border-ink-200">⌘K</span>
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto scrollbar-thin px-3 pb-4">
        <div v-for="group in navGroups" :key="group.key" class="mb-1" :class="group.topSeparator ? 'mt-4 pt-3 border-t border-ink-100' : 'mt-2'">
          <div class="px-2 py-1.5">
            <div
              class="font-semibold uppercase tracking-wider"
              :class="group.muted ? 'text-[10px] text-ink-400' : 'text-[11px] text-ink-500'"
            >{{ group.title }}</div>
            <div
              v-if="group.caption"
              class="text-[9px] text-ink-400 font-normal normal-case tracking-normal mt-0.5"
            >{{ group.caption }}</div>
          </div>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="desk-nav-link flex items-center gap-2.5 px-2 py-1.5 rounded hover:bg-ink-50"
            :class="group.muted ? 'text-sm text-ink-500' : 'text-sm text-ink-700'"
            active-class="active"
            @click="closeSidebar"
          >
            <span
              class="desk-icon w-5 h-5 flex items-center justify-center leading-none flex-shrink-0"
              :class="group.muted ? 'text-ink-300' : 'text-ink-400'"
            >
              <svg
                class="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.75"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
                v-html="getWorkspaceIconPath(item.slug)"
              />
            </span>
            <span class="flex-1 truncate">{{ item.name }}</span>
            <span
              v-if="item.hint"
              :title="item.hint.title"
              class="text-[9px] font-medium text-ink-400 border border-ink-200 rounded px-1 leading-4 flex-shrink-0"
            >{{ item.hint.label }}</span>
          </RouterLink>
        </div>

      </nav>

      <div class="border-t border-ink-200 p-3">
        <RouterLink to="/app/settings" class="flex items-center gap-2 px-2 py-1 text-xs text-ink-500 hover:text-ink-900">
          <svg
            class="w-3.5 h-3.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
            v-html="getWorkspaceIconPath('settings')"
          />
          Settings
        </RouterLink>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex-1 flex flex-col min-w-0">
      <header class="h-12 bg-white border-b border-ink-200 px-3 sm:px-5 flex items-center sticky top-0 z-20 gap-2">
        <!-- Hamburger — opens the sidebar drawer on mobile -->
        <button
          type="button"
          class="lg:hidden p-1.5 text-ink-600 hover:text-ink-900 hover:bg-ink-50 rounded"
          aria-label="Open menu"
          @click="sidebarOpen = true"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
        <div class="ml-auto flex items-center gap-1 sm:gap-2">
          <!-- Theme toggle — sun in dark mode, moon in light mode -->
          <button
            type="button"
            class="text-ink-500 hover:text-ink-900 hover:bg-ink-50 p-1.5 rounded"
            :aria-label="store.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
            :title="store.theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'"
            @click="toggleTheme"
          >
            <svg v-if="store.theme === 'dark'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
          </button>
          <button class="text-ink-400 hover:text-ink-700 p-1.5 hidden sm:inline-flex">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>
          </button>
          <button class="text-ink-400 hover:text-ink-700 p-1.5 hidden sm:inline-flex">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </button>
          <!-- Settings (Session 32) — Frappe-standard topbar placement (gear icon
               near the user / role chip). Active state when on a /app/settings/* route. -->
          <RouterLink
            to="/app/settings"
            class="p-1.5 rounded-md"
            :class="route.path.startsWith('/app/settings') ? 'text-brand-700 bg-brand-50' : 'text-ink-400 hover:text-ink-700'"
            title="Settings"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          </RouterLink>
          <CompanySwitcher />
          <RoleSwitcher />
        </div>
      </header>

      <main class="flex-1 min-h-0">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- Search palette -->
    <div v-if="searchOpen" class="fixed inset-0 bg-ink-900/40 z-50 flex items-start justify-center pt-20" @click="searchOpen = false">
      <div class="bg-white rounded-lg shadow-fp-lg w-full max-w-lg border border-ink-200" @click.stop>
        <div class="p-3 border-b border-ink-200">
          <input autofocus placeholder="Type to search projects, tasks, work packages..." class="w-full px-3 py-2 text-sm focus:outline-none" />
        </div>
        <div class="p-3 text-xs text-ink-500">
          Quick search across all data · ESC to close
        </div>
      </div>
    </div>
  </div>
</template>
