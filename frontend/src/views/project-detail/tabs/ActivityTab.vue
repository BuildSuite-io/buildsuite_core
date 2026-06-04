<script setup>
import UserAvatar from '@/components/UserAvatar.vue'
import { fmtDate } from '@/utils/format'
import { useDataStore } from '@/stores'

const props = defineProps({
  project: { type: Object, required: true }
})

const store = useDataStore()
</script>

<template>
  <div class="pt-4">
    <div class="bg-white border border-ink-200 p-4" style="border-radius: 2px;">
      <div class="flex gap-3 text-sm">
        <UserAvatar :user-id="store.user?.id || 'USR-001'" size="sm" />
        <div>
          <div class="text-ink-700">Project created</div>
          <div class="text-xs text-ink-400 mt-0.5">{{ fmtDate(project.createdAt) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
