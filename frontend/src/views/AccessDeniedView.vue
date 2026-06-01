<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const deniedReason = computed(() => {
  const reason = route.query.reason
  return typeof reason === 'string' && reason ? reason : 'missing_role'
})
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
      </div>

      <div class="mt-8 flex flex-wrap gap-3">
        <RouterLink
          to="/"
          class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium bg-brand-600 text-white rounded-md hover:bg-brand-700 transition-colors"
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
