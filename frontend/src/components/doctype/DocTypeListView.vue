<script setup>
import { computed, ref, watch } from "vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DeskFilterEditor from "@/components/desk/DeskFilterEditor.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate } from "@/utils/format";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const props = defineProps({
	doctype: { type: String, required: true },
	fieldOrder: { type: Array, required: true },
	columns: { type: Array, default: null },
	searchFields: { type: Array, default: () => ["name"] },
	baseFilters: { type: Array, default: () => [] },
	filterValues: { type: Object, default: () => ({}) },
	filterFieldMap: { type: Object, default: () => ({}) },
	pageLength: { type: Number, default: 100 },
	paginated: { type: Boolean, default: true },
	pageSize: { type: Number, default: 10 },
	pageSizeOptions: { type: Array, default: () => [10, 20, 50, 100] },
	cacheKey: { type: [String, Array], default: null },
	initialOrderBy: { type: String, default: "" },
	rowKey: { type: String, default: "name" },
	searchPlaceholder: { type: String, default: "Search" },
	emptyMessage: { type: String, default: "No records found" },
	compact: { type: Boolean, default: false },
});

const emit = defineEmits(["row-click", "count-change"]);

const search = ref("");
const meta = ref(null);
const metaError = ref(null);
const metaLoading = ref(false);
const currentPage = ref(1);
const currentPageSize = ref(props.pageSize);
const totalCount = ref(null);

const sortField = ref("");
const sortDirection = ref("desc");

async function loadMeta() {
	const mode = import.meta.env.VITE_DATA_MODE || "remote";
	if (mode === "local") {
		meta.value = { fields: [] }; // empty meta for local mode
		return;
	}

	metaLoading.value = true;
	metaError.value = null;
	try {
		const response = await fetch("/api/method/frappe.desk.form.load.getdoctype", {
			method: "POST",
			credentials: "include",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: JSON.stringify({
				doctype: props.doctype,
				with_parent: 1,
			}),
		});

		if (!response.ok) {
			throw new Error(`Doctype meta fetch failed with status ${response.status}`);
		}

		const payload = await response.json();
		const resolved = payload?.docs ? payload : payload?.message;
		meta.value = resolved?.docs?.[0] || null;
	} catch (error) {
		metaError.value = error;
		meta.value = null;
		console.warn("[buildsuite] Failed to fetch doctype meta", error);
	} finally {
		metaLoading.value = false;
	}
}

const systemFields = [
	{ fieldname: "name", label: "ID", fieldtype: "Data" },
	{ fieldname: "owner", label: "Owner", fieldtype: "Link" },
	{ fieldname: "_assign", label: "Assigned To", fieldtype: "Text" },
	{ fieldname: "modified", label: "Updated", fieldtype: "Datetime" },
	{ fieldname: "creation", label: "Created", fieldtype: "Datetime" },
];

const fieldMetaMap = computed(() => {
	const map = new Map();
	for (const f of systemFields) map.set(f.fieldname, f);
	for (const f of meta.value?.fields || []) {
		if (f?.fieldname) map.set(f.fieldname, f);
	}
	return map;
});

const configuredColumns = computed(() => {
	if (!Array.isArray(props.columns) || !props.columns.length) return null;
	return props.columns.filter((column) => column?.key);
});

// Standard/system fields aren't in a doctype's `fields` meta, so the validity filter below
// would silently drop them — including `docstatus`, which a status column derives its state
// from (drop it and every row reads as Draft). Keep them permitted.
const STANDARD_FIELDS = new Set([
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
]);

const resolvedFields = computed(() => {
	const candidates = configuredColumns.value
		? configuredColumns.value.flatMap((column) => {
				if (Array.isArray(column.fields) && column.fields.length) return column.fields;
				return [column.key];
		  })
		: props.fieldOrder;

	const valid = meta.value
		? candidates.filter((fieldname) => fieldMetaMap.value.has(fieldname) || STANDARD_FIELDS.has(fieldname))
		: candidates;
	const withName = valid.includes("name") ? valid : ["name", ...valid];
	return Array.from(new Set(withName));
});

function defaultColumnLabel(column) {
	if (column.label != null) return column.label;
	const fallbackField =
		Array.isArray(column.fields) && column.fields.length ? column.fields[0] : column.key;
	const metaField = fieldMetaMap.value.get(fallbackField);
	return metaField?.label || column.key;
}

