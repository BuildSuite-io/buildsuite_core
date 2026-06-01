<script setup>
// Task Detail. Edit + Delete + quick-status actions live on the title row
// (DeskPage #actions slot). Editing opens a modal so the inline content
// stays readable. Progress block is pinned to the top so the headline number
// is the first thing visible.

import { ref, reactive, computed, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useDataStore } from '@/stores'
import StatusBadge from '@/components/StatusBadge.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
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

const task = computed(() => store.taskById(props.id))
const project = computed(() => task.value ? store.projectById(task.value.projectId) : null)
const wp = computed(() => task.value?.workPackageId ? store.workPackageById(task.value.workPackageId) : null)
const activityType = computed(() => task.value?.activityType ? store.activityTypeById(task.value.activityType) : null)
const latestEntry = computed(() => task.value ? store.latestProgressEntry(task.value.id) : null)
const recentEntries = computed(() => task.value ? store.taskProgressEntriesByTask(task.value.id).slice(0, 3) : [])
const entryCount = computed(() => task.value ? store.taskProgressEntriesByTask(task.value.id).length : 0)

// ----- File Progress Entry modal -----------------------------------------
// Replaces the previous route-jump to /app/progress-entries/new. Keeps the
// user on the task home; saves via store.addTaskProgressEntry which fires
// the recompute hook so the page's progress card updates immediately.

const WEATHER_OPTIONS = ['Clear', 'Rainy', 'Hot', 'Cold', 'Storm']
const filingProgress = ref(false)
const savingProgress = ref(false)
const progressForm = reactive({
  entryDate: '',
  enteredBy: '',
  progressPct: 0,
  narrative: '',
  skilledLabour: 0,
  unskilledLabour: 0,
  weather: '',
  blockerFlag: false,
  blockerNote: '',
})
const progressErrors = ref({})

// Pending attachments — files the user picked but haven't been persisted yet
// (the entry record doesn't exist until save). On save we mint the entry
// first, then dispatch store.addAttachment for each pending file with
// parentDoctype = 'Task Progress Entry' and the new entry's id.
const pendingAttachments = ref([])  // [{ fileName, mime, size, url }]
const progressFileInput = ref(null)
// Second input wired with `accept="image/*" capture="environment"` so on
// mobile it opens the rear camera directly (web Capture API). On desktop the
// browser falls back to a file picker filtered to images.
const progressCameraInput = ref(null)

