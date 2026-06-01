<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ROLES } from '@/data/roles'
import { useDataStore } from '@/stores'
import LandingShell from '@/layouts/LandingShell.vue'

const ROLE_ID = 'site-engineer'
const role = ROLES.find(r => r.id === ROLE_ID)
const store = useDataStore()

// Prototype assumption: when the active role is Site Engineer, treat USR-005 (Ravi Kumar)
// as "me" for filtering tasks / picking primary project. When the prototype gains real
// auth, this becomes store.user.id (and the site engineer's primary project is whatever
// they're actively logged into).
const SITE_ENGINEER_USER_ID = 'USR-005'

const today = new Date()
const todayLabel = today.toLocaleDateString('en-IN', { weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' })

const me = computed(() => store.teamMember(SITE_ENGINEER_USER_ID))
const firstName = computed(() => (me.value?.name || '').split(' ')[0] || 'there')

const myTasks = computed(() => store.tasks.filter(t => t.assignee === SITE_ENGINEER_USER_ID))

// Primary project = project with the most assigned tasks for this engineer.
const primaryProject = computed(() => {
  const counts = {}
  myTasks.value.forEach(t => { counts[t.projectId] = (counts[t.projectId] || 0) + 1 })
  let bestId = null, bestCount = 0
  for (const [pid, c] of Object.entries(counts)) {
    if (c > bestCount) { bestId = pid; bestCount = c }
  }
  return bestId ? store.projectById(bestId) : null
})

const inProgressCount = computed(() => myTasks.value.filter(t => t.status === 'In Progress').length)

const pendingScosOnPrimary = computed(() => {
  if (!primaryProject.value) return 0
  return store.scosByProject(primaryProject.value.id).filter(s => s.status === 'Pending Approval').length
})

const PRIORITY_RANK = { High: 3, Medium: 2, Low: 1 }

const todaysTasks = computed(() =>
  myTasks.value
    .filter(t => t.status === 'Open' || t.status === 'In Progress')
    .sort((a, b) => {
      const pa = PRIORITY_RANK[a.priority] || 0
      const pb = PRIORITY_RANK[b.priority] || 0
      if (pa !== pb) return pb - pa
      return new Date(a.endDate).getTime() - new Date(b.endDate).getTime()
    })
    .slice(0, 8)
    .map(t => {
      const wp = t.workPackageId ? store.workPackageById(t.workPackageId) : null
      return { ...t, wpName: wp?.name || null }
    })
)

const quickActions = computed(() => [
  { icon: '👷', label: 'Mark attendance',   to: '/app/workforce',    sub: 'Open Workforce' },
  { icon: '📸', label: 'Daily progress',    to: '/app/tasks',        sub: `${inProgressCount.value} task${inProgressCount.value === 1 ? '' : 's'} in progress` },
  { icon: '🧾', label: 'Raise material request', to: '/app/procurement', sub: 'Open Procurement' },
  { icon: '⚠️', label: 'Report issue / SCO', to: '/app/sco', sub: pendingScosOnPrimary.value === 0 ? 'No SCOs pending on this project' : `${pendingScosOnPrimary.value} pending on this project` },
])

const alerts = computed(() => {
  const out = []
  // Overdue task alerts
  myTasks.value.forEach(t => {
    if (t.status === 'Completed') return
    const due = new Date(t.endDate).getTime()
    if (due < today.getTime() && (t.progress || 0) < 100) {
      const daysOver = Math.ceil((today.getTime() - due) / 86400000)
      out.push({
        key: `overdue-${t.id}`,
        severity: 'danger',
        title: `Overdue: ${t.name}`,
        sub: `${daysOver}d past due · ${t.progress}% complete`,
        to: `/app/tasks/${t.id}`,
      })
    }
  })
  // Work-package behind-schedule alerts (WPs whose tasks I work on)
  const wpIds = new Set(myTasks.value.map(t => t.workPackageId).filter(Boolean))
  wpIds.forEach(wpId => {
    const wp = store.workPackageById(wpId)
    if (!wp || !wp.startDate || !wp.endDate) return
    const total = new Date(wp.endDate).getTime() - new Date(wp.startDate).getTime()
    if (total <= 0) return
    const elapsed = Math.max(0, Math.min(total, today.getTime() - new Date(wp.startDate).getTime()))
    const timeElapsedPct = (elapsed / total) * 100
    if (timeElapsedPct > 60 && (wp.progress || 0) < 50) {
      out.push({
        key: `wp-${wp.id}`,
        severity: 'warning',
        title: `${wp.name} behind schedule`,
        sub: `${wp.progress}% complete · ${timeElapsedPct.toFixed(0)}% of time elapsed`,
        to: `/app/work-packages/${wp.id}`,
      })
    }
  })
  return out
})
</script>

<template>
  <LandingShell>
    <div class="max-w-2xl mx-auto px-5 py-8">
      <!-- Mobile-style greeting card -->
      <div class="rounded-2xl p-5 text-white shadow-fp-lg" style="background-image: linear-gradient(135deg, #16A34A 0%, #15803D 100%);">
        <div class="flex items-center gap-2 text-xs opacity-90 uppercase tracking-wider font-medium">
          <span class="w-2 h-2 rounded-full bg-white/80"></span>
          {{ role.shortName }}
        </div>
        <h1 class="text-2xl font-semibold tracking-tight mt-1">Good morning, {{ firstName }}</h1>
        <p class="text-sm opacity-90 mt-1">{{ todayLabel }}</p>
        <div v-if="primaryProject" class="mt-3 pt-3 border-t border-white/20 text-sm">
          <div class="opacity-75 text-xs uppercase tracking-wider">Today's project</div>
          <div class="font-medium mt-0.5">{{ primaryProject.name }}</div>
        </div>
      </div>

      <!-- Quick actions -->
      <h2 class="text-sm font-semibold text-ink-900 mt-8 mb-3">Today's quick actions</h2>
      <div class="grid grid-cols-2 gap-3">
        <RouterLink
          v-for="a in quickActions"
          :key="a.label"
          :to="a.to"
          class="block bg-white border border-ink-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-fp-md transition-all"
        >
          <div class="text-2xl mb-2">{{ a.icon }}</div>
          <div class="text-sm font-medium text-ink-900 leading-tight">{{ a.label }}</div>
          <div class="text-[11px] text-ink-500 mt-1 leading-snug">{{ a.sub }}</div>
        </RouterLink>
      </div>

      <!-- My tasks today -->
      <h2 class="text-sm font-semibold text-ink-900 mt-8 mb-3">My tasks today</h2>
      <div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
        <div class="divide-y divide-ink-100">
          <RouterLink
            v-for="t in todaysTasks"
            :key="t.id"
            :to="`/app/tasks/${t.id}`"
            class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
          >
            <span
              class="w-2 h-2 rounded-full flex-shrink-0"
              :class="t.status === 'In Progress' ? 'bg-brand-500' : 'bg-ink-300'"
            ></span>
            <div class="flex-1 min-w-0">
              <div class="text-sm text-ink-900 leading-snug">{{ t.name }}</div>
              <div v-if="t.wpName" class="text-[11px] text-ink-500 mt-0.5 truncate">{{ t.wpName }}</div>
            </div>
            <div class="text-right flex-shrink-0">
              <div class="text-xs text-ink-700 tabular-nums font-medium">{{ t.progress }}%</div>
              <div class="text-[10px] text-ink-500 uppercase tracking-wider">{{ t.priority }}</div>
            </div>
          </RouterLink>
          <div v-if="!todaysTasks.length" class="px-4 py-8 text-center text-sm text-ink-400">
            No open tasks assigned to you. Nice.
          </div>
        </div>
      </div>

      <!-- Alerts -->
      <h2 class="text-sm font-semibold text-ink-900 mt-8 mb-3">Alerts</h2>
      <div v-if="alerts.length" class="space-y-2">
        <RouterLink
          v-for="a in alerts"
          :key="a.key"
          :to="a.to"
          class="block rounded-xl px-4 py-3 border"
          :class="a.severity === 'danger' ? 'bg-danger-50 border-danger-200 hover:border-danger-300' : 'bg-warning-50 border-warning-200 hover:border-warning-300'"
        >
          <div class="flex items-start gap-2.5">
            <span class="text-lg leading-none mt-0.5">{{ a.severity === 'danger' ? '🔴' : '⚠️' }}</span>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium leading-snug" :class="a.severity === 'danger' ? 'text-danger-800' : 'text-warning-800'">{{ a.title }}</div>
              <div class="text-xs mt-0.5" :class="a.severity === 'danger' ? 'text-danger-700' : 'text-warning-700'">{{ a.sub }}</div>
            </div>
          </div>
        </RouterLink>
      </div>
      <div v-else class="bg-success-50 border border-success-200 rounded-xl px-4 py-3 text-success-800 text-sm">
        <span class="font-medium">All clear ✓</span>
        <span class="text-success-700 ml-1">· No overdue tasks or behind-schedule work packages.</span>
      </div>
    </div>
  </LandingShell>
</template>