function defaultColumnAlign(column) {
	if (column.align) return column.align;

	if (column.preset === "progress") return "right";
	if (column.preset === "timeline") return "left";

	const fallbackField =
		Array.isArray(column.fields) && column.fields.length ? column.fields[0] : column.key;
	const fieldtype = fieldMetaMap.value.get(fallbackField)?.fieldtype;
	const numericTypes = ["Currency", "Float", "Int", "Percent"];
	return numericTypes.includes(fieldtype) ? "right" : "left";
}

const resolvedColumns = computed(() => {
	if (configuredColumns.value) {
		return configuredColumns.value.map((column) => ({
			key: column.key,
			label: defaultColumnLabel(column),
			align: defaultColumnAlign(column),
			preset: column.preset || "",
			fields: Array.isArray(column.fields) ? column.fields : [],
			renderer: column.renderer || null,
			rendererProps: column.rendererProps || null,
			statusClassMap: column.statusClassMap || null,
			iconFn: typeof column.iconFn === "function" ? column.iconFn : null,
		}));
	}

	return resolvedFields.value.map((fieldname) => {
		const metaField = fieldMetaMap.value.get(fieldname) || {};
		const numericTypes = ["Currency", "Float", "Int", "Percent"];
		return {
			key: fieldname,
			label: metaField.label || fieldname,
			align: numericTypes.includes(metaField.fieldtype) ? "right" : "left",
		};
	});
});

// --- Dynamic (ad-hoc) filters — Frappe-style field/condition/value builder ---------
// Layout / no-value fieldtypes can't be filtered on, so they're excluded from the picker.
const NO_VALUE_FIELDTYPES = new Set([
	"Section Break", "Column Break", "Tab Break", "HTML", "Table", "Table MultiSelect",
	"Button", "Image", "Fold", "Heading", "Signature", "Geolocation",
]);
const STANDARD_FILTER_FIELDS = [
	{ fieldname: "name", label: "ID", fieldtype: "Data" },
	{ fieldname: "owner", label: "Created By", fieldtype: "Link", options: "User" },
	{ fieldname: "creation", label: "Created On", fieldtype: "Datetime" },
	{ fieldname: "modified", label: "Last Updated On", fieldtype: "Datetime" },
	{ fieldname: "modified_by", label: "Last Updated By", fieldtype: "Link", options: "User" },
	{ fieldname: "_assign", label: "Assigned To", fieldtype: "Data" },
	{ fieldname: "idx", label: "Index", fieldtype: "Int" },
];
// Fields offered in the filter editor: standard metadata + the doctype's own
// value-bearing fields, mirroring Frappe's list filter field list.
const filterableFields = computed(() => {
	const out = [...STANDARD_FILTER_FIELDS];
	const seen = new Set(out.map((f) => f.fieldname));
	for (const f of meta.value?.fields || []) {
		if (!f?.fieldname || NO_VALUE_FIELDTYPES.has(f.fieldtype) || seen.has(f.fieldname)) continue;
		out.push({
			fieldname: f.fieldname,
			label: f.label || f.fieldname,
			fieldtype: f.fieldtype,
			options: f.options,
		});
		seen.add(f.fieldname);
	}
	return out;
});

const dynamicFilters = ref([]); // [{ fieldname, label, fieldtype, options, condition, value }]
const filterEditorOpen = ref(false);
const editingFilterIndex = ref(-1);

// One dynamic filter -> a [field, operator, value] tuple the backend understands
// (frappe.client.get_list / reportview). Returns null when the value is empty.
function toServerFilter(f) {
	const field = f.fieldname;
	const v = f.value;
	switch (f.condition) {
		case "like":
		case "not like":
			return v === "" || v == null ? null : [field, f.condition, `%${v}%`];
		case "in":
		case "not in": {
			const list = Array.isArray(v)
				? v.filter(Boolean)
				: String(v ?? "").split(",").map((s) => s.trim()).filter(Boolean);
			return list.length ? [field, f.condition, list] : null;
		}
		case "is":
			return [field, "is", v || "set"];
		case "Between": {
			const [a, b] = Array.isArray(v) ? v : [];
			return a && b ? [field, "between", [a, b]] : null;
		}
		case "Timespan":
			return v ? [field, "timespan", v] : null;
		default:
			return v === "" || v == null ? null : [field, f.condition, v];
	}
}

