<script setup>
import DeskList from '@/components/desk/DeskList.vue'
import DeskLink from '@/components/desk/DeskLink.vue'

const props = defineProps({
  project:       { type: Object,  required: true },
  team:          { type: Array,   default: () => [] },
  teamCols:      { type: Array,   default: () => [] },
  hasCandidates: { type: Boolean, default: false },
})

const emit = defineEmits(['add', 'remove'])
</script>

<template>
  <div class="pt-4">
    <DeskList
      :rows="team"
      :columns="teamCols"
      row-key="id"
      :show-add-filter="false"
      :show-sort="false"
      :show-columns="false"
      :paginated="false"
    >
      <template #actions>
        <button
          type="button"
          class="desk-save-btn"
          :disabled="!hasCandidates"
          @click="emit('add')"
        >+ Add Member</button>
      </template>
      <template #cell-member="{ row }">
        <div class="flex items-center gap-2">
          <div :class="[row.color, 'w-6 h-6 rounded-full text-white flex items-center justify-center font-medium text-[10px]']">{{ row.initials }}</div>
          <span class="text-ink-900 text-sm">{{ row.name }}</span>
        </div>
      </template>
      <template #cell-role="{ row }">
        <span class="text-ink-700 text-sm">{{ row.role }}</span>
      </template>
      <template #cell-flag="{ row }">
        <div class="flex items-center justify-end gap-2">
          <span
            v-if="row.id === project.pm"
            class="text-[10px] font-medium px-1.5 py-0.5 bg-brand-50 text-brand-700"
            style="border-radius: 9999px;"
          >Project Manager</span>
          <button
            v-else
            type="button"
            class="text-xs px-2 py-0.5 border border-ink-200 bg-white hover:bg-danger-50 hover:border-danger-200 text-ink-500 hover:text-danger-700"
            style="border-radius: 6px;"
            :title="`Remove ${row.name} from this project`"
            @click.stop="emit('remove', row.id)"
          >Remove</button>
        </div>
      </template>
      <template #empty>
        <div class="text-sm text-ink-500">
          No team members yet.
          <button v-if="hasCandidates" type="button" class="desk-link" @click="emit('add')">Add the first one →</button>
        </div>
      </template>
    </DeskList>
  </div>
</template>
