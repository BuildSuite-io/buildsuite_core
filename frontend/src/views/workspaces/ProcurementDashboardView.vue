<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";

const today = computed(() =>
	new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
);
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<!-- Header strip — breadcrumb + date eyebrow + title -->
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1 flex items-center gap-2">
					<RouterLink to="/procurement" class="hover:text-brand-700"
						>Procurement</RouterLink
					>
					<span class="text-ink-300">/</span>
					<span>Dashboard</span>
					<span class="text-ink-300 mx-2">·</span>
					<span>{{ today }}</span>
				</div>
				<h1 class="text-2xl font-semibold text-ink-900">Procurement Dashboard</h1>
				<p class="text-xs text-ink-500 mt-1">
					Open material requests, on-order value, site receipts and rate variances at a
					glance.
				</p>
			</div>
		</div>
	</div>
</template>
