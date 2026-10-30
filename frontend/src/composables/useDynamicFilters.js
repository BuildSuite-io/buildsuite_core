import { computed, ref, watch } from "vue";
import { frappeRequest } from "frappe-ui-frappe-request";
import { filterableFieldsFromMeta, toServerFilter, chipLabel } from "@/utils/listFilters";

// Frappe-style "Add filter" for the hand-built lists (the ones that load reshaped rows from a
// custom API or a transformed list, so DocTypeListView can't own the query). Filters are field /
// condition / value built from the doctype's own meta, exactly as in DocTypeListView, but they are
// evaluated by Frappe: the active filters run through frappe.client.get_list on the doctype and the
// list keeps only the rows whose id is in the matching set. That keeps every operator (Between,
// Timespan, Link, like…) and read permissions server-side, whatever shape the rows are in.
//
// Normally DeskList owns this (pass `filter-doctype`). A list that pages on the server can't hold
// every row, so it creates the instance itself in server mode — `resolveNames: false` skips the
// name lookup — sends `df.serverFilters` with its own query, and hands the instance to DeskList
// as `:dynamic-filters` (the editor and chips only).

const metaCache = new Map(); // doctype -> Promise<meta>
function loadDoctypeMeta(doctype) {
	if (!metaCache.has(doctype)) {
		metaCache.set(
			doctype,
			frappeRequest({
				url: "frappe.desk.form.load.getdoctype",
				method: "POST",
				params: { doctype, with_parent: 1 },
			})
				.then((res) => (res?.docs ? res : res?.message)?.docs?.[0] || null)
				.catch((err) => {
					metaCache.delete(doctype);
					console.warn("[buildsuite] Failed to fetch doctype meta", err);
					return null;
				})
		);
	}
	return metaCache.get(doctype);
}

export function useDynamicFilters(doctype, { resolveNames = true } = {}) {
	const meta = ref(null);
	loadDoctypeMeta(doctype).then((m) => (meta.value = m));
	const fields = computed(() => filterableFieldsFromMeta(meta.value));

	const filters = ref([]); // [{ fieldname, label, fieldtype, options, condition, value }]
	const editorOpen = ref(false);
	const editingIndex = ref(-1);

	function openEditor() {
		editingIndex.value = -1;
		editorOpen.value = true;
	}
	function editFilter(i) {
		editingIndex.value = i;
		editorOpen.value = true;
	}
	function closeEditor() {
		editorOpen.value = false;
		editingIndex.value = -1;
	}
	function apply(filter) {
		if (editingIndex.value >= 0) filters.value.splice(editingIndex.value, 1, filter);
		else filters.value.push(filter);
		closeEditor();
	}
	function remove(i) {
		filters.value.splice(i, 1);
	}
	function clear() {
		filters.value = [];
	}

	const serverFilters = computed(() => filters.value.map(toServerFilter).filter(Boolean));
	const active = computed(() => serverFilters.value.length > 0);

	// Names of the records matching the active filters; null until the first answer.
	const matching = ref(null);
	const loading = ref(false);
	let seq = 0;
	watch(
		() => JSON.stringify(serverFilters.value),
		async () => {
			if (!resolveNames) return;
			if (!serverFilters.value.length) {
				matching.value = null;
				loading.value = false;
				return;
			}
			const mine = ++seq;
			loading.value = true;
			try {
				const rows = await frappeRequest({
					url: "frappe.client.get_list",
					params: {
						doctype,
						fields: ["name"],
						filters: serverFilters.value,
						limit_page_length: 0,
					},
				});
				if (mine === seq) matching.value = new Set((rows || []).map((r) => r.name));
			} catch (err) {
				console.warn("[buildsuite] dynamic filter query failed", err);
				if (mine === seq) matching.value = new Set();
			} finally {
				if (mine === seq) loading.value = false;
			}
		}
	);

	// Keep only the rows the filters match (all rows when no filter is active). Until the first
	// answer arrives the set is empty, so the list never flashes unfiltered rows.
	function applyTo(rows, idKey = "id") {
		if (!active.value) return rows;
		const set = matching.value || new Set();
		return rows.filter((r) => set.has(r?.[idKey]));
	}

	return {
		meta,
		fields,
		filters,
		editorOpen,
		editingIndex,
		openEditor,
		editFilter,
		closeEditor,
		apply,
		remove,
		clear,
		chipLabel,
		serverFilters,
		active,
		loading,
		applyTo,
	};
}
