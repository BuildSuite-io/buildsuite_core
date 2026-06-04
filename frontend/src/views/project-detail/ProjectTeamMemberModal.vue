<script setup>
import DeskField from '@/components/desk/DeskField.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'

defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  projectName: {
    type: String,
    default: '',
  },
  availableTeamCandidates: {
    type: Array,
    default: () => [],
  },
  teamPickUserId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'confirm', 'update:teamPickUserId'])
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
      @click.self="emit('close')"
    >
      <div
        class="bg-white border border-ink-200 w-full max-w-md shadow-fp-lg flex flex-col"
        style="border-radius: 12px;"
        @click.stop
      >
        <header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white" style="border-radius: 12px 12px 0 0;">
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-semibold text-ink-900">Add team member</h2>
            <p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ projectName }}</p>
          </div>
          <button
            type="button"
            class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
            aria-label="Close"
            @click="emit('close')"
          >x</button>
        </header>
        <div class="p-5">
          <div v-if="availableTeamCandidates.length">
            <DeskField label="User" hint="Pick from users not already on this project.">
              <DeskSelect
                :model-value="teamPickUserId"
                @update:model-value="(value) => emit('update:teamPickUserId', value)"
              >
                <option v-for="m in availableTeamCandidates" :key="m.id" :value="m.id">{{ m.name }} - {{ m.role }}</option>
              </DeskSelect>
            </DeskField>
          </div>
          <div v-else class="text-sm text-ink-500 italic">
            Every user is already on this project.
          </div>
        </div>
        <footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white" style="border-radius: 0 0 12px 12px;">
          <button
            type="button"
            class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
            style="border-radius: 6px;"
            @click="emit('close')"
          >Cancel</button>
          <button
            type="button"
            class="desk-save-btn"
            :disabled="!teamPickUserId"
            @click="emit('confirm')"
          >Add member</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
