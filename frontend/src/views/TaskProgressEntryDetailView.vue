<script setup>
// Task Progress Entry — detail view. Desk-styled (CLAUDE.md §12.4).
// Edits and deletes go through store.updateTaskProgressEntry / deleteTaskProgressEntry,
// both of which trigger _recomputeTaskFromEntries (the M1 server-hook simulation that
// auto-updates the parent Task's progress + status from the latest entry — see §13.3
// item 20). So saving a smaller progressPct on the latest entry will pull the parent
// task back; deleting the latest entry will revert the task to the prior entry's value
// (or to 0/Open if no entries remain).

import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import { fmtDate } from '@/utils/format'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()

const entry = computed(() => store.taskProgressEntries.find(e => e.id === props.id))
const task = computed(() => entry.value ? store.taskById(entry.value.taskId) : null)
const project = computed(() => task.value ? store.projectById(task.value.projectId) : null)
const wp = computed(() => task.value?.workPackageId ? store.workPackageById(task.value.workPackageId) : null)

// Latest entry on the parent task — useful context when viewing an older entry,
// since this entry's progressPct may differ from the task's current progress.
const latestOnTask = computed(() => task.value ? store.latestProgressEntry(task.value.id) : null)
const isLatestOnTask = computed(() => latestOnTask.value && entry.value && latestOnTask.value.id === entry.value.id)

const editing = ref(false)
const form = ref({})

watch(entry, (e) => { if (e) form.value = { ...e } }, { immediate: true })

function startEdit() {
  if (entry.value) form.value = { ...entry.value }
  editing.value = true
}
function saveEdit() {
  store.updateTaskProgressEntry(props.id, form.value)
  editing.value = false
}
function cancelEdit() {
  if (entry.value) form.value = { ...entry.value }
  editing.value = false
}
function onPrimary() {
  if (editing.value) saveEdit()
  else startEdit()
}
function deleteEntry() {
  const wasLatest = isLatestOnTask.value
  const taskId = entry.value?.taskId
  if (!confirm(wasLatest
    ? `Delete this entry? It's the latest on the task — the task's progress will revert to the previous entry (or 0% if this is the only one).`
    : `Delete this entry? It's a historical entry; the task's current progress will not change.`)) return
  store.deleteTaskProgressEntry(props.id)
  // Return to the parent task if we have it, otherwise the list.
  router.push(taskId ? `/app/tasks/${taskId}` : '/app/progress-entries')
}

const WEATHER_OPTIONS = ['Clear', 'Rainy', 'Hot', 'Cold', 'Storm']
const WEATHER_ICON = { Clear: '☀️', Rainy: '🌧️', Hot: '🌡️', Cold: '❄️', Storm: '⛈️' }

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Task Progress Entry', to: '/app/progress-entries' },
  ]
  if (task.value) out.push({ label: task.value.name, to: `/app/tasks/${task.value.id}` })
  return out
})

const titleStatuses = computed(() => {
  if (!entry.value) return []
  const out = [`${entry.value.progressPct}% cumulative`]
  if (entry.value.blockerFlag) out.push('Blocker')
  if (isLatestOnTask.value) out.push('Latest on task')
  return out
})

const subtitle = computed(() => entry.value
  ? `${entry.value.id} · ${fmtDate(entry.value.entryDate)}`
  : '')
</script>

