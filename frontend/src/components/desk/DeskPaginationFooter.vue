<!--
  Pagination footer for bespoke tables, paired with usePagination(). Visually identical to the
  footer DeskList renders, so paginated raw <table>s match the built-in lists.
-->
<script setup>
defineProps({
	// A reactive pager from usePagination().
	pager: { type: Object, required: true },
});
</script>

<template>
	<div
		v-if="pager.showPagination"
		class="border-t border-ink-200 px-3 py-2 flex items-center gap-3 flex-wrap text-xs text-ink-600"
	>
		<div class="flex items-center gap-2">
			<span class="text-ink-500">Rows per page</span>
			<select
				data-test="pager-size"
				:value="pager.pageSize"
				class="text-xs border border-ink-200 bg-white text-ink-700 hover:bg-ink-50 cursor-pointer"
				style="border-radius: 6px; padding: 4px 8px"
				@change="pager.setPageSize($event.target.value)"
			>
				<option v-for="opt in pager.pageSizeOptions" :key="opt" :value="opt">
					{{ opt }}
				</option>
			</select>
		</div>

		<div class="text-ink-500 tabular-nums">
			Showing
			<span class="text-ink-800 font-medium">{{ pager.rangeStart }}–{{ pager.rangeEnd }}</span> of
			<span class="text-ink-800 font-medium">{{ pager.totalRows }}</span>
		</div>

		<div class="ml-auto flex items-center gap-1">
			<button
				type="button"
				data-test="pager-prev"
				class="text-xs text-ink-700 hover:bg-ink-50 disabled:text-ink-300 disabled:hover:bg-transparent disabled:cursor-not-allowed border border-ink-200 bg-white"
				style="border-radius: 6px; padding: 4px 10px"
				:disabled="pager.page <= 1"
				@click="pager.prev()"
			>
				‹ Prev
			</button>
			<span class="text-ink-500 tabular-nums px-2">
				Page <span class="text-ink-800 font-medium">{{ pager.page }}</span> of
				<span class="text-ink-800 font-medium">{{ pager.totalPages }}</span>
			</span>
			<button
				type="button"
				data-test="pager-next"
				class="text-xs text-ink-700 hover:bg-ink-50 disabled:text-ink-300 disabled:hover:bg-transparent disabled:cursor-not-allowed border border-ink-200 bg-white"
				style="border-radius: 6px; padding: 4px 10px"
				:disabled="pager.page >= pager.totalPages"
				@click="pager.next()"
			>
				Next ›
			</button>
		</div>
	</div>
</template>
