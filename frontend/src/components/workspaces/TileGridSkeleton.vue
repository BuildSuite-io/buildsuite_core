<script setup>
// Loading placeholder for a workspace tile grid (shortcuts / reports / records).
// Mirrors the <WorkspaceShortcut> tile shape — icon square + label line (+ optional
// description line) — and the same 3-up responsive grid, so content swaps in without
// layout shift. Pure pulse, matching the animate-pulse idiom already used in InsightsView.
import { computed } from "vue";

const props = defineProps({
	// How many placeholder tiles to render (roughly the count you expect back).
	count: { type: Number, default: 3 },
	// Show the second (description) line — reports/records tiles carry subtext; bare
	// shortcut tiles don't.
	withDescription: { type: Boolean, default: false },
});

const tiles = computed(() => Array.from({ length: Math.max(1, props.count) }, (_, i) => i));
</script>

<template>
	<div
		class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
		role="status"
		aria-busy="true"
		aria-live="polite"
	>
		<span class="sr-only">Loading…</span>
		<div
			v-for="i in tiles"
			:key="i"
			class="bg-white border border-ink-200 p-4"
			style="border-radius: 8px"
			aria-hidden="true"
		>
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-lg bg-ink-100 animate-pulse flex-shrink-0"></div>
				<div class="flex-1 min-w-0">
					<div class="h-3 rounded bg-ink-100 animate-pulse" style="width: 45%"></div>
					<div
						v-if="withDescription"
						class="h-2.5 rounded bg-ink-100 animate-pulse mt-2"
						style="width: 75%"
					></div>
				</div>
			</div>
		</div>
	</div>
</template>
