<script setup>
import { ref } from 'vue'
import { useDataStore } from '@/stores'
import { createDataAdapter } from '@/data/adapters'
import { showToast } from '@/utils/appToast'
import FileUploadHandler from 'frappe-ui-file-upload-handler'
import DocTypeListView from '@/components/doctype/DocTypeListView.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { fmtDate } from '@/utils/format'

const props = defineProps({
  projectId: { type: String, required: true },
})
const emit = defineEmits(['count-change'])

const store = useDataStore()
const adapter = createDataAdapter(store)

const listRef = ref(null)
const uploadingCount = ref(0)
const fileInput = ref(null)

function fileIconFromRow(row) {
  const url = row?.file_url || row?.file_name || ''
  const ext = url.split('.').pop().toLowerCase().split('?')[0]
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return 'image'
  if (ext === 'pdf') return 'file-text'
  if (['dwg', 'dxf'].includes(ext)) return 'estimation'
  if (['doc', 'docx'].includes(ext)) return 'file-text'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'chart-line'
  if (['zip', 'rar', '7z'].includes(ext)) return 'archive'
  return 'file'
}

const FILE_COLUMNS = [
  {
    key: '__icon',
    label: '',
    preset: 'icon',
    fields: ['file_name', 'file_url'],
    iconFn: fileIconFromRow,
    align: 'center',
  },
  {
    key: 'file_name',
    label: 'File',
    align: 'left',
  },
  {
    key: 'file_size',
    label: 'Size',
    align: 'right',
  },
  {
    key: 'creation',
    label: 'Uploaded',
    align: 'left',
  },
  {
    key: 'owner',
    label: 'By',
    align: 'left',
  },
  {
    key: '__delete',
    label: '',
    fields: ['name', 'file_name'],
    align: 'center',
  },
]

function getBaseFilters() {
  return [
    ['attached_to_doctype', '=', 'Project'],
    ['attached_to_name', '=', props.projectId],
  ]
}

async function onFilesPicked(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  uploadingCount.value += files.length
  for (const file of files) {
    const handler = new FileUploadHandler()
    try {
      await handler.upload(file, {
        doctype: 'Project',
        docname: props.projectId,
        private: false,
      })
    } catch (err) {
      showToast(`Failed to upload ${file.name}`, 'error')
      console.error('upload failed:', err)
    } finally {
      uploadingCount.value--
    }
  }
  if (e.target) e.target.value = ''
  listRef.value?.reload()
}

const showDeleteConfirm = ref(false)
const deleteLoading = ref(false)
const pendingDelete = ref(null)

function promptDelete(name, fileName) {
  pendingDelete.value = { name, fileName }
  showDeleteConfirm.value = true
}

async function confirmDelete() {
  if (!pendingDelete.value) return
  deleteLoading.value = true
  try {
    await adapter.remove('File', pendingDelete.value.name)
    showDeleteConfirm.value = false
    pendingDelete.value = null
    listRef.value?.reload()
    showToast('Attachment deleted')
  } catch (err) {
    showToast('Failed to delete attachment', 'error')
    console.error('deleteFile failed:', err)
  } finally {
    deleteLoading.value = false
  }
}

function openFile(row) {
  if (!row?.file_url) return
  window.open(row.file_url, '_blank', 'noopener')
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
  return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + ' ' + units[i]
}
</script>

<template>
  <div class="pt-4">
    <input ref="fileInput" type="file" multiple class="hidden" @change="onFilesPicked" />

    <DocTypeListView
      ref="listRef"
      doctype="File"
      :field-order="['file_name', 'file_url', 'file_size', 'creation', 'owner']"
      :columns="FILE_COLUMNS"
      :base-filters="getBaseFilters()"
      :paginated="false"
      :page-length="200"
      initial-order-by="creation desc"
      search-placeholder="Search files…"
      empty-message="No attachments yet. Upload drawings, contracts, or site documents."
      @row-click="openFile"
      @count-change="emit('count-change', $event)"
    >
      <template #actions>
        <button
          type="button"
          class="desk-save-btn"
          :disabled="uploadingCount > 0"
          @click="fileInput?.click()"
        >{{ uploadingCount > 0 ? `Uploading… (${uploadingCount})` : '+ Upload' }}</button>
      </template>

      <template #cell-file_name="{ row }">
        <a
          v-if="row?.file_url"
          :href="row.file_url"
          target="_blank"
          rel="noopener"
          class="text-sm text-brand-700 hover:underline truncate block max-w-xs"
          :title="row.file_name"
          @click.stop
        >{{ row.file_name }}</a>
        <span v-else class="text-sm text-ink-700 truncate">{{ row.file_name }}</span>
      </template>

      <template #cell-file_size="{ row }">
        <span class="text-xs text-ink-600 tabular-nums">{{ formatFileSize(row?.file_size) }}</span>
      </template>

      <template #cell-creation="{ row }">
        <span class="text-xs text-ink-600">{{ fmtDate(row?.creation) }}</span>
      </template>

      <template #cell-owner="{ row }">
        <UserAvatar :user-id="row?.owner" :show-name="true" size="xs" />
      </template>

      <template #cell-__delete="{ row }">
        <button
          type="button"
          class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-danger-50 text-danger-700"
          style="border-radius: 4px;"
          :title="`Delete ${row?.file_name}`"
          @click.stop="promptDelete(row?.name, row?.file_name)"
        >✕</button>
      </template>
    </DocTypeListView>

    <ConfirmDialog
      v-model:open="showDeleteConfirm"
      title="Delete attachment"
      :message="pendingDelete ? `Delete '${pendingDelete.fileName}'? This cannot be undone.` : ''"
      confirm-label="Delete"
      :destructive="true"
      :loading="deleteLoading"
      @confirm="confirmDelete"
    />
  </div>
</template>
