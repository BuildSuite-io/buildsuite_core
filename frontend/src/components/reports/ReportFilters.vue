<script setup>
// The filter strip every report sits under — one component so reports don't each invent
// their own bar: same chrome, same Clear affordance, plus the two things a filtered report
// must have — a live "N of M" count (so a narrowed report is never mistaken for the whole
// set) and a Clear that appears only when something is actually filtering. Reports pass
// their own controls through the default slot. print:hidden — a filter row is a control,
// not part of the printed document.
defineProps({
	active: { type: Boolean, default: false }, // true when ≥1 filter is set → Clear appears
	shown: { type: Number, default: null }, // rows currently shown
	total: { type: Number, default: null }, // rows before filtering
	noun: { type: String, default: "rows" },
});
defineEmits(["clear"]);
</script>

<template>
	<div
		class="bg-ink-50 border border-ink-200 px-3 py-2 mb-3 flex items-center gap-x-4 gap-y-2 flex-wrap print:hidden"
		style="border-radius: 6px"
	>
		<slot />

		<div class="ml-auto flex items-center gap-3">
			<span v-if="shown !== null" class="text-[11px] text-ink-500 tabular-nums">
				<template v-if="total !== null && shown !== total"
					>{{ shown }} of {{ total }} {{ noun }}</template
				>
				<template v-else>{{ shown }} {{ noun }}</template>
			</span>
			<button
				v-if="active"
				type="button"
				class="text-[11px] text-brand-700 hover:underline"
				@click="$emit('clear')"
			>
				Clear filters
			</button>
		</div>
	</div>
</template>
