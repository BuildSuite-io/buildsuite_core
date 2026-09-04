import { computed, reactive, ref, unref, watch } from "vue";

/**
 * Client-side pager for BESPOKE tables — the finance/expense/petty-cash panels render raw
 * <table>s rather than <DeskList>, so they don't get DeskList's built-in pagination. Feed this
 * the full (already filtered/sorted) row array; render `pager.pagedRows` and drop a
 * <DeskPaginationFooter :pager="pager" /> under the table.
 *
 * @param {import('vue').Ref<Array>|Function|Array} rowsRef  ref, getter, or array of all rows.
 * @param {{pageSize?: number, pageSizeOptions?: number[]}} opts
 * @returns reactive pager: { page, pageSize, pageSizeOptions, pagedRows, totalRows, totalPages,
 *          rangeStart, rangeEnd, showPagination, prev(), next(), setPageSize(v) }
 */
export function usePagination(rowsRef, opts = {}) {
	const initialSize = opts.pageSize || 10;
	const pageSizeOptions = opts.pageSizeOptions || [10, 20, 50, 100];

	const page = ref(1);
	const size = ref(initialSize);
	const rows = computed(() => unref(rowsRef) || []);
	const totalRows = computed(() => rows.value.length);
	const totalPages = computed(() => Math.max(1, Math.ceil(totalRows.value / size.value)));
	const pagedRows = computed(() => {
		const start = (page.value - 1) * size.value;
		return rows.value.slice(start, start + size.value);
	});
	const rangeStart = computed(() => (totalRows.value === 0 ? 0 : (page.value - 1) * size.value + 1));
	const rangeEnd = computed(() =>
		Math.min(rangeStart.value + pagedRows.value.length - 1, totalRows.value),
	);
	// Only worth showing once there's more than the smallest page size worth of rows.
	const showPagination = computed(() => totalRows.value > Math.min(...pageSizeOptions));

	// When the row set shrinks (filter / search / tab switch), never leave the view stranded
	// past the last page.
	watch(totalPages, (tp) => {
		if (page.value > tp) page.value = tp;
	});

	return reactive({
		page,
		pageSize: size,
		pageSizeOptions,
		pagedRows,
		totalRows,
		totalPages,
		rangeStart,
		rangeEnd,
		showPagination,
		prev() {
			if (page.value > 1) page.value -= 1;
		},
		next() {
			if (page.value < totalPages.value) page.value += 1;
		},
		setPageSize(v) {
			size.value = Number(v) || initialSize;
			page.value = 1;
		},
	});
}
