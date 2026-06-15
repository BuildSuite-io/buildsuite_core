// Promise-based confirmation dialog. A single <ConfirmDialog> is mounted in
// App.vue bound to this shared state; call useConfirm() anywhere to get a
// confirm() function that returns Promise<boolean>.
//
//   const confirmDialog = useConfirm()
//   const ok = await confirmDialog({ title, message, confirmLabel, destructive })
//   if (!ok) return
//
// Props mirror ConfirmDialog.vue (title / message / confirmLabel / destructive).
// Only one dialog is shown at a time; opening a new one settles any pending
// promise as false.

import { reactive } from 'vue'

const state = reactive({
  open: false,
  title: 'Are you sure?',
  message: '',
  confirmLabel: 'Confirm',
  destructive: false,
})

let resolver = null

function settle(result) {
  if (resolver) {
    const r = resolver
    resolver = null
    r(result)
  }
}

// Used by the host component (App.vue) to bind state + wire the buttons.
export function useConfirmState() {
  return {
    state,
    onConfirm() {
      state.open = false
      settle(true)
    },
    onCancel() {
      state.open = false
      settle(false)
    },
  }
}

// Used by call sites.
export function useConfirm() {
  return function confirm(opts = {}) {
    settle(false) // resolve any previous pending dialog as cancelled
    state.title = opts.title || 'Are you sure?'
    state.message = opts.message || ''
    state.confirmLabel = opts.confirmLabel || 'Confirm'
    state.destructive = !!opts.destructive
    state.open = true
    return new Promise((resolve) => { resolver = resolve })
  }
}