function openFilterEditor() {
	editingFilterIndex.value = -1;
	filterEditorOpen.value = true;
}
function editFilter(i) {
	editingFilterIndex.value = i;
	filterEditorOpen.value = true;
}
function onFilterApply(filter) {
	if (editingFilterIndex.value >= 0) {
		dynamicFilters.value.splice(editingFilterIndex.value, 1, filter);
	} else {
		dynamicFilters.value.push(filter);
	}
	filterEditorOpen.value = false;
	editingFilterIndex.value = -1;
}
function removeFilter(i) {
	dynamicFilters.value.splice(i, 1);
}
function clearFilters() {
	dynamicFilters.value = [];
}

// Chip text: "Label operator value".
const CONDITION_SYMBOL = {
	"=": "=", "!=": "≠", like: "like", "not like": "not like", in: "in", "not in": "not in",
	is: "is", ">": ">", "<": "<", ">=": "≥", "<=": "≤", Between: "between", Timespan: "in",
};
function chipLabel(f) {
	let text;
	if (f.condition === "is") text = f.value === "not set" ? "Not Set" : "Set";
	else if (f.condition === "Between" && Array.isArray(f.value)) text = `${f.value[0]} – ${f.value[1]}`;
	else if (Array.isArray(f.value)) text = f.value.join(", ");
	else if (f.fieldtype === "Check") text = f.value === "0" || f.value === 0 ? "No" : "Yes";
	else text = String(f.value ?? "");
	return `${f.label} ${CONDITION_SYMBOL[f.condition] || f.condition} ${text}`.trim();
}

const serverFilters = computed(() => {
	const filters = [...props.baseFilters];
	for (const [key, value] of Object.entries(props.filterValues || {})) {
		if (!value) continue;
		const spec = props.filterFieldMap?.[key];
		if (!spec) continue;
		// A spec is either a fieldname string (equality) or { field, op, like } —
		// the latter lets a filter target e.g. `_assign` with a `like %value%`.
		if (typeof spec === "string") {
			filters.push([spec, "=", value]);
		} else if (spec.field) {
			filters.push([spec.field, spec.op || "=", spec.like ? `%${value}%` : value]);
		}
	}
	for (const f of dynamicFilters.value) {
		const sf = toServerFilter(f);
		if (sf) filters.push(sf);
	}
	return filters;
});

const serverOrFilters = computed(() => {
	const term = search.value.trim();
	if (!props.paginated || !term) return [];

	return props.searchFields
		.filter((fieldname) => fieldMetaMap.value.has(fieldname))
		.map((fieldname) => [fieldname, "like", `%${term}%`]);
});

const sortableFields = computed(() => {
	const base = new Set();
	const sortFieldFromMeta = meta.value?.sort_field;
	if (sortFieldFromMeta && fieldMetaMap.value.has(sortFieldFromMeta)) {
		base.add(sortFieldFromMeta);
	}

	const sortableTypes = new Set([
		"Date",
		"Datetime",
		"Currency",
		"Float",
		"Int",
		"Percent",
		"Data",
		"Link",
		"Select",
		"Check",
	]);
	for (const fieldname of resolvedFields.value) {
		const field = fieldMetaMap.value.get(fieldname);
		if (!field) continue;
		if (sortableTypes.has(field.fieldtype)) {
			base.add(fieldname);
		}
	}

	base.add("modified");
	base.add("creation");

	return Array.from(base).map((fieldname) => {
		const field = fieldMetaMap.value.get(fieldname);
		return {
			value: fieldname,
			label: field?.label || fieldname,
		};
	});
});

const resource = useDocTypeList(props.doctype, {
	fields: props.fieldOrder,
	filters: serverFilters.value,
	orFilters: serverOrFilters.value,
	orderBy: props.initialOrderBy || "modified desc",
	pageLength: props.paginated ? currentPageSize.value : props.pageLength,
	start: props.paginated ? 0 : 0,
	cache: props.cacheKey || `doctype-list:${props.doctype}`,
	auto: false,
});

const parsedDefaultOrder = computed(() => {
	if (props.initialOrderBy) {
		const [field = "modified", direction = "desc"] = props.initialOrderBy.split(/\s+/);
		return { field, direction: direction.toLowerCase() === "asc" ? "asc" : "desc" };
	}

	// Default to `modified desc` so the most recently updated record is always on top —
	// regardless of the doctype's own meta sort_field (which can be creation, a name, etc.).
	// Every doctype has `modified`, so this is always valid; a view wanting a different
	// default passes `initialOrderBy` explicitly.
	return { field: "modified", direction: "desc" };
});

