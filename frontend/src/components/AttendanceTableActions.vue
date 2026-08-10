<script setup>
// The buttons above the Employee List, shared by both attendance forms.

defineProps({
	hasProject: { type: Boolean, default: false },
	rosterToAdd: { type: Number, default: 0 },
	rosterTitle: { type: String, default: "" },
});
defineEmits(["add-roster", "open-bulk", "add-row"]);
</script>

<template>
	<div class="flex items-center gap-2">
		<button
			v-if="hasProject"
			type="button"
			class="text-xs px-2.5 py-1.5 border border-brand-200 bg-brand-50 hover:bg-brand-100 text-brand-700 rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed"
			:disabled="!rosterToAdd"
			:title="rosterTitle"
			@click="$emit('add-roster')"
		>
			+ Project roster ({{ rosterToAdd }})
		</button>
		<button
			type="button"
			class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
			@click="$emit('open-bulk')"
		>
			Bulk Select
		</button>
		<button
			type="button"
			class="text-xs text-brand-700 hover:underline"
			@click="$emit('add-row')"
		>
			+ Add Row
		</button>
	</div>
</template>
