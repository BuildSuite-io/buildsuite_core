<script setup>
import DeskField from '@/components/desk/DeskField.vue'
import DeskLinkPicker from '@/components/desk/DeskLinkPicker.vue'
import { computed } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  projectName: { type: String, default: '' },
  // User ids already on the team (+ the PM) — excluded from the picker.
  excludeUsers: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['close', 'confirm', 'update:modelValue'])

// Exclude users already on the team; enabled users only.
const pickerFilters = computed(() => {
  const f = [['enabled', '=', 1]]
  if (props.excludeUsers.length) f.push(['name', 'not in', props.excludeUsers])
  return f
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
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
          <DeskField label="User" :error="error" hint="Pick a user to add to this project's team.">
            <DeskLinkPicker
              :model-value="modelValue"
              doctype="User"
              placeholder="Search users…"
              label-field="full_name"
              value-field="name"
              :search-fields="['full_name', 'name', 'email']"
              :filters="pickerFilters"
              order-by="full_name asc"
              :page-length="20"
              :error="error"
              @update:model-value="(value) => emit('update:modelValue', value)"
            />
          </DeskField>
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
            :disabled="!modelValue || saving"
            @click="emit('confirm')"
          >{{ saving ? 'Adding…' : 'Add member' }}</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
