<script setup>
// "1-8 of 8 records" under a bespoke table's card — the same line DeskList and DocTypeListView
// show, so every list reads the same whether or not it has the pager (DeskPaginationFooter only
// appears past the smallest page size). Pair it with usePagination(); place it after the card.
defineProps({
	// A reactive pager from usePagination().
	pager: { type: Object, required: true },
});
</script>

<template>
	<div data-test="list-count" class="mt-2 text-xs text-ink-500 tabular-nums">
		{{
			pager.totalRows
				? `${pager.rangeStart}-${pager.rangeEnd} of ${pager.totalRows} records`
				: "0 records"
		}}
	</div>
</template>
