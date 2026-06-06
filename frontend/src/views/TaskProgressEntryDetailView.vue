<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import { showToast } from '@/utils/appToast'
import { parseFrappeError } from '@/utils/frappeError'
import { toDateInputValue } from '@/utils/dateInput'
import UserAvatar from '@/components/UserAvatar.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskForm from '@/components/desk/DeskForm.vue'
import DeskActionBar from '@/components/desk/DeskActionBar.vue'
import DeskSection from '@/components/desk/DeskSection.vue'
import DeskField from '@/components/desk/DeskField.vue'
import DeskInput from '@/components/desk/DeskInput.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskTextarea from '@/components/desk/DeskTextarea.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import FileUploadHandler from 'frappe-ui-file-upload-handler'
import { fmtDate } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({ id: String })
const router = useRouter()
const store = useDataStore()
const adapter = createDataAdapter(store)

function firstResourceRow(resource) {
  if (resource?.doc) return resource.doc
  const raw = resource?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  if (raw && typeof raw === 'object' && 'value' in raw) return raw.value || null
  return raw || null
}

// ── Entry ────────────────────────────────────────────────────────────────────

const entryResource = ref(null)

function loadEntryResource() {
  if (!props.id) { entryResource.value = null; return }
  entryResource.value = adapter.read('Task Update', props.id, {
    nameField: 'name',
    fields: ['name', 'task', 'entry_date', 'cumulative_progress', 'skilled', 'unskilled', 'weather', 'blocker', 'blocker_detail', 'narrative', 'owner', 'creation'],
    cache: `buildsuite-task-update-detail:${props.id}`,
    transform(rows) {
      return rows.map(row => ({
        id:              row?.name || '',
        task:            row?.task || '',
        entryDate:       row?.entry_date || null,
        progressPct:     Number(row?.cumulative_progress) || 0,
        narrative:       row?.narrative || '',
        skilledLabour:   Number(row?.skilled) || 0,
        unskilledLabour: Number(row?.unskilled) || 0,
        weather:         row?.weather || '',
        blockerFlag:     !!Number(row?.blocker),
        blockerNote:     row?.blocker_detail || '',
        enteredBy:       row?.owner || '',
        createdAt:       row?.creation || null,
      }))
    },
  })
}

watch(() => props.id, loadEntryResource, { immediate: true })

const entry = computed(() => {
  const backendEntry = firstResourceRow(entryResource.value)
  if (backendEntry) return backendEntry
  const local = store.taskProgressEntries?.find(e => e.id === props.id || e.name === props.id)
  if (!local) return null
  return {
    id:              local.id,
    task:            local.taskId || local.task || '',
    entryDate:       local.entryDate || local.entry_date || null,
    progressPct:     Number(local.progressPct ?? local.progress_pct) || 0,
    narrative:       local.narrative || '',
    skilledLabour:   Number(local.skilledLabour ?? local.skilled_labour) || 0,
    unskilledLabour: Number(local.unskilledLabour ?? local.unskilled_labour) || 0,
    weather:         local.weather || '',
    blockerFlag:     !!(local.blockerFlag ?? local.blocker_flag),
    blockerNote:     local.blockerNote || local.blocker_note || '',
    enteredBy:       local.enteredBy || local.owner || '',
    createdAt:       local.createdAt || null,
  }
})

// ── Related records ──────────────────────────────────────────────────────────

const taskResource = ref(null)

function loadTaskResource(taskId) {
  if (!taskId) { taskResource.value = null; return }
  taskResource.value = adapter.read('Task', taskId, {
    fields: ['name', 'subject', 'project', 'work_package', 'status', 'progress'],
    transform(rows) {
      return rows.map(row => ({
        id:            row?.name || '',
        name:          row?.subject || row?.name || '',
        projectId:     row?.project || '',
        workPackageId: row?.work_package || '',
        status:        row?.status || '',
        progress:      Number(row?.progress) || 0,
      }))
    },
  })
}

watch(() => entry.value?.task, loadTaskResource, { immediate: true })
const task = computed(() => firstResourceRow(taskResource.value))

const projectResource = ref(null)

function loadProjectResource(projectId) {
  if (!projectId) { projectResource.value = null; return }
  projectResource.value = adapter.read('Project', projectId, {
    fields: ['name', 'project_name'],
    transform(rows) {
      return rows.map(row => ({
        id:   row?.name || '',
        name: row?.project_name || row?.name || '',
      }))
    },
  })
}

watch(() => task.value?.projectId, loadProjectResource, { immediate: true })
const project = computed(() => firstResourceRow(projectResource.value))

const wpResource = ref(null)