function fmtBytes(n) {
  if (!n) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function openProgressFilePicker() {
  if (progressFileInput.value) progressFileInput.value.click()
}
function openProgressCamera() {
  if (progressCameraInput.value) progressCameraInput.value.click()
}
function onProgressFilesPicked(ev) {
  const files = Array.from(ev.target.files || [])
  for (const f of files) {
    // Camera capture on iOS sometimes gives an empty filename — synthesize
    // one keyed by timestamp so the row still reads sensibly.
    const fileName = f.name && f.name.trim()
      ? f.name
      : `photo-${new Date().toISOString().replace(/[:.]/g, '-')}.jpg`
    pendingAttachments.value.push({
      fileName,
      mime: f.type || 'application/octet-stream',
      size: f.size,
      url: URL.createObjectURL(f),
    })
  }
  // Reset the input so picking the same file twice in a row still fires.
  if (ev.target) ev.target.value = ''
}
function removePendingAttachment(idx) {
  const att = pendingAttachments.value[idx]
  if (att?.url) {
    try { URL.revokeObjectURL(att.url) } catch (_) { /* tolerate non-blob */ }
  }
  pendingAttachments.value.splice(idx, 1)
}
function clearPendingAttachments() {
  for (const a of pendingAttachments.value) {
    if (a?.url) {
      try { URL.revokeObjectURL(a.url) } catch (_) { /* tolerate non-blob */ }
    }
  }
  pendingAttachments.value = []
}

function resetProgressForm() {
  progressForm.entryDate     = new Date().toISOString().slice(0, 10)
  progressForm.enteredBy     = store.user?.id || store.team[0]?.id || ''
  progressForm.progressPct   = task.value?.progress ?? 0
  progressForm.narrative     = ''
  progressForm.skilledLabour = 0
  progressForm.unskilledLabour = 0
  progressForm.weather       = ''
  progressForm.blockerFlag   = false
  progressForm.blockerNote   = ''
  progressErrors.value = {}
  clearPendingAttachments()
}

function fileProgressEntry() {
  if (!task.value) return
  resetProgressForm()
  filingProgress.value = true
}
function cancelProgressEntry() {
  clearPendingAttachments()
  filingProgress.value = false
}
function validateProgressEntry() {
  const e = {}
  const pct = Number(progressForm.progressPct)
  if (Number.isNaN(pct) || pct < 0 || pct > 100) {
    e.progressPct = 'Progress must be between 0 and 100'
  }
  if (progressForm.blockerFlag && !progressForm.blockerNote.trim()) {
    e.blockerNote = 'Describe the blocker'
  }
  progressErrors.value = e
  return Object.keys(e).length === 0
}
function saveProgressEntry() {
  if (!validateProgressEntry()) return
  savingProgress.value = true
  const entry = store.addTaskProgressEntry({ ...progressForm, taskId: props.id })
  // Persist any pending attachments against the new entry. Polymorphic
  // attachments slice — parentDoctype + parentId form the back-reference,
  // and the cascade in deleteTaskProgressEntry sweeps them when the entry
  // is deleted (same shape as Project attachments).
  for (const f of pendingAttachments.value) {
    store.addAttachment({
      parentDoctype: 'Task Progress Entry',
      parentId: entry.id,
      fileName: f.fileName,
      mime: f.mime,
      size: f.size,
      url: f.url,
      uploadedBy: progressForm.enteredBy,
    })
  }
  // Clear local ref WITHOUT revoking blob URLs — the store now owns them and
  // expects to use them on click-to-open. Revoking here would invalidate them.
  pendingAttachments.value = []
  savingProgress.value = false
  filingProgress.value = false
}

// Edit modal state. `editing` controls visibility; `form` is the working copy
// that gets reset on cancel so the store record isn't touched mid-edit.
const editing = ref(false)
const form = ref({})

watch(task, (t) => { if (t && !editing.value) form.value = { ...t } }, { immediate: true })

function startEdit() {
  if (!task.value) return
  form.value = { ...task.value }
  editing.value = true
}
function saveEdit() {
  store.updateTask(props.id, form.value)
  editing.value = false
}
function cancelEdit() {
  form.value = { ...task.value }
  editing.value = false
}

function quickStatus(status) {
  const patch = { status }
  if (status === 'Completed') patch.progress = 100
  if (status === 'Open') patch.progress = 0
  store.updateTask(props.id, patch)
}
function deleteTask() {
  if (confirm('Delete this task?')) {
    store.deleteTask(props.id)
    router.push('/app/tasks')
  }
}

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Task', to: '/app/tasks' },
  ]
  if (project.value) out.push({ label: project.value.name, to: `/app/projects/${project.value.id}` })
  return out
})

// Title-strip badges. task_type sits alongside status + priority.
const titleStatuses = computed(() => {
  if (!task.value) return []
  const out = [task.value.status, task.value.priority]
  if (task.value.task_type) out.push(task.value.task_type)
  return out
})

const progressColor = computed(() => {
  if (!task.value) return 'bg-ink-300'
  if (task.value.progress === 100) return 'bg-success-500'
  if (task.value.progress > 0)     return 'bg-brand-500'
  return 'bg-ink-300'
})
</script>

