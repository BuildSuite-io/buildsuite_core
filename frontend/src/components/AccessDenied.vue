<script setup>
import { RouterLink } from "vue-router";

// Branded in-page "no access" panel for record/section permission denials (a read
// returning 403). Distinct from the full-page AccessDeniedView route, which covers
// global app access. Render inside a view's body when isPermissionDenied(error).
defineProps({
	title: { type: String, default: "You don't have access to this" },
	message: {
		type: String,
		default:
			"Your account doesn't have permission to view this. Contact your administrator to request access.",
	},
	backTo: { type: String, default: "/" },
	backLabel: { type: String, default: "Back to Home" },
});
</script>

<template>
	<div class="px-6 py-16 flex items-center justify-center">
		<div
			class="max-w-md w-full text-center bg-white border border-ink-200 rounded-2xl p-8 dark:bg-ink-900 dark:border-ink-700"
		>
			<div
				class="mx-auto w-12 h-12 rounded-full bg-danger-50 text-danger-600 flex items-center justify-center dark:bg-ink-800"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.8"
						d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
					/>
				</svg>
			</div>
			<p class="mt-4 text-[11px] uppercase tracking-[0.18em] text-danger-700 font-semibold">
				No access
			</p>
			<h2 class="mt-1 text-lg font-semibold text-ink-900 dark:text-ink-100">{{ title }}</h2>
			<p class="mt-2 text-sm text-ink-500 leading-6">{{ message }}</p>
			<RouterLink
				:to="backTo"
				class="mt-6 inline-flex items-center justify-center px-4 py-2 text-sm font-medium border border-ink-300 text-ink-700 rounded-md hover:bg-ink-50 dark:border-ink-600 dark:text-ink-200"
			>
				{{ backLabel }}
			</RouterLink>
		</div>
	</div>
</template>