watch(
	parsedDefaultOrder,
	(next) => {
		if (!sortField.value) {
			sortField.value = next.field;
			sortDirection.value = next.direction;
		}
	},
	{ immediate: true }
);

const activeOrderBy = computed(() => `${sortField.value || "modified"} ${sortDirection.value}`);
const hasNextPage = computed(() => !!resource.hasNextPage);

const backendRangeStart = computed(() => {
	if (!props.paginated) return 0;
	const length = resource.data?.length ?? 0;
	if (!length) return 0;
	return (currentPage.value - 1) * currentPageSize.value + 1;
});

const backendRangeEnd = computed(() => {
	if (!props.paginated) return 0;
	const length = resource.data?.length ?? 0;
	if (!length) return 0;
	return backendRangeStart.value + length - 1;
});

async function fetchCurrentPage(resetPage = false) {
	if (resetPage) currentPage.value = 1;

	const start = props.paginated ? (currentPage.value - 1) * currentPageSize.value : 0;

	const pageLength = props.paginated ? currentPageSize.value : props.pageLength;

	resource.update({
		doctype: props.doctype,
		fields: resolvedFields.value,
		filters: serverFilters.value,
		orFilters: serverOrFilters.value,
		orderBy: activeOrderBy.value,
		start,
		pageLength,
	});

	// frappe-ui list resource appends rows when start > 0 by default;
	// reset local list data so each request represents one page.
	if (props.paginated && start > 0) {
		resource.setData([]);
	}

	return resource.fetch();
}

// Real total count of matching records (respects filters + search + permissions),
// so the pager shows "1-10 of 47" instead of a lookahead estimate. Falls back to
// the estimate (totalCount stays null) if the count call fails.
async function fetchCount() {
	if (!props.paginated) return;
	if ((import.meta.env.VITE_DATA_MODE || "remote") === "local") {
		totalCount.value = resource.data?.length ?? 0;
		return;
	}
	try {
		const body = new URLSearchParams();
		body.set("doctype", props.doctype);
		body.set("filters", JSON.stringify(serverFilters.value));
		if (serverOrFilters.value.length) {
			body.set("or_filters", JSON.stringify(serverOrFilters.value));
		}
		const res = await fetch("/api/method/frappe.desk.reportview.get_count", {
			method: "POST",
			credentials: "include",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded",
				Accept: "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: body.toString(),
		});
		if (!res.ok) throw new Error(`get_count failed with status ${res.status}`);
		const payload = await res.json();
		totalCount.value = Number(payload?.message) || 0;
	} catch (err) {
		totalCount.value = null; // fall back to the lookahead estimate
		console.warn("[buildsuite] Failed to fetch list count", err);
	}
}

watch(
	() => JSON.stringify(serverFilters.value),
	() => {
		fetchCurrentPage(true);
		fetchCount();
	}
);

watch(
	() => JSON.stringify(serverOrFilters.value),
	() => {
		fetchCurrentPage(true);
		fetchCount();
	}
);

watch(
	() => resolvedFields.value.join(","),
	(next, prev) => {
		if (!prev || next === prev) return;
		fetchCurrentPage(true);
	}
);

watch(activeOrderBy, (next, prev) => {
	if (!next || next === prev) return;
	fetchCurrentPage(true);
});

watch(
	() => props.doctype,
	() => {
		loadMeta();
		fetchCurrentPage(true);
		fetchCount();
	}
);

watch(
	() => props.pageSize,
	(next) => {
		if (!props.paginated) return;
		const parsed = Number(next);
		if (!Number.isFinite(parsed) || parsed <= 0) return;
		currentPageSize.value = parsed;
		fetchCurrentPage(true);
	}
);

loadMeta();
fetchCurrentPage(true);
fetchCount();

function getColumnValue(row, column) {
	if (!column) return null;
	if (Array.isArray(column.fields) && column.fields.length) {
		return column.fields.map((fieldname) => row?.[fieldname]);
	}
	return row?.[column.key];
}

