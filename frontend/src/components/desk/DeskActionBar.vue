<script setup>
// The save bar that sits at the top of a Desk form (DeskForm puts it in a sticky
// region). Save button is Frappe blue, NOT brand green. Cancel sits to the left as a
// muted text link. Slots: `left` for additional left-side controls, `menu` for an
// Actions/Menu dropdown beside the save button.

defineProps({
  canSave: { type: Boolean, default: true },
  saving: { type: Boolean, default: false },
  savingLabel: { type: String, default: 'Saving…' },
  saveLabel: { type: String, default: 'Save' },
  cancelLabel: { type: String, default: 'Cancel' },
  showCancel: { type: Boolean, default: true },
  showSave: { type: Boolean, default: true },     // hide entirely for locked records with no workflow action
})
defineEmits(['save', 'cancel'])
</script>

<template>
  <div class="flex items-center justify-between gap-3 px-5 py-2 bg-white">
    <div class="flex items-center gap-3 min-w-0">
      <button
        v-if="showCancel"
        type="button"
        class="text-xs text-ink-600 hover:text-ink-900"
        @click="$emit('cancel')"
      >{{ cancelLabel }}</button>
      <slot name="left" />
    </div>
    <div class="flex items-center gap-2 flex-shrink-0">
      <slot name="menu" />
      <button
        v-if="showSave"
        type="button"
        class="desk-save-btn"
        :disabled="!canSave || saving"
        @click="$emit('save')"
      >{{ saving ? savingLabel : saveLabel }}</button>
    </div>
  </div>
</template>
