<script setup>
// Task Progress Entry — list view. Desk-styled (CLAUDE.md §12.4). This is the
// canonical M2 progress-update record from §13.3 item 17; the underlying store
// slice was added in Session 22. Every list interaction here flows through
// store.addTaskProgressEntry / updateTaskProgressEntry / deleteTaskProgressEntry,
// each of which triggers _recomputeTaskFromEntries (the prototype's simulation
// of the M1 server hook that auto-updates the parent Task's progress + status).

import { computed, ref } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskList from '@/components/desk/DeskList.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtDate } from '@/utils/format'

const store = useDataStore()
const router = useRouter()
const route = useRoute()

const search = ref('')
const taskFilter = ref(route.query.task || '')
const enteredByFilter = ref('')
const blockerOnly = ref(false)

const TODAY = new Date().toISOString().slice(0, 10)
function daysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}
const SEVEN_DAYS_AGO = daysAgo(6)  // inclusive 7-day window

const allEntries = computed(() => store.taskProgressEntries)
function taskName(id) { return store.taskById(id)?.name || id }
function memberName(id) { return store.teamMember(id)?.name || id }

const items = computed(() => {
  const term = search.value.trim().toLowerCase()
  return allEntries.value.filter(e => {
    if (taskFilter.value && e.taskId !== taskFilter.value) return false
    if (enteredByFilter.value && e.enteredBy !== enteredByFilter.value) return false
    if (blockerOnly.value && !e.blockerFlag) return false
    if (term) {
      const hay = `${e.id} ${e.narrative || ''} ${taskName(e.taskId)} ${e.blockerNote || ''}`.toLowerCase()
      if (!hay.includes(term)) return false
    }
    return true
  }).slice().sort((a, b) => {
    const cmp = (b.entryDate || '').localeCompare(a.entryDate || '')
    return cmp !== 0 ? cmp : (b.id || '').localeCompare(a.id || '')
  })
})

const kpis = computed(() => {
  const all = allEntries.value
  return {
    total:        all.length,
    today:        all.filter(e => e.entryDate === TODAY).length,
    thisWeek:     all.filter(e => e.entryDate >= SEVEN_DAYS_AGO).length,
    blockers:     all.filter(e => e.blockerFlag).length,
  }
})

const WEATHER_ICON = {
  Clear: '☀️', Rainy: '🌧️', Hot: '🌡️', Cold: '❄️', Storm: '⛈️',
}

const columns = [
  { key: 'id',           label: 'ID' },
  { key: 'entryDate',    label: 'Date' },
  { key: 'task',         label: 'Task' },
  { key: 'progressPct',  label: 'Progress', align: 'right' },
  { key: 'labour',       label: 'Labour',   align: 'right' },
  { key: 'weather',      label: 'Weather' },
  { key: 'flags',        label: 'Flags' },
  { key: 'enteredBy',    label: 'Entered by' },
]

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Task Progress Entry' },
]

const subtitle = computed(() =>
  `${items.value.length} of ${allEntries.value.length} · M2 canonical progress record · §13.3 item 17`
)

function onRowClick(row) { router.push(`/app/progress-entries/${row.id}`) }
</script>

<template>
  <DeskPage title="Task Progress Entry" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/app/progress-entries/new" class="desk-save-btn">+ New Entry</RouterLink>
    </template>

    <!-- KPI strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Total entries</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ kpis.total }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Filed today</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ kpis.today }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Last 7 days</div>
        <div class="text-base font-semibold text-ink-900 mt-0.5">{{ kpis.thisWeek }}</div>
      </div>
      <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
        <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Flagged blockers</div>
        <div class="text-base font-semibold mt-0.5" :class="kpis.blockers > 0 ? 'text-danger-700' : 'text-ink-900'">{{ kpis.blockers }}</div>
      </div>
    </div>

    <DeskList
      v-model="search"
      :rows="items"
      :columns="columns"
      row-key="id"
      search-placeholder="Search narrative, task, blocker note…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <!-- Task filter -->
        <DeskSelect v-if="!taskFilter" v-model="taskFilter" class="!w-56">
          <option value="">Task: Any</option>
          <option v-for="t in store.tasks" :key="t.id" :value="t.id">{{ t.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Task"
          :value="taskName(taskFilter)"
          @remove="taskFilter = ''"
        />

        <!-- Entered by filter -->
        <DeskSelect v-if="!enteredByFilter" v-model="enteredByFilter" class="!w-44">
          <option value="">Entered by: Any</option>
          <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }}</option>
        </DeskSelect>
        <DeskFilterChip
          v-else
          label="Entered by"
          :value="memberName(enteredByFilter)"
          @remove="enteredByFilter = ''"
        />

        <!-- Blocker-only toggle. Renders as a chip when active. -->
        <button
          v-if="!blockerOnly"
          type="button"
          class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
          style="border-radius: 2px;"
          @click="blockerOnly = true"
        >🚩 Blockers only</button>
        <DeskFilterChip
          v-else
          label="Blockers"
          value="only"
          @remove="blockerOnly = false"
        />
      </template>

      <template #cell-id="{ row }">
        <DeskLink :to="`/app/progress-entries/${row.id}`" @click.stop class="font-mono text-xs">{{ row.id }}</DeskLink>
      </template>
      <template #cell-entryDate="{ row }">
        <span class="text-xs text-ink-700">{{ fmtDate(row.entryDate) }}</span>
      </template>
      <template #cell-task="{ row }">
        <DeskLink :to="`/app/tasks/${row.taskId}`" @click.stop>{{ taskName(row.taskId) }}</DeskLink>
      </template>
      <template #cell-progressPct="{ row }">
        <div class="flex items-center justify-end gap-2">
          <div class="w-14 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
            <div
              class="h-full"
              :class="row.progressPct === 100 ? 'bg-success-500' : row.progressPct > 0 ? 'bg-brand-500' : 'bg-ink-300'"
              :style="`width:${row.progressPct}%`"
            ></div>
          </div>
          <span class="text-xs tabular-nums w-8 text-right font-medium">{{ row.progressPct }}%</span>
        </div>
      </template>
      <template #cell-labour="{ row }">
        <span class="text-xs text-ink-700 tabular-nums">
          {{ row.skilledLabour }}+{{ row.unskilledLabour }}
          <span class="text-ink-400">({{ row.skilledLabour + row.unskilledLabour }})</span>
        </span>
      </template>
      <template #cell-weather="{ row }">
        <span v-if="row.weather" class="text-xs">
          <span class="mr-1">{{ WEATHER_ICON[row.weather] || '' }}</span>{{ row.weather }}
        </span>
        <span v-else class="text-[10px] text-ink-300">—</span>
      </template>
      <template #cell-flags="{ row }">
        <span
          v-if="row.blockerFlag"
          class="text-[10px] px-1.5 py-0.5 bg-danger-50 text-danger-700 font-medium"
          style="border-radius: 2px;"
          :title="row.blockerNote || 'Blocker flagged'"
        >🚩 Blocker</span>
        <span v-else class="text-[10px] text-ink-300">—</span>
      </template>
      <template #cell-enteredBy="{ row }">
        <UserAvatar :user-id="row.enteredBy" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No progress entries match these filters ·
          <RouterLink to="/app/progress-entries/new" class="desk-link">File a new entry →</RouterLink>
        </div>
      </template>
    </DeskList>
  </DeskPage>
</template>
