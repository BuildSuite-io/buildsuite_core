<script setup>
import { ref } from 'vue'
import { useDataStore } from '@/stores'
import UserAvatar from '@/components/UserAvatar.vue'
import { fmtDate } from '@/utils/format'
import { getWorkspaceIconPath } from '@/utils/workspaceIcons'

const props = defineProps({
  projectId:   { type: String, required: true },
  attachments: { type: Array,  default: () => [] },
})

const store = useDataStore()
const fileInput = ref(null)

function openFilePicker() { fileInput.value?.click() }

function onFilesPicked(e) {
  const files = Array.from(e.target.files || [])
  for (const f of files) {
    const url = URL.createObjectURL(f)
    store.addAttachment({
      parentDoctype: 'Project',
      parentId: props.projectId,
      fileName: f.name,
      mime: f.type || 'application/octet-stream',
      size: f.size,
      url,
    })
  }
  if (e.target) e.target.value = ''
}

function openAttachment(att) {
  if (!att.url) {
    alert('Seed sample — no actual file attached. Upload a real file to test the open-in-new-tab flow.')
    return
  }
  window.open(att.url, '_blank', 'noopener')
}

function deleteAttachment(att) {
  if (!confirm(`Delete "${att.fileName}"?`)) return
  store.deleteAttachment(att.id)
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = bytes
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
  return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + ' ' + units[i]
}

function fileIcon(mime) {
  if (!mime) return 'file'
  if (mime.startsWith('image/')) return 'image'
  if (mime === 'application/pdf') return 'file-text'
  if (mime.includes('acad') || mime.includes('dwg')) return 'estimation'
  if (mime.includes('word') || mime.includes('document')) return 'file-text'
  if (mime.includes('sheet') || mime.includes('excel')) return 'chart-line'
  if (mime.includes('zip') || mime.includes('compress')) return 'archive'
  return 'file'
}
</script>

<template>
  <div class="pt-4">
    <input ref="fileInput" type="file" multiple class="hidden" @change="onFilesPicked" />

    <div v-if="attachments.length" class="bg-white border border-ink-200" style="border-radius: 8px;">
      <!-- Action bar -->
      <div class="border-b border-ink-200 px-3 py-2 flex items-center gap-2 flex-wrap">
        <div class="text-xs text-ink-500">
          <span class="text-ink-900 font-medium">{{ attachments.length }} {{ attachments.length === 1 ? 'file' : 'files' }}</span>
          · drawings, contracts, sanctioned plans, site documents
        </div>
        <div class="ml-auto">
          <button type="button" class="desk-save-btn" @click="openFilePicker">+ Upload</button>
        </div>
      </div>
      <!-- Header row -->
      <div
        class="grid bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
        style="grid-template-columns: 28px minmax(220px, 2fr) 80px 110px 130px 32px;"
      >
        <div></div>
        <div class="px-3 py-1.5">File</div>
        <div class="px-3 py-1.5 text-right">Size</div>
        <div class="px-3 py-1.5">Uploaded</div>
        <div class="px-3 py-1.5">By</div>
        <div></div>
      </div>
      <!-- Rows -->
      <div
        v-for="att in attachments"
        :key="att.id"
        class="grid desk-row-stripe hover:bg-brand-50 border-b border-ink-100 last:border-b-0 items-center text-sm"
        style="grid-template-columns: 28px minmax(220px, 2fr) 80px 110px 130px 32px;"
      >
        <div class="px-2 py-2 text-center">
          <svg class="w-4 h-4 text-ink-500 mx-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath(fileIcon(att.mime))" />
        </div>
        <div class="px-3 py-2">
          <button
            type="button"
            class="text-left text-sm text-ink-900 hover:underline truncate w-full"
            :title="att.fileName"
            @click="openAttachment(att)"
          >{{ att.fileName }}</button>
          <div v-if="!att.url" class="text-[10px] text-ink-400 italic mt-0.5">metadata only</div>
        </div>
        <div class="px-3 py-2 text-right text-xs text-ink-600 tabular-nums">{{ formatFileSize(att.size) }}</div>
        <div class="px-3 py-2 text-xs text-ink-600">{{ fmtDate(att.uploadedAt) }}</div>
        <div class="px-3 py-2">
          <UserAvatar :user-id="att.uploadedBy" :show-name="true" size="xs" />
        </div>
        <div class="px-1 py-2 flex justify-center">
          <button
            type="button"
            class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-ink-50 text-danger-700"
            style="border-radius: 2px;"
            :title="`Delete ${att.fileName}`"
            @click="deleteAttachment(att)"
          >✕</button>
        </div>
      </div>
    </div>

    <div v-else class="py-8 text-center">
      <div class="text-sm text-ink-500 mb-2">No attachments yet.</div>
      <div class="text-xs text-ink-400 italic mb-4">Drawings, contracts, and site documents go here.</div>
      <button type="button" class="desk-save-btn" @click="openFilePicker">+ Upload first file</button>
    </div>
  </div>
</template>
