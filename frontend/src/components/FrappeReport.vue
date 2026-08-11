<script setup>
// Generic, report-agnostic renderer for a Frappe/ERPNext Report (Query or Script).
//
// Filters come from the REPORT itself, resolved the way the Desk does (query_report.js):
// the report's client script is evaluated for its dynamic filters (frappe.query_reports
// [name].filters) incl. their computed defaults, falling back to the Report Filter child
// table when the script defines none. So any report's filters render here — the component
// is agnostic of which workspace links it. Each fieldtype maps to a control (Link /
// Select / Date / Check / number / data); Apply re-runs the report server-side with the
// values, seeded from the report's defaults. A client-side search filters the returned
// rows, then pagination. Themed for light + dark.
import { ref, reactive, computed, watch } from "vue";
import { useRoute } from "vue-router";
import { runReport, getReportFilters } from "@/data/reportApi";
import { evalReportFilters } from "@/utils/reportFilters";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { fmtINR, fmtDate } from "@/utils/format";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const props = defineProps({
	report: { type: String, required: true },
	pageSize: { type: Number, default: 50 },
});

const activeCompany = useActiveCompany();
const route = useRoute();
const loading = ref(true);
const error = ref("");
const columns = ref([]);
const rows = ref([]);

// Filter values supplied via the URL query (a deep-linked report view). These override
// the report's own computed defaults, so a shared link renders exactly what it encodes.
// This also covers reports whose filters we can't evaluate client-side — e.g. ERPNext's
// financial statements, whose script pulls filters from erpnext.financial_statements
// (absent from our shim), so they'd otherwise run with no filters and error.
const ROUTE_KEYS = new Set(["from", "fromLabel"]);
const urlFilters = computed(() => {
	const out = {};
	for (const [k, v] of Object.entries(route.query || {})) {
		if (ROUTE_KEYS.has(k)) continue;
		out[k] = Array.isArray(v) ? v[v.length - 1] : v;
	}
	return out;
});

// --- filters (report-defined) ---
const filterDefs = ref([]);
const filterValues = reactive({});
const NUMERIC = new Set(["Currency", "Float", "Int", "Percent"]);

function seedFilters(defs) {
	for (const k of Object.keys(filterValues)) delete filterValues[k];
	for (const f of defs) {
		filterValues[f.fieldname] =
			f.fieldtype === "Check" ? Number(f.default) || 0 : f.default ?? "";
	}
}
function selectOptions(f) {
	return (f.options || "")
		.split("\n")
		.map((o) => o.trim())
		.filter(Boolean);
}
const missingRequired = computed(() =>
	filterDefs.value.filter(
		(f) =>
			f.mandatory && (filterValues[f.fieldname] === "" || filterValues[f.fieldname] == null)
	)
);

async function runWith() {
	if (missingRequired.value.length) {
		error.value = `Set the required filter${
			missingRequired.value.length > 1 ? "s" : ""
		}: ${missingRequired.value.map((f) => f.label).join(", ")}.`;
		rows.value = [];
		columns.value = [];
		return;
	}
	loading.value = true;
	error.value = "";
	try {
		const res = await runReport(props.report, { ...filterValues });
		columns.value = (res.columns || [])
			.filter((c) => c && (c.label || c.fieldname))
			.map((c, i) => ({
				label: c.label || c.fieldname || `Column ${i + 1}`,
				fieldname: c.fieldname || c.label || String(i),
				fieldtype: c.fieldtype || "Data",
				index: i,
				align: NUMERIC.has(c.fieldtype) ? "right" : "left",
			}));
		rows.value = res.result || [];
		page.value = 1;
	} catch (err) {
		error.value = err.message || "Failed to run report.";
		columns.value = [];
		rows.value = [];
	} finally {
		loading.value = false;
	}
}

async function load() {
	loading.value = true;
	error.value = "";
	try {
		// Prefer the report's DYNAMIC (script) filters — read the same way the Desk does —
		// and fall back to its Report Filter child table, mirroring query_report.js.
		const cfg = (await getReportFilters(props.report)) || {};
		const js = evalReportFilters(cfg.script || "", props.report, {
			company: activeCompany.value,
		});
		filterDefs.value = js.length ? js : cfg.filters || [];
	} catch {
		filterDefs.value = [];
	}
	seedFilters(filterDefs.value);
	// URL query params win — makes deep-linked report URLs (with filters encoded) render
	// as shared, and supplies filters for reports whose defs we can't evaluate here.
	Object.assign(filterValues, urlFilters.value);
	await runWith();
}
watch(() => [props.report, route.fullPath], load, { immediate: true });

function applyFilters() {
	page.value = 1;
	runWith();
}
function clearFilters() {
	seedFilters(filterDefs.value);
	runWith();
}

// --- cells ---
function cellRaw(row, col) {
	if (Array.isArray(row)) return row[col.index];
	return row?.[col.fieldname];
}
function cellText(row, col) {
	const v = cellRaw(row, col);
	if (v === null || v === undefined || v === "") return "—";
	switch (col.fieldtype) {
		case "Currency":
			return fmtINR(v);
		case "Percent":
			return `${Math.round((Number(v) || 0) * 100) / 100}%`;
		case "Int":
			return Number(v).toLocaleString("en-IN");
		case "Float":
			return Number(v).toLocaleString("en-IN", {
				minimumFractionDigits: 2,
				maximumFractionDigits: 2,
			});
		case "Date":
		case "Datetime":
			return fmtDate(v);
		default:
			return String(v);
	}
}