<template>
  <DeskPage
    v-if="task"
    :title="task.name"
    :subtitle="task.id"
    :breadcrumbs="breadcrumbs"
    :status="titleStatuses"
  >
    <!-- Edit / Delete / quick-status actions share the title row -->
    <template #actions>
      <button
        v-if="task.status === 'Open'"
        type="button"
        class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
        style="border-radius: 6px;"
        @click="quickStatus('In Progress')"
      >Start</button>
      <button
        v-if="task.status !== 'Completed'"
        type="button"
        class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50"
        style="border-radius: 6px; color: #15803D;"
        @click="quickStatus('Completed')"
      >Mark complete</button>
      <button
        type="button"
        class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
        style="border-radius: 6px;"
        @click="startEdit"
      >Edit</button>
      <button
        type="button"
        class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
        style="border-radius: 6px;"
        @click="deleteTask"
      >Delete</button>
    </template>

    <!-- ===== Progress block — pinned at top so the headline number is the
         first thing visible on the task home. ===== -->
    <section class="bg-white border border-ink-200 mb-4 overflow-hidden" style="border-radius: 10px;">
      <header class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-base">📊</span>
          <h3 class="text-sm font-semibold text-ink-900">Progress</h3>
        </div>
        <button
          type="button"
          class="desk-save-btn text-xs"
          @click="fileProgressEntry"
        >+ File Progress Entry</button>
      </header>
      <div class="p-5">
        <div class="flex items-center gap-4">
          <div class="flex-1 h-2.5 bg-ink-100 overflow-hidden" style="border-radius: 999px;">
            <div
              class="h-full transition-all"
              :class="progressColor"
              :style="{ width: `${task.progress}%` }"
            />
          </div>
          <span class="text-2xl font-semibold text-ink-900 tabular-nums w-16 text-right">{{ task.progress }}%</span>
        </div>
        <div class="text-[11px] text-ink-500 mt-3">
          <template v-if="latestEntry">
            Latest:
            <DeskLink :to="`/app/progress-entries/${latestEntry.id}`">{{ latestEntry.progressPct }}% on {{ fmtDate(latestEntry.entryDate) }}</DeskLink>
            by <UserAvatar :user-id="latestEntry.enteredBy" size="xs" /> · {{ entryCount }} {{ entryCount === 1 ? 'entry' : 'entries' }} total
          </template>
          <template v-else>
            No progress entries filed yet — progress derives from the latest entry.
          </template>
        </div>
      </div>
    </section>

    <!-- ===== Two-column body: details on left, connections panel on right ===== -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2">
        <DeskSection title="Details">
          <DeskField label="Name">
            <div class="text-sm text-ink-900 py-1">{{ task.name }}</div>
          </DeskField>
          <DeskField label="Task Type" hint="Drives workflow.">
            <div class="py-1"><StatusBadge :status="task.task_type || 'Activity'" /></div>
          </DeskField>
          <DeskField label="Description">
            <div class="text-sm text-ink-700 py-1 whitespace-pre-line">{{ task.description || '—' }}</div>
          </DeskField>
          <DeskField label="Start">
            <div class="text-sm text-ink-900 py-1">{{ fmtDate(task.startDate) }}</div>
          </DeskField>
          <DeskField label="Due">
            <div class="text-sm text-ink-900 py-1">{{ fmtDate(task.endDate) }}</div>
          </DeskField>
        </DeskSection>
      </div>

      <!-- Connections panel — related records on the right -->
      <aside class="lg:col-span-1 space-y-2">
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Project</div>
          <DeskLink v-if="project" :to="`/app/projects/${project.id}`" class="text-sm font-medium">{{ project.name }}</DeskLink>
          <span v-else class="text-sm text-ink-500">—</span>
        </div>
        <div v-if="wp" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Work Package</div>
          <DeskLink :to="`/app/work-packages/${wp.id}`" class="text-sm font-medium">{{ wp.name }}</DeskLink>
        </div>
        <div v-if="activityType" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Activity Type</div>
          <DeskLink :to="`/app/activity-types/${activityType.id}`" class="text-sm font-medium">{{ activityType.name }}</DeskLink>
          <div class="text-[11px] text-ink-500 mt-0.5">{{ activityType.category }} · {{ activityType.expectedProductivityPerManDay }} {{ activityType.productivityUnit }}/man-day</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Assignee</div>
          <UserAvatar :user-id="task.assignee" :show-name="true" />
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Timeline</div>
          <div class="text-sm text-ink-700">{{ fmtDate(task.startDate) }} → {{ fmtDate(task.endDate) }}</div>
        </div>
        <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px;">
          <div class="flex items-center justify-between mb-1.5">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Recent entries</div>
            <DeskLink
              v-if="entryCount > 3"
              :to="{ path: '/app/progress-entries', query: { task: task.id } }"
              class="text-[10px]"
            >View all {{ entryCount }} →</DeskLink>
          </div>
          <ul v-if="recentEntries.length" class="space-y-1.5">
            <li v-for="e in recentEntries" :key="e.id" class="flex items-center justify-between gap-2 text-xs">
              <DeskLink :to="`/app/progress-entries/${e.id}`" class="font-medium tabular-nums">{{ e.progressPct }}%</DeskLink>
              <span class="text-ink-500 flex-1 truncate">{{ fmtDate(e.entryDate) }}</span>
              <UserAvatar :user-id="e.enteredBy" size="xs" />
              <span v-if="e.blockerFlag" class="text-danger-700" title="Blocker flagged">🚩</span>
            </li>
          </ul>
          <div v-else class="text-xs text-ink-400 italic">None yet</div>
        </div>
      </aside>
    </div>

    <!-- ===== Edit modal — opens via the title-row Edit button ===== -->
    <Teleport to="body">
      <div
        v-if="editing"
        class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
        @click.self="cancelEdit"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
          style="border-radius: 12px; max-height: calc(100vh - 3rem);"
          @click.stop
        >
          <!-- Modal header (pinned) -->
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900">Edit task</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ task.name }}</p>
            </div>
            <button
              type="button"
              class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
              aria-label="Close"
              @click="cancelEdit"
            >×</button>
          </header>

          <!-- Modal body — the only scrolling region -->
          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Details">
              <DeskField label="Name" required>
                <DeskInput v-model="form.name" />
              </DeskField>
              <DeskField
                label="Task Type"
                required
                hint="Activity = standard work with progress entries; Milestone = checkpoint with no qty progress; Inspection = pass/fail gate."
              >
                <DeskSelect v-model="form.task_type">
                  <option value="Activity">Activity</option>
                  <option value="Milestone">Milestone</option>
                  <option value="Inspection">Inspection</option>
                </DeskSelect>
              </DeskField>
              <DeskField label="Description">
                <DeskTextarea v-model="form.description" :rows="4" />
              </DeskField>
              <DeskField label="Start">
                <DeskInput v-model="form.startDate" type="date" />
              </DeskField>
              <DeskField label="Due">
                <DeskInput v-model="form.endDate" type="date" />
              </DeskField>
            </DeskSection>

            <DeskSection title="Assignment & status">
              <DeskField label="Assignee">
                <DeskSelect v-model="form.assignee">
                  <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }} — {{ m.role }}</option>
                </DeskSelect>
              </DeskField>
              <DeskField label="Status">
                <DeskSelect v-model="form.status">
                  <option>Open</option>
                  <option>In Progress</option>
                  <option>Completed</option>
                  <option>Cancelled</option>
                </DeskSelect>
              </DeskField>
              <DeskField label="Priority">
                <DeskSelect v-model="form.priority">
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                </DeskSelect>
              </DeskField>
            </DeskSection>
          </div>

          <!-- Modal footer (pinned) -->
          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
            <button
              type="button"
              class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
              style="border-radius: 6px;"
              @click="cancelEdit"
            >Cancel</button>
            <button
              type="button"
              class="desk-save-btn"
              @click="saveEdit"
            >Save</button>
          </footer>
        </div>
      </div>
    </Teleport>

    <!-- ===== File Progress Entry modal — opens via the "+ File Progress
         Entry" button in the Progress card header. Saves via
         store.addTaskProgressEntry which fires the recompute hook so the
         task home's Progress card updates immediately. ===== -->
    <Teleport to="body">
      <div
        v-if="filingProgress"
        class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
        @click.self="cancelProgressEntry"
      >
        <div
          class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
          style="border-radius: 12px; max-height: calc(100vh - 3rem);"
          @click.stop
        >
          <!-- Modal header (pinned) -->
          <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
            <div class="min-w-0 flex-1">
              <h2 class="text-sm font-semibold text-ink-900">File progress entry</h2>
              <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ task.name }} · currently {{ task.progress }}% · {{ task.status }}</p>
            </div>
            <button
              type="button"
              class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
              aria-label="Close"
              @click="cancelProgressEntry"
            >×</button>
          </header>

          <!-- Modal body — the only scrolling region -->
          <div class="p-5 overflow-y-auto flex-1">
            <DeskSection title="Progress" :cols="2">
              <DeskField label="Cumulative progress (%)" required hint="The NEW cumulative % after this entry — not a delta. 0–100." :error="progressErrors.progressPct">
                <DeskInput v-model="progressForm.progressPct" type="number" min="0" max="100" step="1" />
              </DeskField>
              <DeskField label="Entry date">
                <DeskInput v-model="progressForm.entryDate" type="date" />
              </DeskField>
              <DeskField label="Entered by">
                <DeskSelect v-model="progressForm.enteredBy">
                  <option v-for="m in store.team" :key="m.id" :value="m.id">{{ m.name }} — {{ m.role }}</option>
                </DeskSelect>
              </DeskField>
              <div class="md:col-span-2">
                <DeskField label="Narrative" hint="What was completed today? Any context worth recording?">
                  <DeskTextarea v-model="progressForm.narrative" :rows="3" placeholder="e.g. Bays 3-4 complete; 285 of 380 m² done. Cube test taken." />
                </DeskField>
              </div>
            </DeskSection>

            <DeskSection title="Labour deployed today" :cols="2">
              <DeskField label="Skilled labour" hint="Count of skilled workers on site today">
                <DeskInput v-model="progressForm.skilledLabour" type="number" />
              </DeskField>
              <DeskField label="Unskilled labour" hint="Count of unskilled workers / helpers">
                <DeskInput v-model="progressForm.unskilledLabour" type="number" />
              </DeskField>
            </DeskSection>

            <DeskSection title="Site conditions" :cols="2">
              <DeskField label="Weather" hint="Optional — only if it's worth recording.">
                <DeskSelect v-model="progressForm.weather">
                  <option value="">— No record —</option>
                  <option v-for="w in WEATHER_OPTIONS" :key="w" :value="w">{{ w }}</option>
                </DeskSelect>
              </DeskField>
              <DeskField label="Blocker">
                <label class="flex items-center gap-2 py-1 text-sm text-ink-700 cursor-pointer">
                  <input v-model="progressForm.blockerFlag" type="checkbox" class="h-3.5 w-3.5" />
                  Flag a blocker on this entry
                </label>
              </DeskField>
              <div v-if="progressForm.blockerFlag" class="md:col-span-2">
                <DeskField label="Blocker detail" required hint="What blocked progress today?" :error="progressErrors.blockerNote">
                  <DeskTextarea v-model="progressForm.blockerNote" :rows="2" placeholder="e.g. Afternoon shower delayed final bay by 2 hours" />
                </DeskField>
              </div>
            </DeskSection>

            <DeskSection title="Attachments" :cols="1">
              <input
                ref="progressFileInput"
                type="file"
                multiple
                class="hidden"
                @change="onProgressFilesPicked"
              />
              <input
                ref="progressCameraInput"
                type="file"
                accept="image/*"
                capture="environment"
                class="hidden"
                @change="onProgressFilesPicked"
              />
              <DeskField label="Files" hint="Site photos, QC reports, drawings — picked here and saved with the entry.">
                <div class="space-y-2 py-1">
                  <ul v-if="pendingAttachments.length" class="space-y-1.5">
                    <li
                      v-for="(att, idx) in pendingAttachments"
                      :key="idx"
                      class="flex items-center gap-2 px-2.5 py-1.5 bg-ink-50 border border-ink-200 text-xs"
                      style="border-radius: 6px;"
                    >
                      <img
                        v-if="att.mime?.startsWith('image/') && att.url"
                        :src="att.url"
                        class="w-8 h-8 object-cover flex-shrink-0"
                        style="border-radius: 4px;"
                        alt=""
                      />
                      <span v-else class="text-base leading-none">📎</span>
                      <span class="flex-1 min-w-0 truncate text-ink-800">{{ att.fileName }}</span>
                      <span class="text-[11px] text-ink-500 tabular-nums">{{ fmtBytes(att.size) }}</span>
                      <button
                        type="button"
                        class="text-ink-400 hover:text-danger-700 text-base leading-none"
                        aria-label="Remove"
                        @click="removePendingAttachment(idx)"
                      >×</button>
                    </li>
                  </ul>
                  <div class="flex items-center gap-2 flex-wrap">
                    <button
                      type="button"
                      class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 inline-flex items-center gap-1"
                      style="border-radius: 6px;"
                      @click="openProgressFilePicker"
                    >
                      <span class="text-sm leading-none">+</span>
                      <span>Attach file{{ pendingAttachments.length ? 's' : '' }}</span>
                    </button>
                    <button
                      type="button"
                      class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 inline-flex items-center gap-1.5"
                      style="border-radius: 6px;"
                      @click="openProgressCamera"
                    >
                      <span class="text-sm leading-none">📷</span>
                      <span>Capture photo</span>
                    </button>
                  </div>
                </div>
              </DeskField>
            </DeskSection>
          </div>

          <!-- Modal footer (pinned) -->
          <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
            <button
              type="button"
              class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
              style="border-radius: 6px;"
              @click="cancelProgressEntry"
            >Cancel</button>
            <button
              type="button"
              class="desk-save-btn"
              :disabled="savingProgress"
              @click="saveProgressEntry"
            >{{ savingProgress ? 'Filing…' : 'File entry' }}</button>
          </footer>
        </div>
      </div>
    </Teleport>
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">Task not found</div>
</template>