function loadWpResource(wpId) {
  if (!wpId) { wpResource.value = null; return }
  wpResource.value = adapter.read('Work Package', wpId, {
    fields: ['name', 'work_package_name'],
    transform(rows) {
      return rows.map(row => ({
        id:   row?.name || '',
        name: row?.work_package_name || row?.name || '',
      }))
    },
  })
}

watch(() => task.value?.workPackageId, loadWpResource, { immediate: true })
const wp = computed(() => firstResourceRow(wpResource.value))

// ── Latest-on-task check ─────────────────────────────────────────────────────

const latestEntriesResource = ref(null)

function loadLatestEntriesResource(taskId) {
  if (!taskId) { latestEntriesResource.value = null; return }
  latestEntriesResource.value = adapter.list('Task Update', {
    filters: [['task', '=', taskId]],
    fields: ['name', 'entry_date', 'cumulative_progress'],
    orderBy: 'entry_date desc',
    pageLength: 1,
    transform(rows) {
      return rows.map(row => ({
        id:          row?.name || '',
        entryDate:   row?.entry_date || null,
        progressPct: Number(row?.cumulative_progress) || 0,
      }))
    },
  })
}

watch(() => task.value?.id, loadLatestEntriesResource, { immediate: true })

const latestOnTask = computed(() => {
  const raw = latestEntriesResource.value?.data
  if (Array.isArray(raw)) return raw[0] || null
  if (Array.isArray(raw?.value)) return raw.value[0] || null
  return null
})
const isLatestOnTask = computed(() =>
  latestOnTask.value && entry.value && latestOnTask.value.id === entry.value.id
)

// ── Edit form ────────────────────────────────────────────────────────────────

const editing = ref(false)
const saving = ref(false)
const form = ref({})

function buildEntryForm(source) {
  if (!source) return {}
  return {
    entryDate:       toDateInputValue(source.entryDate),
    progressPct:     source.progressPct ?? 0,
    narrative:       source.narrative || '',
    skilledLabour:   source.skilledLabour ?? 0,
    unskilledLabour: source.unskilledLabour ?? 0,
    weather:         source.weather || '',
    blockerFlag:     !!source.blockerFlag,
    blockerNote:     source.blockerNote || '',
  }
}

watch(entry, (e) => { if (e && !editing.value) form.value = buildEntryForm(e) }, { immediate: true })

function startEdit() {
  if (entry.value) form.value = buildEntryForm(entry.value)
  editing.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    await adapter.update('Task Update', props.id, {
      entry_date:          form.value.entryDate,
      cumulative_progress: Number(form.value.progressPct),
      narrative:           form.value.narrative,
      skilled:             Number(form.value.skilledLabour) || 0,
      unskilled:           Number(form.value.unskilledLabour) || 0,
      weather:             form.value.weather,
      blocker:             form.value.blockerFlag ? 1 : 0,
      blocker_detail:      form.value.blockerNote,
    })
    editing.value = false
    entryResource.value?.reload?.()
    showToast('Progress entry updated')
  } catch (err) {
    showToast(parseFrappeError(err).summary ?? 'Failed to save progress entry', 'error')
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  if (entry.value) form.value = buildEntryForm(entry.value)
  editing.value = false
}

function onPrimary() {
  if (editing.value) saveEdit()
  else startEdit()
}

// ── Delete ───────────────────────────────────────────────────────────────────

const showDeleteConfirm = ref(false)
const deleteLoading = ref(false)

function deleteEntry() { showDeleteConfirm.value = true }

async function confirmDelete() {
  deleteLoading.value = true
  const taskId = entry.value?.task
  try {
    await adapter.remove('Task Update', props.id)
    showDeleteConfirm.value = false
    await router.push(taskId ? `/tasks/${taskId}` : '/progress-entries')
    await nextTick()
    showToast('Progress entry deleted')
  } catch (err) {
    showToast(parseFrappeError(err).summary ?? 'Failed to delete progress entry', 'error')
  } finally {
    deleteLoading.value = false
  }
}

// ── Attachments ──────────────────────────────────────────────────────────────

const attachmentsResource = ref(null)
const uploadingCount = ref(0)
const attachFileInput = ref(null)

function loadAttachmentsResource(entryId) {
  if (!entryId) { attachmentsResource.value = null; return }
  attachmentsResource.value = adapter.list('File', {
    filters: [
      ['attached_to_doctype', '=', 'Task Update'],
      ['attached_to_name',    '=', entryId],
    ],
    fields: ['name', 'file_name', 'file_url', 'file_size', 'is_private', 'creation', 'owner'],
    orderBy: 'creation desc',
  })
}

