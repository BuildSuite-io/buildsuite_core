<script setup>
// Generic renderer for a Frappe/ERPNext Report (Query or Script) inside the SPA.
// Runs the report via buildsuite_core.api.report.run_report and renders its typed
// columns + rows — cell formatting by fieldtype (Currency / Float / Int / Percent /
// Date / Link), a client-side search, and pagination. Reusable on any workspace's
// report tiles.
import { ref, computed, watch } from "vue";
import { runReport } from "@/data/reportApi";
import { fmtINR, fmtDate } from "@/utils/format";

const props = defineProps({
	report: { type: String, required: true },
	filters: { type: Object, default: () => ({}) },
	pageSize: { type: Number, default: 50 },
});

const loading = ref(true);
const error = ref("");
const columns = ref([]);
const rows = ref([]);

const NUMERIC = new Set(["Currency", "Float", "Int", "Percent"]);

async function load() {
	loading.value = true;
	error.value = "";
	try {
		const res = await runReport(props.report, props.filters);
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
watch(() => [props.report, props.filters], load, { immediate: true, deep: true });

// Rows come back as dicts keyed by fieldname (query reports) or as arrays.
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
</script>

<template>
	<div>
		<!-- Toolbar: search + count -->
		<div class="flex items-center gap-3 mb-3 flex-wrap">
			<input
				v-model="search"
				type="text"
				placeholder="Search this report…"
				class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 w-64 max-w-full"
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
