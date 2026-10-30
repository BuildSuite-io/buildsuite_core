<script setup>
// The applied dynamic filters as removable chips (click a chip to edit it) plus a Clear link —
// drop it into a DeskList's #filter-chips slot next to any list-specific chips.
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import { __ } from "@/utils/translate";

defineProps({ filters: { type: Object, required: true } });
</script>

<template>
	<span
		v-for="(f, i) in filters.filters.value"
		:key="i"
		class="cursor-pointer"
		:title="__('Click to edit')"
		@click="filters.editFilter(i)"
	>
		<DeskFilterChip :label="filters.chipLabel(f)" @remove="filters.remove(i)" />
	</span>
	<button
		v-if="filters.filters.value.length"
		type="button"
		class="text-[11px] text-ink-500 hover:text-ink-800 px-1"
		@click="filters.clear()"
	>
		{{ __("Clear") }}
	</button>
</template>
