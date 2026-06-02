<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'

const store = useDataStore()

const now = new Date()
const todayISO = now.toISOString().slice(0, 10)

const greeting = computed(() => {
  const hour = now.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})

const userName = computed(() => store.user?.name || 'Admin User')

const roleLabel = computed(() => (store.isAdmin ? 'System Manager (Admin)' : (store.currentRole?.name || 'User')))

const dateLabel = computed(() =>
  new Intl.DateTimeFormat('en-GB', {
    weekday: 'long',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(now)
)

const initials = computed(() => {
  const name = userName.value || 'A D'
  const parts = name.split(' ').filter(Boolean)
  if (!parts.length) return 'AD'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase()
})

const activeProjectsCount = computed(() => store.activeProjectsCount || 0)
const openTasksCount = computed(() => store.openTasksCount || 0)
const usersCount = computed(() => {
  const ids = new Set((store.team || []).map((u) => u.id))
  if (store.user?.id) ids.add(store.user.id)
  return ids.size
})
const workspacesCount = computed(() => (store.visibleWorkspaces || []).length)

const pendingScosCount = computed(() => store.pendingScosCount || 0)
const overdueTasksCount = computed(() =>
  (store.tasks || []).filter((t) =>
    t.endDate && t.endDate < todayISO && t.status !== 'Completed' && t.status !== 'Cancelled'
  ).length
)
const progressTodayCount = computed(() =>
  (store.taskProgressEntries || []).filter((e) => e.entryDate === todayISO).length
)

const quickActions = [
  { label: 'Users', to: '/app/settings/users' },
  { label: 'Companies', to: '/app/settings/companies' },
  { label: 'Project Types', to: '/app/settings/project-types' },
  { label: 'Workspace Structure', to: '/app/settings/workspace-structure' },
  { label: 'All Projects', to: '/app/projects' },
  { label: 'Data Tools', to: '/app/settings/data' },
]

function showCount(value, fallback) {
  return Number.isFinite(value) ? value : fallback
}
</script>

<template>
  <div class="min-h-full bg-ink-50">
    <div class="max-w-6xl mx-auto px-6 py-8 space-y-6">
      <div class="bg-white border border-ink-200 p-6 sm:p-8" style="border-radius: 10px;">
        <div class="text-xs text-ink-500 font-semibold">{{ initials }}</div>

        <p class="text-sm text-ink-700">{{ greeting }},</p>
        <h1 class="text-3xl sm:text-4xl font-semibold text-ink-900 mt-1">{{ userName }}</h1>
        <p class="text-sm text-ink-500 mt-3">Here is a snapshot of system activity today.</p>

        <p class="text-xs text-ink-500 mt-6">
          {{ roleLabel }}·{{ dateLabel }}
        </p>
      </div>

      <section class="bg-white border border-ink-200 p-5 sm:p-6" style="border-radius: 10px;">
        <h2 class="text-lg font-semibold text-ink-900">Today's snapshot</h2>
        <div class="text-[11px] text-success-700 font-semibold mt-1">Live</div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="border border-ink-200 bg-ink-50 p-3" style="border-radius: 8px;">
            <div class="text-2xl font-semibold text-ink-900 tabular-nums">{{ showCount(activeProjectsCount, 4) }}</div>
            <div class="text-xs text-ink-600 mt-1">Active projects</div>
          </div>
          <div class="border border-ink-200 bg-ink-50 p-3" style="border-radius: 8px;">
            <div class="text-2xl font-semibold text-ink-900 tabular-nums">{{ showCount(openTasksCount, 9) }}</div>
            <div class="text-xs text-ink-600 mt-1">Open tasks</div>
          </div>
          <div class="border border-ink-200 bg-ink-50 p-3" style="border-radius: 8px;">
            <div class="text-2xl font-semibold text-ink-900 tabular-nums">{{ showCount(usersCount, 7) }}</div>
            <div class="text-xs text-ink-600 mt-1">Users</div>
          </div>
          <div class="border border-ink-200 bg-ink-50 p-3" style="border-radius: 8px;">
            <div class="text-2xl font-semibold text-ink-900 tabular-nums">{{ showCount(workspacesCount, 11) }}</div>
            <div class="text-xs text-ink-600 mt-1">Workspaces</div>
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <RouterLink to="/app/settings" class="border border-ink-200 bg-white p-4 hover:border-brand-400 transition-colors" style="border-radius: 8px;">
          <h3 class="text-base font-semibold text-ink-900">Settings</h3>
          <p class="text-xs text-ink-600 mt-1">Manage workspaces, users, project types, and data.</p>
          <div class="text-sm text-brand-700 font-medium mt-3">Open Settings→</div>
        </RouterLink>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <RouterLink to="/app/sco" class="border border-ink-200 bg-white p-4 hover:border-brand-400 transition-colors" style="border-radius: 8px;">
            <h3 class="text-sm font-semibold text-ink-900">Pending SCOs</h3>
            <p class="text-xs text-ink-600 mt-1 tabular-nums">{{ showCount(pendingScosCount, 2) }} awaiting approval</p>
            <div class="text-sm text-brand-700 font-medium mt-3">View →</div>
          </RouterLink>
          <RouterLink to="/app/tasks" class="border border-ink-200 bg-white p-4 hover:border-brand-400 transition-colors" style="border-radius: 8px;">
            <h3 class="text-sm font-semibold text-ink-900">Overdue tasks</h3>
            <p class="text-xs text-ink-600 mt-1 tabular-nums">{{ showCount(overdueTasksCount, 4) }} past their end date</p>
            <div class="text-sm text-brand-700 font-medium mt-3">View →</div>
          </RouterLink>
          <RouterLink to="/app/progress-entries" class="border border-ink-200 bg-white p-4 hover:border-brand-400 transition-colors" style="border-radius: 8px;">
            <h3 class="text-sm font-semibold text-ink-900">Progress today</h3>
            <p class="text-xs text-ink-600 mt-1">{{ progressTodayCount ? `${progressTodayCount} entries filed` : 'No entries filed yet' }}</p>
            <div class="text-sm text-brand-700 font-medium mt-3">View →</div>
          </RouterLink>
        </div>
      </section>

      <section class="bg-white border border-ink-200 p-5 sm:p-6" style="border-radius: 10px;">
        <h2 class="text-lg font-semibold text-ink-900 mb-4">Quick actions</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
          <RouterLink
            v-for="action in quickActions"
            :key="action.to"
            :to="action.to"
            class="border border-ink-200 bg-ink-50 hover:bg-white hover:border-brand-400 px-3 py-2.5 transition-colors flex items-center justify-between"
            style="border-radius: 8px;"
          >
            <span class="text-sm text-ink-900 font-medium">{{ action.label }}</span>
            <span class="text-ink-500">→</span>
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>