<template>
  <DeskPage
    v-if="entry"
    :title="task ? task.name : entry.id"
    :subtitle="subtitle"
    :breadcrumbs="breadcrumbs"
    :status="titleStatuses"
  >
    <DeskForm>
      <template #action-bar>
        <DeskActionBar
          :save-label="editing ? 'Save' : 'Edit'"
          :show-cancel="editing"
          cancel-label="Cancel"
          @save="onPrimary"
          @cancel="cancelEdit"
        >
          <template #left>
            <span v-if="!isLatestOnTask && latestOnTask" class="text-[11px] text-ink-500">
              ⚠ Older entry — task's current progress is
              <DeskLink :to="`/app/progress-entries/${latestOnTask.id}`" class="font-medium">{{ latestOnTask.progressPct }}% from TPE-{{ latestOnTask.id.split('-').slice(-2).join('-') }}</DeskLink>
            </span>
          </template>
          <template #menu>
            <button
              type="button"
              class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
              style="border-radius: 2px; color: #B91C1C;"
              @click="deleteEntry"
            >Delete</button>
          </template>
        </DeskActionBar>
      </template>

      <!-- 2-col body: main details on the left, Connections on the right -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2">
          <!-- Progress section -->
          <DeskSection title="Progress" v-if="!editing">
            <DeskField label="Entry date">
              <div class="text-sm text-ink-900 py-1">{{ fmtDate(entry.entryDate) }}</div>
            </DeskField>
            <DeskField label="Cumulative progress">
              <div class="flex items-center gap-3 py-1">
                <div class="flex-1 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px;">
                  <div
                    class="h-full"
                    :class="entry.progressPct === 100 ? 'bg-success-500' : entry.progressPct > 0 ? 'bg-brand-500' : 'bg-ink-300'"
                    :style="`width:${entry.progressPct}%`"
                  ></div>
                </div>
                <span class="text-base font-semibold tabular-nums text-ink-900 w-12 text-right">{{ entry.progressPct }}%</span>
              </div>
            </DeskField>
            <DeskField label="Narrative">
              <div class="text-sm text-ink-700 py-1 whitespace-pre-wrap">{{ entry.narrative || '—' }}</div>
            </DeskField>
          </DeskSection>

          <DeskSection title="Progress" v-else>
            <DeskField label="Entry date">
              <DeskInput v-model="form.entryDate" type="date" />
            </DeskField>
            <DeskField label="Cumulative progress (%)" required hint="The NEW cumulative % after this entry — not a delta. 0–100.">
              <DeskInput v-model="form.progressPct" type="number" min="0" max="100" step="1" />
            </DeskField>
            <DeskField label="Narrative">
              <DeskTextarea v-model="form.narrative" :rows="3" placeholder="What was completed today? Any context worth recording?" />
            </DeskField>
          </DeskSection>

          <!-- Labour section -->
          <DeskSection title="Labour deployed today" :cols="2" v-if="!editing">
            <DeskField label="Skilled labour">
              <div class="text-sm text-ink-900 py-1 tabular-nums">{{ entry.skilledLabour || 0 }}</div>
            </DeskField>
            <DeskField label="Unskilled labour">
              <div class="text-sm text-ink-900 py-1 tabular-nums">{{ entry.unskilledLabour || 0 }}</div>
            </DeskField>
          </DeskSection>

          <DeskSection title="Labour deployed today" :cols="2" v-else>
            <DeskField label="Skilled labour" hint="Count of skilled workers on site today">
              <DeskInput v-model="form.skilledLabour" type="number" />
            </DeskField>
            <DeskField label="Unskilled labour" hint="Count of unskilled workers / helpers">
              <DeskInput v-model="form.unskilledLabour" type="number" />
            </DeskField>
          </DeskSection>

          <!-- Conditions section -->
          <DeskSection title="Site conditions" :cols="2" v-if="!editing">
            <DeskField label="Weather">
              <div class="text-sm text-ink-900 py-1">
                <span v-if="entry.weather">
                  <span class="mr-1">{{ WEATHER_ICON[entry.weather] || '' }}</span>{{ entry.weather }}
                </span>
                <span v-else class="text-ink-400">—</span>
              </div>
            </DeskField>
            <DeskField label="Blocker">
              <div class="text-sm py-1">
                <span
                  v-if="entry.blockerFlag"
                  class="text-[10px] px-1.5 py-0.5 bg-danger-50 text-danger-700 font-medium"
                  style="border-radius: 2px;"
                >🚩 Blocker flagged</span>
                <span v-else class="text-ink-500 text-xs">No blocker</span>
              </div>
            </DeskField>
            <div v-if="entry.blockerFlag && entry.blockerNote" class="md:col-span-2">
              <DeskField label="Blocker detail">
                <div class="text-sm text-ink-700 py-1 whitespace-pre-wrap">{{ entry.blockerNote }}</div>
              </DeskField>
            </div>
          </DeskSection>

          <DeskSection title="Site conditions" :cols="2" v-else>
            <DeskField label="Weather">
              <DeskSelect v-model="form.weather">
                <option value="">— No record —</option>
                <option v-for="w in WEATHER_OPTIONS" :key="w" :value="w">{{ w }}</option>
              </DeskSelect>
            </DeskField>
            <DeskField label="Blocker">
              <label class="flex items-center gap-2 py-1 text-sm text-ink-700 cursor-pointer">
                <input v-model="form.blockerFlag" type="checkbox" class="h-3.5 w-3.5" />
                Flag a blocker on this entry
              </label>
            </DeskField>
            <div v-if="form.blockerFlag" class="md:col-span-2">
              <DeskField label="Blocker detail" hint="What blocked progress today?">
                <DeskTextarea v-model="form.blockerNote" :rows="2" />
              </DeskField>
            </div>
          </DeskSection>

          <!-- Attachments (stub — full upload pipeline lives in Phase 4) -->
          <DeskSection title="Attachments">
            <div class="md:col-span-2 text-xs text-ink-500">
              <template v-if="(entry.attachments || []).length">
                <ul class="space-y-1">
                  <li v-for="(f, i) in entry.attachments" :key="i" class="font-mono">📎 {{ f }}</li>
                </ul>
              </template>
              <template v-else>
                <span class="italic">No attachments on this entry.</span>
                <span class="text-ink-400 italic ml-1">Full upload pipeline — Phase 4.</span>
              </template>
            </div>
          </DeskSection>
        </div>

        <!-- Connections panel (Frappe-style related-records) -->
        <aside class="lg:col-span-1 space-y-2">
          <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Task</div>
            <DeskLink v-if="task" :to="`/app/tasks/${task.id}`" class="text-sm font-medium">{{ task.name }}</DeskLink>
            <span v-else class="text-sm text-ink-500">—</span>
            <div v-if="task" class="text-[11px] text-ink-500 mt-1">
              Currently {{ task.progress }}% · {{ task.status }}
            </div>
          </div>
          <div v-if="project" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Project</div>
            <DeskLink :to="`/app/projects/${project.id}`" class="text-sm font-medium">{{ project.name }}</DeskLink>
          </div>
          <div v-if="wp" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Work Package</div>
            <DeskLink :to="`/app/work-packages/${wp.id}`" class="text-sm font-medium">{{ wp.name }}</DeskLink>
          </div>
          <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Entered by</div>
            <UserAvatar :user-id="entry.enteredBy" :show-name="true" />
          </div>
          <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Total labour</div>
            <div class="text-sm text-ink-700 tabular-nums">
              {{ (entry.skilledLabour || 0) + (entry.unskilledLabour || 0) }} workers
              <span class="text-[11px] text-ink-500">({{ entry.skilledLabour || 0 }} skilled, {{ entry.unskilledLabour || 0 }} unskilled)</span>
            </div>
          </div>
        </aside>
      </div>

      <!-- Comments / Attachments stub footer -->
      <section class="mt-8 pt-4 border-t border-ink-200">
        <div class="flex items-center gap-6 text-xs text-ink-500 flex-wrap">
          <div class="flex items-center gap-1.5">
            <span>💬</span><span>Comments — <span class="font-medium text-ink-700">0</span></span>
            <span class="text-ink-400 italic ml-1">stub</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span>📎</span><span>Attachments — <span class="font-medium text-ink-700">{{ (entry.attachments || []).length }}</span></span>
            <span v-if="!(entry.attachments || []).length" class="text-ink-400 italic ml-1">stub</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span>👥</span><span>Entered by —</span>
            <UserAvatar :user-id="entry.enteredBy" size="xs" />
          </div>
        </div>
      </section>
    </DeskForm>
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">Progress entry not found.</div>
</template>
