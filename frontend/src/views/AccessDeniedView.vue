<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const { access } = storeToRefs(sessionStore)

const checkingAccess = ref(false)

const deniedReason = computed(() => {
  const reason = route.query.reason
  return typeof reason === 'string' && reason ? reason : 'missing_role'
})

const blockedPath = computed(() => {
  const target = route.query.target
  return typeof target === 'string' && target ? target : '/app'
})

async function retryAccess() {
  checkingAccess.value = true
  try {
    const latest = await sessionStore.recheckAccess()
    if (latest.allowed) {
      router.replace(blockedPath.value)
    }
  } finally {
    checkingAccess.value = false
  }
}
</script>

<template>
  <section class="min-h-screen bg-ink-50 flex items-center justify-center px-6 py-16">
    <div class="max-w-2xl w-full bg-white border border-ink-200 rounded-2xl shadow-fp-sm p-8 md:p-10">
      <p class="text-[11px] uppercase tracking-[0.18em] text-danger-700 font-semibold">BuildSuite Access</p>
      <h1 class="mt-2 text-2xl md:text-3xl font-semibold text-ink-900">You do not have permission to open this workspace</h1>
      <p class="mt-3 text-sm text-ink-600 leading-6">
        Your account is authenticated, but backend access checks blocked this route.
        Contact your administrator to request BuildSuite Core roles.
      </p>

      <div class="mt-6 bg-ink-50 border border-ink-200 rounded-lg p-4">
        <p class="text-xs text-ink-500">Access check reason</p>
        <p class="mt-1 text-sm font-medium text-ink-800">{{ deniedReason }}</p>
        <p class="mt-3 text-xs text-ink-500">Target route</p>
        <p class="mt-1 text-sm font-medium text-ink-800 break-all">{{ blockedPath }}</p>
      </div>

      <div class="mt-4 bg-ink-50 border border-ink-200 rounded-lg p-4">
        <p class="text-xs text-ink-500">Required access</p>
        <p class="mt-1 text-sm font-medium text-ink-800">System Manager role</p>
        <p class="mt-3 text-xs text-ink-500">Your roles</p>
        <p class="mt-1 text-sm text-ink-700 break-all">{{ (access.roles || []).join(', ') || 'None reported' }}</p>
      </div>

      <div class="mt-8 flex flex-wrap gap-3">
        <button
          type="button"
          class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium bg-brand-600 text-white rounded-md hover:bg-brand-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="checkingAccess"
          @click="retryAccess"
        >
          {{ checkingAccess ? 'Rechecking access...' : 'Retry Access Check' }}
        </button>
        <RouterLink
          to="/"
          class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium border border-ink-300 text-ink-700 rounded-md hover:bg-ink-100 transition-colors"
        >
          Go to Home
        </RouterLink>
        <a
          href="/app"
          class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium border border-ink-300 text-ink-700 rounded-md hover:bg-ink-100 transition-colors"
        >
          Open Frappe Desk
        </a>
      </div>
    </div>
  </section>
</template>