function formatValue(row, fieldname, column = null) {
	const value = row?.[fieldname];
	if (value === null || value === undefined || value === "") return "—";

	const fieldtype = fieldMetaMap.value.get(fieldname)?.fieldtype;
	if (fieldtype === "Date" || fieldtype === "Datetime") {
		return fmtDate(value);
	}
	if (fieldtype === "Check") {
		return value ? "Yes" : "No";
	}
	if (
		fieldtype === "Currency" ||
		fieldtype === "Float" ||
		fieldtype === "Int" ||
		fieldtype === "Percent"
	) {
		const number = Number(value);
		return Number.isFinite(number) ? number.toLocaleString() : value;
	}

	return value;
}

function resolvePreset(column) {
	if (!column) return "";
	if (typeof column.renderer === "string") return column.renderer;
	return column.preset || "";
}

function getTimelineValues(row, column) {
	const [startField = "expected_start_date", endField = "expected_end_date"] =
		column?.fields || [];
	return {
		start: row?.[startField],
		end: row?.[endField],
	};
}

function renderPresetText(row, column) {
	const preset = resolvePreset(column);
	if (preset === "timeline") {
		const { start, end } = getTimelineValues(row, column);
		if (!start && !end) return "—";
		return `${start ? fmtDate(start) : "—"} -> ${end ? fmtDate(end) : "—"}`;
	}

	if (preset === "progress") {
		const value = Number(row?.[column.key]);
		return Number.isFinite(value) ? `${value}%` : "—";
	}

	return formatValue(row, column.key, column);
}

function hasComponentRenderer(column) {
	return !!column?.renderer && typeof column.renderer !== "string";
}

function getRendererProps(row, column) {
	return {
		row,
		column,
		value: getColumnValue(row, column),
		meta: fieldMetaMap.value.get(column.key) || null,
		...(column?.rendererProps || {}),
	};
}

defineExpose({ reload: () => fetchCurrentPage(false) });

function progressValue(row, column) {
	const value = Number(row?.[column.key]);
	if (!Number.isFinite(value)) return 0;
	return Math.max(0, Math.min(100, value));
}

function progressTone(row, column) {
	const value = progressValue(row, column);
	if (value >= 100) return "bg-success-500";
	if (value >= 50) return "bg-info-500";
	return "bg-warning-500";
}

const filteredRows = computed(() => {
	const rows = resource.data || [];
	if (props.paginated) return rows;

	const term = search.value.trim().toLowerCase();
	if (!term) return rows;

	return rows.filter((row) => {
		return props.searchFields.some((fieldname) => {
			const raw = row?.[fieldname];
			if (raw === null || raw === undefined) return false;
			return String(raw).toLowerCase().includes(term);
		});
	});
});

watch(
	() => filteredRows.value.length,
	(n) => emit("count-change", n),
	{ immediate: true }
);

const estimatedTotalRows = computed(() => {
	if (!props.paginated) return filteredRows.value.length;
	if (hasNextPage.value) {
		return currentPage.value * currentPageSize.value + 1;
	}
	return backendRangeEnd.value;
});

// Prefer the real count; fall back to the lookahead estimate while it's loading
// or if the count call failed, so the pager keeps working.
const effectiveTotalRows = computed(() =>
	totalCount.value != null ? totalCount.value : estimatedTotalRows.value
);

const listCountText = computed(() => {
	if (!props.paginated) {
		return `${filteredRows.value.length} of ${resource.data?.length ?? 0}`;
	}

	if (!filteredRows.value.length) return "0 records";
	if (totalCount.value != null) {
		return `${backendRangeStart.value}-${backendRangeEnd.value} of ${totalCount.value} records`;
	}
	return `${backendRangeStart.value}-${backendRangeEnd.value} records`;
});

function onPageChange(page) {
	const parsed = Number(page);
	if (!Number.isFinite(parsed) || parsed <= 0 || parsed === currentPage.value) return;
	currentPage.value = parsed;
	fetchCurrentPage(false);
}

function onPageSizeChange(value) {
	const parsed = Number(value);
	if (!Number.isFinite(parsed) || parsed <= 0) return;
	if (parsed === currentPageSize.value) return;
	currentPageSize.value = parsed;
	fetchCurrentPage(true);
}
</script>

