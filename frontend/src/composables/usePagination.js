import { computed, reactive, ref, watch } from "vue";

// Client-side pagination over a reactive rows ref — for the bespoke finance tables
// (Expenses / Payments / Bank & Cash Accounts) that render their own <table> instead of
// DeskList. Mirrors DeskList's footer semantics so pagination looks and behaves the same.
//
// Returns a reactive `pager`: render `pager.pagedRows` in the table and drop
// <DeskPaginationFooter :pager="pager" /> below it.
export function usePagination(rowsRef, initialPageSize = 10) {
	const page = ref(1);
	const pageSize = ref(initialPageSize);

	const total = computed(() => (rowsRef.value || []).length);
	const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));

	// Keep the current page in range as the underlying rows change (filtering, tab switch).
	watch([total, pageSize], () => {
		if (page.value > totalPages.value) page.value = totalPages.value;
	});

	const pagedRows = computed(() => {
		const start = (page.value - 1) * pageSize.value;
		return (rowsRef.value || []).slice(start, start + pageSize.value);
	});
	const rangeStart = computed(() => (total.value ? (page.value - 1) * pageSize.value + 1 : 0));
	const rangeEnd = computed(() => Math.min(page.value * pageSize.value, total.value));
	const showPagination = computed(() => totalPages.value > 1);

	function setPageSize(v) {
		pageSize.value = Number(v) || initialPageSize;
		page.value = 1;
	}
	function prev() {
		if (page.value > 1) page.value--;
	}
	function next() {
		if (page.value < totalPages.value) page.value++;
	}

	// reactive() unwraps the refs so the footer + table read plain values in the template.
	return reactive({
		page,
		pageSize,
		total,
		totalPages,
		pagedRows,
		rangeStart,
		rangeEnd,
		showPagination,
		setPageSize,
		prev,
		next,
	});
}