// --- client-side search + pagination ---
const search = ref("");
const filtered = computed(() => {
	const q = search.value.trim().toLowerCase();
	if (!q) return rows.value;
	return rows.value.filter((row) =>
		columns.value.some((col) => {
			const v = cellRaw(row, col);
			return v != null && String(v).toLowerCase().includes(q);
		})
	);
});
const page = ref(1);
const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / props.pageSize)));
const paged = computed(() => {
	const start = (page.value - 1) * props.pageSize;
	return filtered.value.slice(start, start + props.pageSize);
});
watch(search, () => (page.value = 1));
function go(delta) {
	page.value = Math.min(pageCount.value, Math.max(1, page.value + delta));
}

const inputClass =
	"text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400";
</script>

<template>
	<div>
		<!-- Report filter bar (report-defined filters) -->
		<div
			v-if="filterDefs.length"
			class="bg-ink-50 border border-ink-200 rounded-lg px-3 py-2.5 mb-3 flex items-end gap-3 flex-wrap"
		>
			<div v-for="f in filterDefs" :key="f.fieldname" class="flex flex-col gap-1 min-w-0">
				<label class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ f.label }}<span v-if="f.mandatory" class="text-danger-600"> *</span>
				</label>

				<!-- Link / Dynamic Link -->
				<div v-if="f.fieldtype === 'Link' || f.fieldtype === 'Dynamic Link'" class="w-52">
					<DeskLinkPicker
						v-model="filterValues[f.fieldname]"
						:doctype="f.options || 'DocType'"
						label-field="name"
						value-field="name"
						:placeholder="`All ${f.label.toLowerCase()}`"
					/>
				</div>

				<!-- Select -->
				<DeskSelect
					v-else-if="f.fieldtype === 'Select'"
					v-model="filterValues[f.fieldname]"
					class="!w-44"
				>
					<option value="">All</option>
					<option v-for="o in selectOptions(f)" :key="o" :value="o">{{ o }}</option>
				</DeskSelect>

				<!-- Date / Datetime -->
				<input
					v-else-if="f.fieldtype === 'Date' || f.fieldtype === 'Datetime'"
					v-model="filterValues[f.fieldname]"
					type="date"
					:class="inputClass"
				/>

				<!-- Check -->
				<label
					v-else-if="f.fieldtype === 'Check'"
					class="inline-flex items-center gap-1.5 text-xs text-ink-700 h-[30px]"
				>
					<input
						v-model="filterValues[f.fieldname]"
						type="checkbox"
						:true-value="1"
						:false-value="0"
					/>
					<span>Yes</span>
				</label>

				<!-- Int / Float / Currency -->
				<input
					v-else-if="NUMERIC.has(f.fieldtype)"
					v-model.number="filterValues[f.fieldname]"
					type="number"
					:class="[inputClass, 'w-28 text-right tabular-nums']"
				/>

				<!-- Data / fallback -->
				<input
					v-else
					v-model="filterValues[f.fieldname]"
					type="text"
					:class="[inputClass, 'w-44']"
				/>
			</div>

			<div class="flex items-center gap-2 ml-auto">
				<button
					type="button"
					class="text-[11px] text-ink-500 hover:underline"
					@click="clearFilters"
				>
					Clear
				</button>
				<button type="button" class="text-xs desk-save-btn" @click="applyFilters">
					Apply
				</button>
			</div>
		</div>

		<!-- Search + count -->
		<div class="flex items-center gap-3 mb-3 flex-wrap">
			<input
				v-model="search"
				type="text"
				placeholder="Search this report…"
				class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 w-64 max-w-full"
			/>
			<span v-if="!loading && !error" class="text-[11px] text-ink-400">
				{{ filtered.length.toLocaleString("en-IN") }} row{{
					filtered.length === 1 ? "" : "s"
				}}
			</span>
		</div>

		<div v-if="loading" class="py-16 text-center text-sm text-ink-400">Running report…</div>
		<div
			v-else-if="error"
			class="bg-danger-50 border border-danger-200 rounded-lg px-4 py-6 text-sm text-danger-700"
		>
			{{ error }}
		</div>

		<template v-else>
			<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
				<table class="w-full text-xs">
					<thead
						class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200"
					>
						<tr>
							<th
								v-for="col in columns"
								:key="col.fieldname"
								class="px-3 py-2 whitespace-nowrap"
								:class="col.align === 'right' ? 'text-right' : 'text-left'"
							>
								{{ col.label }}
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(row, i) in paged"
							:key="i"
							class="border-b border-ink-100 last:border-0 hover:bg-brand-50/30"
						>
							<td
								v-for="col in columns"
								:key="col.fieldname"
								class="px-3 py-2 whitespace-nowrap"
								:class="[
									col.align === 'right'
										? 'text-right tabular-nums'
										: 'text-left',
									col.fieldtype === 'Link'
										? 'font-mono text-ink-600'
										: 'text-ink-800',
								]"
							>
								{{ cellText(row, col) }}
							</td>
						</tr>
						<tr v-if="!paged.length">
							<td
								:colspan="columns.length || 1"
								class="px-3 py-12 text-center text-xs text-ink-400 italic"
							>
								{{ search ? "No rows match the search." : "No rows." }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- Pagination -->
			<div
				v-if="pageCount > 1"
				class="flex items-center justify-end gap-3 mt-3 text-xs text-ink-500"
			>
				<button
					type="button"
					class="px-2 py-1 border border-ink-200 rounded-md disabled:opacity-40 hover:bg-ink-50"
					:disabled="page <= 1"
					@click="go(-1)"
				>
					← Prev
				</button>
				<span>Page {{ page }} / {{ pageCount }}</span>
				<button
					type="button"
					class="px-2 py-1 border border-ink-200 rounded-md disabled:opacity-40 hover:bg-ink-50"
					:disabled="page >= pageCount"
					@click="go(1)"
				>
					Next →
				</button>
			</div>
		</template>
	</div>
</template>