watch(() => entry.value?.id, loadAttachmentsResource, { immediate: true })

const attachedFiles = computed(() => {
  const raw = attachmentsResource.value?.data
  if (Array.isArray(raw)) return raw
  if (Array.isArray(raw?.value)) return raw.value
  return []
})

async function onAttachFilesPicked(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploadingCount.value += files.length
  for (const file of files) {
    const handler = new FileUploadHandler()
    try {
      await handler.upload(file, {
        doctype: 'Task Update',
        docname: props.id,
        private: true,
      })
    } catch (err) {
      showToast(`Failed to upload ${file.name}`, 'error')
      console.error('upload failed:', err)
    } finally {
      uploadingCount.value--
    }
  }
  attachmentsResource.value?.reload?.()
  if (e.target) e.target.value = ''
}

const showFileDeleteConfirm = ref(false)
const fileDeleteLoading = ref(false)
const pendingFileDelete = ref(null)

function deleteFile(fileId, fileName) {
  pendingFileDelete.value = { id: fileId, name: fileName }
  showFileDeleteConfirm.value = true
}

async function confirmFileDelete() {
  if (!pendingFileDelete.value) return
  fileDeleteLoading.value = true
  try {
    await adapter.remove('File', pendingFileDelete.value.id)
    showFileDeleteConfirm.value = false
    pendingFileDelete.value = null
    attachmentsResource.value?.reload?.()
    showToast('Attachment deleted')
  } catch (err) {
    showToast('Failed to delete attachment', 'error')
    console.error('deleteFile failed:', err)
  } finally {
    fileDeleteLoading.value = false
  }
}

function fileIcon(url) {
  const ext = (url || '').split('.').pop().toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return 'image'
  if (ext === 'pdf') return 'file-text'
  if (['dwg', 'dxf'].includes(ext)) return 'estimation'
  if (['doc', 'docx'].includes(ext)) return 'file-text'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'chart-line'
  if (['zip', 'rar', '7z'].includes(ext)) return 'archive'
  return 'file'
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0, n = bytes
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
  return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + ' ' + units[i]
}

// ── Display helpers ──────────────────────────────────────────────────────────

const WEATHER_OPTIONS = ['Clear', 'Rainy', 'Hot', 'Cold', 'Storm']
const WEATHER_ICON = { Clear: '☀️', Rainy: '🌧️', Hot: '🌡️', Cold: '❄️', Storm: '⛈️' }

const deleteMessage = computed(() => isLatestOnTask.value
  ? `Delete this entry? It's the latest on the task — the task's progress will revert to the previous entry (or 0% if this is the only one).`
  : `Delete this entry? It's a historical entry; the task's current progress will not change.`
)

