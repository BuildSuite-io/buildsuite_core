<script setup>
import { onMounted, watch } from 'vue'
import { useDataStore } from '@/stores'
import { useSessionStore } from '@/stores/session'
import { personaIdFromName, personaIdFromRoles } from '@/data/roles'
import { toasts } from '@/utils/appToast'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useConfirmState } from '@/composables/useConfirm'

const { state: confirmState, onConfirm, onCancel } = useConfirmState()

const store = useDataStore()
const session = useSessionStore()

onMounted(() => {
  store.hydrate()
  // Set the active persona from the logged-in user (real persona wins over any
  // persisted switcher choice). The switcher remains usable for previewing other
  // personas within the session; the backend is the authoritative gate.
  const personaId = personaIdFromName(session.access?.persona)
    || personaIdFromRoles(session.access?.roles)
  if (personaId) store.setRole(personaId)
})

// Apply the `dark` class on <html> based on store.theme. Watch immediate so
// the class lands on first paint after hydrate; subsequent flips persist via
// store.setTheme which writes to localStorage.
function applyThemeClass(theme) {
  const root = document.documentElement
  if (theme === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}
watch(() => store.theme, (t) => applyThemeClass(t), { immediate: true })
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>

  <!-- App-level toast notifications (bottom-right) -->
  <Teleport to="body">
    <div class="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-center gap-2.5 rounded-lg px-4 py-2.5 shadow-fp-md text-sm font-medium min-w-[240px] max-w-[360px]"
          :class="{
            'bg-ink-800 text-white':          t.type === 'success',
            'bg-danger-500 text-white':        t.type === 'error',
            'bg-warning-500 text-ink-900':     t.type === 'warning',
            'bg-info-500 text-white':          t.type === 'info',
          }"
        >
          <span class="flex-1">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>

  <!-- App-level confirmation dialog driven by useConfirm() -->
  <ConfirmDialog
    :open="confirmState.open"
    :title="confirmState.title"
    :message="confirmState.message"
    :confirm-label="confirmState.confirmLabel"
    :destructive="confirmState.destructive"
    @confirm="onConfirm"
    @update:open="(v) => { if (!v) onCancel() }"
  />
</template>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.toast-enter-active, .toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
