<script setup>
// Not Found — unknown URL. Same wording whatever the cause, so the page never
// confirms whether a record exists. Card mirrors AccessDenied.vue.

import { RouterLink } from "vue-router";
</script>

<template>
	<div class="min-h-screen px-6 py-16 flex items-center justify-center">
		<div
			class="max-w-md w-full text-center bg-white border border-ink-200 rounded-2xl p-8 dark:bg-ink-900 dark:border-ink-700"
		>
			<div
				class="mx-auto w-14 h-14 rounded-2xl bg-brand-50 text-brand-700 flex items-center justify-center dark:bg-ink-800"
			>
				<svg
					class="w-7 h-7"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.7"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<circle cx="11" cy="11" r="7" />
					<path d="m21 21-4.3-4.3" />
					<path d="M8 11h6" />
				</svg>
			</div>

			<p class="mt-4 text-[11px] uppercase tracking-[0.18em] text-brand-700 font-semibold">
				404 · Not Found
			</p>
			<h1 class="mt-1 text-lg font-semibold text-ink-900 dark:text-ink-100">
				We couldn't find that page
			</h1>
			<p class="mt-2 text-sm text-ink-500 leading-6">
				The page or record doesn't exist, may have been deleted, or you don't have access
				to it.
			</p>

			<RouterLink to="/home" class="mt-6 inline-block desk-save-btn !text-sm !px-4 !py-2">
				Back to Home
			</RouterLink>
		</div>
	</div>
</template>
