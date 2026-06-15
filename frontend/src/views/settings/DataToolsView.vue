<script setup>
// Data Tools — Settings sub-page. Preserves the Export / Reset actions that
// used to live on the old single-page SettingsView (Session 19 work). Adds a
// localStorage-key inspector so reviewers can see exactly what the prototype
// persists (and what's NOT persisted — blob URLs, role pref under its own key).

import { useDataStore } from '@/stores'
import { useConfirm } from '@/composables/useConfirm'
import { RouterLink } from 'vue-router'
import DeskPage from '@/components/desk/DeskPage.vue'

const store = useDataStore()
const confirmDialog = useConfirm()

async function resetData() {
  const ok = await confirmDialog({
    title: 'Reset all data',
    message: 'Reset all data to initial seed values?\n\nAny projects, tasks, SCOs, attachments, and stage plannings you created will be lost. Role and active-company preferences are preserved (they live under separate localStorage keys).',
    confirmLabel: 'Reset',
    destructive: true,
  })
  if (!ok) return
  store.resetAll()
  location.reload()
}

function exportData() {
  // Full payload — every slice that's part of saveToStorage. Useful as a
  // diagnostic dump too.
  const payload = {
    exportedAt: new Date().toISOString(),
    activeRole: store.role,
    activeCompany: store.activeCompany,
    companies: store.companies,
    user: store.user,
    team: store.team,
    projects: store.projects,
    workPackages: store.workPackages,
    tasks: store.tasks,
    activityTypes: store.activityTypes,
    taskProgressEntries: store.taskProgressEntries,
    stagePlannings: store.stagePlannings,
    attachments: store.attachments,
    scos: store.scos,
    rateMaster: store.rateMaster,
    rateHistory: store.rateHistory,
    boqs: store.boqs,
    boqGroups: store.boqGroups,
    boqItems: store.boqItems,
    boqSubItems: store.boqSubItems,
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `buildsuite-data-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Settings', to: '/settings' },
  { label: 'Data Tools' },
]
</script>

<template>
  <DeskPage title="Data Tools" subtitle="Prototype dataset · export · reset · localStorage inspector" :breadcrumbs="breadcrumbs">

    <div class="max-w-3xl">

      <section class="mb-5">
        <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Persistence model</h2>
        <hr class="border-0 border-t border-ink-200 mt-1 mb-3" />
        <div class="bg-white border border-ink-200 px-4 py-3 text-xs text-ink-700 leading-relaxed" style="border-radius: 2px;">
          <p class="mb-2">
            All domain data lives in your browser's <code class="bg-ink-50 px-1 py-0.5 border border-ink-200" style="border-radius: 2px;">localStorage</code> — no backend, no API.
            Created projects, tasks, SCOs, BOQs, attachments, and stage plannings persist across reloads in <em>this browser only</em>.
          </p>
          <p class="mb-2">
            Three independent keys:
          </p>
          <ul class="space-y-1 ml-4 list-disc">
            <li><code class="bg-ink-50 px-1 py-0.5 border border-ink-200" style="border-radius: 2px;">buildsuite:data:v1</code> — full domain payload (rehydrated by store.hydrate()).</li>
            <li><code class="bg-ink-50 px-1 py-0.5 border border-ink-200" style="border-radius: 2px;">buildsuite:role</code> — active role (separate so resetAll() preserves UI preference).</li>
            <li><code class="bg-ink-50 px-1 py-0.5 border border-ink-200" style="border-radius: 2px;">buildsuite:company</code> — active company (same independent-persistence pattern).</li>
          </ul>
          <p class="mt-2 text-ink-500 italic">
            Attachment file bytes live as <code class="bg-ink-50 px-1 py-0.5 border border-ink-200" style="border-radius: 2px;">blob:</code> URLs in the renderer process — session-only, lost on tab close (per §13.3 items 13 + 26).
          </p>
        </div>
      </section>

      <section class="mb-5">
        <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Export</h2>
        <hr class="border-0 border-t border-ink-200 mt-1 mb-3" />
        <div class="bg-white border border-ink-200 px-4 py-3" style="border-radius: 2px;">
          <p class="text-xs text-ink-600 mb-3">
            Download the full payload as JSON — useful for sharing a snapshot with the dev team or attaching to a bug report. Includes every slice from saveToStorage plus the active role + company.
          </p>
          <button
            type="button"
            @click="exportData"
            class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
            style="border-radius: 2px;"
          >Export as JSON</button>
        </div>
      </section>

      <section>
        <h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Reset</h2>
        <hr class="border-0 border-t border-ink-200 mt-1 mb-3" />
        <div class="bg-white border border-ink-200 px-4 py-3" style="border-radius: 2px;">
          <p class="text-xs text-ink-600 mb-3">
            Wipe <code class="bg-ink-50 px-1 py-0.5 border border-ink-200" style="border-radius: 2px;">buildsuite:data:v1</code> and re-hydrate from seed. Role / active-company preferences survive (separate keys).
            Useful when seed data has been updated and you want to pick up the new shape.
          </p>
          <button
            type="button"
            @click="resetData"
            class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
            style="border-radius: 2px; color: #B91C1C;"
          >Reset all data</button>
        </div>
      </section>

    </div>
  </DeskPage>
</template>
