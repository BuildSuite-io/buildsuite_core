<script setup>
/**
 * ConfirmDialog — reusable confirmation modal matching the app's desk modal chrome.
 *
 * Props:
 *   open        {Boolean}  v-model:open
 *   title       {String}   Dialog heading
 *   message     {String}   Body copy
 *   confirmLabel {String}  Confirm button label (default "Confirm")
 *   destructive {Boolean}  When true the confirm button uses danger colours (default false)
 *   loading     {Boolean}  Shows spinner on confirm button and disables both buttons
 */
defineProps({
  open:         { type: Boolean, required: true },
  title:        { type: String,  default: 'Are you sure?' },
  message:      { type: String,  default: '' },
  confirmLabel: { type: String,  default: 'Confirm' },
  destructive:  { type: Boolean, default: false },
  loading:      { type: Boolean, default: false },
})

const emit = defineEmits(['update:open', 'confirm'])

function close() { emit('update:open', false) }
function confirm() { emit('confirm') }
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 bg-ink-900/40 z-40 flex items-center justify-center p-6"
      @click.self="close"
    >
      <div
        class="bg-white border border-ink-200 w-full max-w-md shadow-fp-lg flex flex-col"
        style="border-radius: 12px;"
        @click.stop
      >
        <!-- Header -->
        <header
          class="px-5 py-3 border-b border-ink-200 flex items-center justify-between bg-white"
          style="border-radius: 12px 12px 0 0;"
        >
          <h2 class="text-sm font-semibold text-ink-900">{{ title }}</h2>
          <button
            type="button"
            class="text-ink-500 hover:text-ink-900 text-lg leading-none ml-3"
            aria-label="Close"
            :disabled="loading"
            @click="close"
          >×</button>
        </header>

        <!-- Body -->
        <div class="px-5 py-4 text-sm text-ink-700 leading-relaxed">
          {{ message }}
        </div>

        <!-- Footer -->
        <footer
          class="px-5 py-3 border-t border-ink-200 flex justify-end gap-2"
          style="border-radius: 0 0 12px 12px;"
        >
          <button
            type="button"
            class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 disabled:opacity-50"
            style="border-radius: 6px;"
            :disabled="loading"
            @click="close"
          >Cancel</button>
          <button
            type="button"
            class="text-xs px-3 py-1.5 border text-white disabled:opacity-50 flex items-center gap-1.5"
            style="border-radius: 6px;"
            :class="destructive
              ? 'border-danger-600 bg-danger-500 hover:bg-danger-600'
              : 'border-brand-600 bg-brand-600 hover:bg-brand-700'"
            :disabled="loading"
            @click="confirm"
          >
            <svg v-if="loading" class="animate-spin size-3" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/>
            </svg>
            {{ confirmLabel }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
