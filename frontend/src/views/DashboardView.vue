<script setup>
// Admin working dashboard inside the Desk shell (CLAUDE.md §12.4). NOT the AdminLanding
// at `/` — that one is Vue-styled with the workspace launcher + greeting. This is the
// denser Desk-styled overview accessed via "Browse all workspaces" from a landing, or
// the legacy `/` redirect.

import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtCompactINR } from '@/utils/format'

const store = useDataStore()
const rootProjects = computed(() => store.rootProjects)
const pendingScos = computed(() => store.scos.filter(s => s.status === 'Pending Approval'))
const inProgressTasks = computed(() => store.tasks.filter(t => t.status === 'In Progress').slice(0, 6))

// Schedule-based progress-bar color, same convention as Projects list.
const today = new Date()
function progressBarColor(p) {
  if (!p.startDate || !p.endDate) return 'bg-success-500'
  const start = new Date(p.startDate).getTime()
  const end = new Date(p.endDate).getTime()
  const total = end - start
  if (total <= 0) return 'bg-success-500'
  const elapsed = Math.max(0, Math.min(total, today.getTime() - start))
  const expected = (elapsed / total) * 100
  if (expected <= 0) return 'bg-success-500'
  const v = ((expected - p.progress) / expected) * 100
  if (v > 15) return 'bg-danger-500'
  if (v > 5) return 'bg-warning-500'
  return 'bg-success-500'
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Dashboard' },
]
</script>

<template>
  <DeskPage title="Dashboard" subtitle="Operations overview · live from local storage" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/tasks/new" class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50" style="border-radius: 2px;">+ New Task</RouterLink>
      <RouterLink to="/projects/new" class="desk-save-btn">+ New Project</RouterLink>
    </template>

    <!-- KPI strip — Desk-tight, 4 cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Active projects</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ store.activeProjectsCount }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Open tasks</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ store.openTasksCount }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Pending SCOs</div>
        <div class="text-base font-semibold text-warning-700 mt-0.5">{{ store.pendingScosCount }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total order book</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">{{ fmtCompactINR(store.totalOrderBook) }}</div>
      </div>
    </div>

    <!-- Projects + side panels — Desk density, no shadows, sharp corners -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
      <!-- Active projects (span 2) -->
      <div class="lg:col-span-2 bg-white border border-ink-200 overflow-hidden" style="border-radius: 2px;">
        <div class="px-3 py-2 bg-ink-50 border-b border-ink-200 flex items-center justify-between">
          <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Active projects</h2>
          <DeskLink to="/projects" class="text-xs">See all →</DeskLink>
        </div>
        <div>
          <RouterLink
            v-for="(p, idx) in rootProjects"
            :key="p.id"
            :to="`/projects/${p.id}`"
            class="flex items-center gap-3 px-3 py-2 border-b border-ink-100 last:border-b-0 hover:bg-brand-50"
            :class="idx % 2 === 1 ? 'bg-[#FAFBFC]' : 'bg-white'"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm text-ink-900">{{ p.name }}</span>
                <StatusBadge :status="p.status" />
              </div>
              <div class="text-[11px] text-ink-500 mt-0.5">{{ p.client }} · {{ fmtCompactINR(p.budget) }}</div>
            </div>
            <div class="w-32 flex-shrink-0">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-1 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
                  <div class="h-full" :class="progressBarColor(p)" :style="`width:${p.progress}%`"></div>
                </div>
                <span class="text-[11px] text-ink-700 tabular-nums w-8 text-right">{{ p.progress }}%</span>
              </div>
            </div>
            <UserAvatar :user-id="p.pm" size="xs" />
          </RouterLink>
          <div v-if="!rootProjects.length" class="px-3 py-6 text-center text-xs text-ink-400">No projects yet.</div>
        </div>
      </div>

      <!-- Side panels -->
      <div class="space-y-3">
        <div class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 2px;">
          <div class="px-3 py-2 bg-ink-50 border-b border-ink-200">
            <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Pending SCOs</h2>
          </div>
          <div>
            <RouterLink
              v-for="(s, idx) in pendingScos"
              :key="s.id"
              to="/sco"
              class="block px-3 py-2 border-b border-ink-100 last:border-b-0 hover:bg-brand-50"
              :class="idx % 2 === 1 ? 'bg-[#FAFBFC]' : 'bg-white'"
            >
              <div class="text-xs text-ink-900 truncate">{{ s.title }}</div>
              <div class="text-[10px] text-ink-500 mt-0.5 font-mono">{{ s.id }} · {{ fmtCompactINR(s.impact) }}</div>
            </RouterLink>
            <div v-if="!pendingScos.length" class="px-3 py-5 text-center text-xs text-ink-400">No pending SCOs</div>
          </div>
        </div>

        <div class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 2px;">
          <div class="px-3 py-2 bg-ink-50 border-b border-ink-200">
            <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Tasks in progress</h2>
          </div>
          <div>
            <RouterLink
              v-for="(t, idx) in inProgressTasks"
              :key="t.id"
              :to="`/tasks/${t.id}`"
              class="block px-3 py-2 border-b border-ink-100 last:border-b-0 hover:bg-brand-50"
              :class="idx % 2 === 1 ? 'bg-[#FAFBFC]' : 'bg-white'"
            >
              <div class="text-xs text-ink-900 truncate">{{ t.name }}</div>
              <div class="flex items-center justify-between mt-1">
                <span class="text-[10px] text-ink-500 tabular-nums">{{ t.progress }}%</span>
                <UserAvatar :user-id="t.assignee" size="xs" />
              </div>
            </RouterLink>
            <div v-if="!inProgressTasks.length" class="px-3 py-5 text-center text-xs text-ink-400">No tasks in progress</div>
          </div>
        </div>
      </div>
    </div>
  </DeskPage>
</template>