const breadcrumbs = computed(() => {
  const out = [
    { label: 'BuildSuite Core', to: '/' },
    { label: 'Task Progress Entry', to: '/progress-entries' },
  ]
  if (task.value) out.push({ label: task.value.name, to: `/tasks/${task.value.id}` })
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
  : ''
)
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
          :save-label="editing ? (saving ? 'Saving…' : 'Save') : 'Edit'"
          :show-cancel="editing"
          cancel-label="Cancel"
          @save="onPrimary"
          @cancel="cancelEdit"
        >
          <template #left>
            <span v-if="!isLatestOnTask && latestOnTask" class="text-[11px] text-ink-500">
              ⚠ Older entry — task's current progress is
              <DeskLink :to="`/progress-entries/${latestOnTask.id}`" class="font-medium">
                {{ latestOnTask.progressPct }}% ({{ latestOnTask.id }})
              </DeskLink>
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

      <!-- 2-col body: main details left, Connections right -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2">

          <!-- Progress section — view mode -->
          <DeskSection v-if="!editing" title="Progress">
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

          <!-- Progress section — edit mode -->
          <DeskSection v-else title="Progress">
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

          <!-- Labour section — view mode -->
          <DeskSection v-if="!editing" title="Labour deployed today" :cols="2">
            <DeskField label="Skilled labour">
              <div class="text-sm text-ink-900 py-1 tabular-nums">{{ entry.skilledLabour || 0 }}</div>
            </DeskField>
            <DeskField label="Unskilled labour">
              <div class="text-sm text-ink-900 py-1 tabular-nums">{{ entry.unskilledLabour || 0 }}</div>
            </DeskField>
          </DeskSection>

          <!-- Labour section — edit mode -->
          <DeskSection v-else title="Labour deployed today" :cols="2">
            <DeskField label="Skilled labour" hint="Count of skilled workers on site today">
              <DeskInput v-model="form.skilledLabour" type="number" />
            </DeskField>
            <DeskField label="Unskilled labour" hint="Count of unskilled workers / helpers">
              <DeskInput v-model="form.unskilledLabour" type="number" />
            </DeskField>
          </DeskSection>

          <!-- Site conditions — view mode -->
          <DeskSection v-if="!editing" title="Site conditions" :cols="2">
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

          <!-- Site conditions — edit mode -->
          <DeskSection v-else title="Site conditions" :cols="2">
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

          <!-- Attachments -->
          <DeskSection title="Attachments">
            <div class="md:col-span-2">
              <div v-if="attachedFiles.length" class="bg-white border border-ink-200 mb-3" style="border-radius: 6px;">
                <div class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
                     style="grid-template-columns: 24px 1fr 70px 32px;">
                  <div></div>
                  <div class="px-3 py-1.5">File</div>
                  <div class="px-3 py-1.5 text-right">Size</div>
                  <div></div>
                </div>
                <div
                  v-for="f in attachedFiles"
                  :key="f.name"
                  class="grid hover:bg-brand-50 border-b border-ink-100 last:border-b-0 items-center"
                  style="grid-template-columns: 24px 1fr 70px 32px;"
                >
                  <div class="px-1 py-2 text-center">
                    <svg class="w-3.5 h-3.5 text-ink-400 mx-auto" viewBox="0 0 24 24" fill="none"
                         stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
                         stroke-linejoin="round" v-html="getWorkspaceIconPath(fileIcon(f.file_url))" />
                  </div>
                  <div class="px-3 py-2 min-w-0">
                    <a :href="f.file_url" target="_blank" rel="noopener"
                       class="text-xs text-brand-700 hover:underline truncate block">{{ f.file_name }}</a>
                  </div>
                  <div class="px-3 py-2 text-right text-xs text-ink-500 tabular-nums">{{ formatFileSize(f.file_size) }}</div>
                  <div class="px-1 py-2 flex justify-center">
                    <button
                      type="button"
                      class="text-xs px-1 py-0.5 border border-ink-200 bg-white hover:bg-danger-50 text-danger-700"
                      style="border-radius: 4px;"
                      @click="deleteFile(f.name, f.file_name)"
                    >✕</button>
                  </div>
                </div>
              </div>

              <input ref="attachFileInput" type="file" multiple class="hidden" @change="onAttachFilesPicked" />
              <button
                type="button"
                class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
                style="border-radius: 6px;"
                :disabled="uploadingCount > 0"
                @click="attachFileInput?.click()"
              >{{ uploadingCount > 0 ? `Uploading… (${uploadingCount})` : '+ Attach file' }}</button>
            </div>
          </DeskSection>

        </div>

        <!-- Connections panel -->
        <aside class="lg:col-span-1 space-y-2">
          <div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Task</div>
            <DeskLink v-if="task" :to="`/tasks/${task.id}`" class="text-sm font-medium">{{ task.name }}</DeskLink>
            <span v-else class="text-sm text-ink-500">—</span>
            <div v-if="task" class="text-[11px] text-ink-500 mt-1">
              Currently {{ task.progress }}% · {{ task.status }}
            </div>
          </div>
          <div v-if="project" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Project</div>
            <DeskLink :to="`/projects/${project.id}`" class="text-sm font-medium">{{ project.name }}</DeskLink>
          </div>
          <div v-if="wp" class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px;">
            <div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">Work Package</div>
            <DeskLink :to="`/work-packages/${wp.id}`" class="text-sm font-medium">{{ wp.name }}</DeskLink>
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
            <span>📎</span><span>Attachments — <span class="font-medium text-ink-700">{{ attachedFiles.length }}</span></span>
          </div>
          <div class="flex items-center gap-1.5">
            <span>👥</span><span>Entered by —</span>
            <UserAvatar :user-id="entry.enteredBy" size="xs" />
          </div>
        </div>
      </section>
    </DeskForm>

    <ConfirmDialog
      v-model:open="showDeleteConfirm"
      title="Delete progress entry"
      :message="deleteMessage"
      confirm-label="Delete"
      :destructive="true"
      :loading="deleteLoading"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model:open="showFileDeleteConfirm"
      title="Delete attachment"
      :message="pendingFileDelete ? `Delete '${pendingFileDelete.name}'? This cannot be undone.` : ''"
      confirm-label="Delete"
      :destructive="true"
      :loading="fileDeleteLoading"
      @confirm="confirmFileDelete"
    />
  </DeskPage>

  <div v-else class="px-6 py-20 text-center text-sm text-ink-400">Progress entry not found.</div>
</template>
