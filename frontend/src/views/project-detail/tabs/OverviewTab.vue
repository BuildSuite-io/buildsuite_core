<script setup>
import { RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { fmtDate, fmtCompactINR } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({
  project:          { type: Object,   required: true },
  activeBoq:        { type: Object,   default: null },
  projectReports:   { type: Array,    default: () => [] },
  delayedDays:      { type: Number,   default: 0 },
  scheduleSummary:  { type: Object,   default: null },
  progressBarColor: { type: Function, required: true },
})

const emit = defineEmits(['edit'])

const store = useDataStore()

function plannedCost() {
  if (props.activeBoq) return store.boqTotals(props.activeBoq.id).planned
  return props.project?.budget || 0
}
function actualCost() {
  if (props.activeBoq) return store.boqTotals(props.activeBoq.id).actual
  return 0
}
function costDeviation() { return actualCost() - plannedCost() }
function costDeviationPct() {
  return plannedCost() ? (costDeviation() / plannedCost()) * 100 : 0
}
function deviationColor(pct) {
  if (Math.abs(pct) < 0.5) return 'text-ink-500'
  return pct > 0 ? 'text-danger-700' : 'text-success-700'
}
</script>

<template>
  <div class="pt-5">
    <!-- Summary strip -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      <!-- Client -->
      <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('building-2')" />
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Client</div>
        </div>
        <div class="text-sm text-ink-900 font-medium mt-1.5 truncate">{{ project.client || '—' }}</div>
      </div>

      <!-- Actual vs Planned -->
      <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('wallet')" />
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Actual vs Planned</div>
        </div>
        <div class="flex items-baseline gap-1 mt-1.5 tabular-nums">
          <span class="text-base font-semibold text-ink-900">{{ fmtCompactINR(actualCost()) }}</span>
          <span class="text-xs text-ink-400">/ {{ fmtCompactINR(plannedCost()) }}</span>
        </div>
        <div class="text-[11px] mt-1 tabular-nums" :class="deviationColor(costDeviationPct())">
          <span class="font-medium">{{ costDeviation() > 0 ? '+' : '' }}{{ fmtCompactINR(Math.abs(costDeviation())) }}</span>
          <span class="ml-0.5">({{ costDeviationPct() > 0 ? '+' : '' }}{{ costDeviationPct().toFixed(1) }}%)</span>
          <span class="text-ink-400 ml-0.5">{{ costDeviationPct() > 0 ? 'over' : 'under' }}</span>
        </div>
      </div>

      <!-- Progress + delayed -->
      <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('chart-line')" />
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Progress</div>
        </div>
        <div class="flex items-center gap-2 mt-1.5">
          <div class="flex-1 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 999px;">
            <div class="h-full" :class="progressBarColor(project)" :style="`width:${project.progress}%`"></div>
          </div>
          <span class="text-sm text-ink-900 font-semibold tabular-nums">{{ project.progress }}%</span>
        </div>
        <div v-if="delayedDays > 0" class="text-[11px] text-danger-700 font-medium mt-1">
          Delayed by {{ delayedDays }}d
        </div>
        <div v-else-if="project.progress >= 100" class="text-[11px] text-success-700 font-medium mt-1">
          Completed
        </div>
        <div v-else class="text-[11px] text-success-700 font-medium mt-1">
          On track
        </div>
      </div>

      <!-- Timeline -->
      <div class="bg-white border border-ink-200 p-3.5" style="border-radius: 8px;">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('calendar')" />
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Timeline</div>
        </div>
        <div class="text-xs text-ink-900 font-medium mt-1.5 tabular-nums">
          {{ fmtDate(project.startDate) }} → {{ fmtDate(project.endDate) }}
        </div>
        <div v-if="scheduleSummary" class="text-[11px] text-ink-500 mt-1 tabular-nums">
          {{ scheduleSummary.totalDays }}d total · {{ scheduleSummary.remainingDays }}d remaining
        </div>
      </div>
    </div>

    <!-- Two-column main / sidebar layout -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

      <!-- Main column (span 2) -->
      <div class="lg:col-span-2 space-y-4">

        <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
          <header class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('clipboard-list')" />
            <h3 class="text-sm font-semibold text-ink-900">About this project</h3>
          </header>
          <div class="p-5">
            <p class="text-sm text-ink-800 leading-relaxed whitespace-pre-wrap">{{ project.description || 'No description provided yet.' }}</p>
          </div>
        </section>

        <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
          <header class="px-5 py-3 bg-gradient-to-r from-info-50 to-white border-b border-ink-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('chart-line')" />
            <h3 class="text-sm font-semibold text-ink-900">Reports</h3>
          </header>
          <div class="p-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
              <RouterLink
                v-for="rt in projectReports"
                :key="rt.slug"
                :to="`/reports/${rt.slug}`"
                class="bg-white border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 p-3 transition-colors group block"
                style="border-radius: 8px;"
              >
                <div class="flex items-start gap-2.5">
                  <svg class="w-5 h-5 text-ink-600 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath(rt.icon)" />
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-1.5 flex-wrap">
                      <div class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors">{{ rt.label }}</div>
                      <span class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider" style="border-radius: 2px;">Report</span>
                    </div>
                    <div class="text-[11px] text-ink-500 mt-0.5 leading-snug">{{ rt.desc }}</div>
                  </div>
                </div>
              </RouterLink>
            </div>
          </div>
        </section>
      </div>

      <!-- Sidebar (span 1) -->
      <div class="space-y-4">

        <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
          <header class="px-4 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('hr')" />
            <h3 class="text-sm font-semibold text-ink-900">Project Manager</h3>
          </header>
          <div class="p-4 flex items-center gap-3">
            <template v-if="project.pm">
              <UserAvatar :user-id="project.pm" size="md" />
              <div class="min-w-0 flex-1">
                <div class="text-sm font-semibold text-ink-900 truncate">{{ store.teamMember(project.pm)?.name || project.pm }}</div>
                <div class="text-[11px] text-ink-500 truncate">{{ store.teamMember(project.pm)?.role || 'Project Manager' }}</div>
              </div>
            </template>
            <div v-else class="text-sm text-ink-500">No project manager assigned.</div>
          </div>
        </section>

        <section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px;">
          <header class="px-4 py-3 bg-gradient-to-r from-ink-50 to-white border-b border-ink-100 flex items-center gap-2">
            <svg class="w-4 h-4 text-ink-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('tag')" />
            <h3 class="text-sm font-semibold text-ink-900">Project details</h3>
            <button
              type="button"
              class="ml-auto text-[11px] text-brand-700 hover:text-brand-800 font-medium"
              @click="emit('edit')"
            >Edit</button>
          </header>
          <dl class="divide-y divide-ink-100">
            <div class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Status</dt>
              <dd><StatusBadge :status="project.status" /></dd>
            </div>
            <div class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Priority</dt>
              <dd><StatusBadge :status="project.priority" /></dd>
            </div>
            <div class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Type</dt>
              <dd class="text-ink-800">{{ project.type || '—' }}</dd>
            </div>
            <div v-if="store.isMultiCompany && project.company" class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Company</dt>
              <dd class="flex items-center gap-1.5 text-ink-800 min-w-0">
                <span
                  v-if="store.companyById(project.company)"
                  :class="store.companyById(project.company).color"
                  class="w-2 h-2 flex-shrink-0"
                  style="border-radius: 999px;"
                ></span>
                <span class="truncate">{{ store.companyById(project.company)?.shortName || project.company }}</span>
              </dd>
            </div>
            <div class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Location</dt>
              <dd class="text-ink-800 truncate ml-2">{{ project.location || '—' }}</dd>
            </div>
            <div class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Project ID</dt>
              <dd class="text-ink-800 font-mono">{{ project.code }}</dd>
            </div>
            <div class="flex items-center justify-between px-4 py-2.5 text-xs">
              <dt class="text-ink-500 font-medium">Created</dt>
              <dd class="text-ink-700 tabular-nums">{{ fmtDate(project.createdAt) }}</dd>
            </div>
          </dl>
        </section>

      </div>
    </div>
  </div>
</template>