<template>
	<div class="relative">
		<div v-if="metaError" class="mb-2 text-xs text-danger-600">
			Failed to load {{ doctype }} metadata.
		</div>

		<!-- Dynamic filter editor (Frappe-style field/condition/value builder) -->
		<template v-if="filterEditorOpen">
			<div class="fixed inset-0 z-30" @click="filterEditorOpen = false"></div>
			<div class="absolute left-0 top-12 z-40">
				<DeskFilterEditor
					:fields="filterableFields"
					:initial="editingFilterIndex >= 0 ? dynamicFilters[editingFilterIndex] : null"
					@apply="onFilterApply"
					@cancel="filterEditorOpen = false"
				/>
			</div>
		</template>

		<DeskList
			v-model="search"
			:rows="filteredRows"
			:columns="resolvedColumns"
			:row-key="rowKey"
			:paginated="paginated"
			:page-size="currentPageSize"
			:page-size-options="pageSizeOptions"
			:server-paginated="paginated"
			:current-page="currentPage"
			:total-rows="effectiveTotalRows"
			:search-placeholder="searchPlaceholder"
			:compact="compact"
			:sort-field="sortField"
			:sort-direction="sortDirection"
			:sort-options="sortableFields"
			@row-click="(row) => emit('row-click', row)"
			@update:sort-field="sortField = $event"
			@update:sort-direction="sortDirection = $event"
			@page-change="onPageChange"
			@page-size-change="onPageSizeChange"
			@add-filter="openFilterEditor"
		>
			<template #filter-chips>
				<slot
					name="filter-chips"
					:resource="resource"
					:meta="meta"
					:meta-loading="metaLoading"
					:fields="resolvedFields"
				/>
				<span
					v-for="(f, i) in dynamicFilters"
					:key="i"
					class="cursor-pointer"
					title="Click to edit"
					@click="editFilter(i)"
				>
					<DeskFilterChip :label="chipLabel(f)" @remove="removeFilter(i)" />
				</span>
				<button
					v-if="dynamicFilters.length"
					type="button"
					class="text-[11px] text-ink-500 hover:text-ink-800 px-1"
					@click="clearFilters"
				>
					Clear
				</button>
			</template>

			<template #actions>
				<slot name="actions" />
			</template>

			<template
				v-for="column in resolvedColumns"
				:key="column.key"
				#[`cell-${column.key}`]="slotProps"
			>
				<slot :name="`cell-${column.key}`" v-bind="slotProps">
					<component
						:is="column.renderer"
						v-if="hasComponentRenderer(column)"
						v-bind="getRendererProps(slotProps.row, column)"
					/>

					<template v-else-if="resolvePreset(column) === 'status'">
						<StatusBadge
							v-if="
								typeof slotProps.row?.[column.key] === 'string' &&
								slotProps.row?.[column.key].trim()
							"
							:status="slotProps.row?.[column.key]"
							:status-class-map="column.statusClassMap || {}"
						/>
						<span v-else>—</span>
					</template>

					<div
						v-else-if="resolvePreset(column) === 'progress'"
						class="flex items-center justify-end gap-2"
					>
						<div
							class="w-16 h-1.5 bg-ink-100 overflow-hidden"
							style="border-radius: 2px"
						>
							<div
								class="h-full"
								:class="progressTone(slotProps.row, column)"
								:style="`width:${progressValue(slotProps.row, column)}%`"
							></div>
						</div>
						<span class="text-xs text-ink-700 tabular-nums w-8 text-right">{{
							renderPresetText(slotProps.row, column)
						}}</span>
					</div>

					<span
						v-else-if="resolvePreset(column) === 'timeline'"
						class="text-xs text-ink-500 whitespace-nowrap"
						>{{ renderPresetText(slotProps.row, column) }}</span
					>

					<div
						v-else-if="resolvePreset(column) === 'icon'"
						class="flex items-center justify-center"
					>
						<svg
							class="w-4 h-4 text-ink-400"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							v-html="
								getWorkspaceIconPath(
									column.iconFn ? column.iconFn(slotProps.row) : 'file'
								)
							"
						/>
					</div>

					<span v-else>{{ formatValue(slotProps.row, column.key, column) }}</span>
				</slot>
			</template>

			<template #empty>
				<slot name="empty">
					<div class="text-sm text-ink-500">{{ emptyMessage }}</div>
				</slot>
			</template>
		</DeskList>

		<div class="mt-2 text-xs text-ink-500 tabular-nums">{{ listCountText }}</div>
	</div>
</template>
