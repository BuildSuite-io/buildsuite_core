<script setup>
// The six Procurement reports, computed from live records via
// buildsuite_core.api.procurement_report. One view, one section per :slug on
// /procurement/report/:slug — matching the finance report pattern. An optional ?project=
// narrows every report to that project and its sub-projects (resolved server-side); the rest
// of the filters — search, supplier, status, dates, the one-click narrowings — are applied
// here over the rows the backend returns.

import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";

import DeskInput from "@/components/desk/DeskInput.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { PROCUREMENT_REPORTS } from "@/data/procurementReportApi";
import { fmtCompactINR, fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const route = useRoute();
const router = useRouter();
const { projectOptions } = useProjectOptions();

const DAY = 86400000;
const todayISO = new Date().toISOString().slice(0, 10);
const daysSince = (iso) =>
	!iso ? null : Math.floor((new Date(todayISO) - new Date(iso + "T00:00:00")) / DAY);

const META = {
	"requests-to-order": {
		title: __("Requests waiting to be ordered"),
		desc: __(
			"What site has asked for that is not yet on a purchase order — the gap between the request book and the order book."
		),
	},
	"delivery-followup": {
		title: __("Delivery follow-up"),
		desc: __(
			"Open orders by the date they were needed, how much has landed, and what is still outstanding."
		),
	},
	"site-stock": {
		title: __("Material at site"),
		desc: __("Received minus consumed, per item, at each project store."),
	},
	"rate-check": {
		title: __("Purchase rate vs estimate"),
		desc: __(
			"What you are paying against the QS rate in the Rate Master. Only lines carrying a rate code can be compared."
		),
	},
	"purchase-register": {
		title: __("Purchase register"),
		desc: __(
			"Every purchase order line — supplier, item, quantity and rate — so last paid is one search away."
		),
	},
	"consumption-by-cost-code": {
		title: __("Consumption by cost code"),
		desc: __("Material issued to site, grouped by the cost code it was booked against."),
	},
};

const slug = computed(() => route.params.slug);
const meta = computed(() => META[slug.value] || null);
const projectId = computed(() => route.query.project || "");
function setProject(id) {
	router.replace({
		query: id ? { ...route.query, project: id } : { ...route.query, project: undefined },
	});
}

// -------------------------------------------------------------- data load ---
const raw = ref(null); // an array, or { rows, unlinked } for rate-check
const loading = ref(true);
const error = ref("");

async function load() {
	if (!meta.value) {
		raw.value = null;
		loading.value = false;
		return;
	}
	loading.value = true;
	error.value = "";
	try {
		raw.value = await PROCUREMENT_REPORTS[slug.value](projectId.value || undefined);
	} catch (e) {
		error.value = e.message || __("Failed to load the report.");
		raw.value = null;
	} finally {
		loading.value = false;
	}
}
onMounted(load);
watch(slug, () => Object.assign(f, BLANK)); // a new report starts unfiltered
watch([slug, projectId], load); // re-scope from the server when the report or project changes

const rowsArr = computed(() => (Array.isArray(raw.value) ? raw.value : raw.value?.rows || []));

// ---------------------------------------------------------------- filters ---
const BLANK = {
	q: "",
	supplier: "",
	status: "",
	from: "",
	to: "",
	lateOnly: false,
	overOnly: false,
	inStockOnly: false,
	code: "",
};
const f = reactive({ ...BLANK });
function clearFilters() {
	Object.assign(f, BLANK);
	if (projectId.value) setProject("");
}
const anyFilter = computed(
	() => !!projectId.value || Object.keys(BLANK).some((k) => f[k] !== BLANK[k])
);

const hit = (hay, needle) =>
	!needle ||
	String(hay || "")
		.toLowerCase()
		.includes(needle.trim().toLowerCase());
const inDates = (d) => (!f.from || (d || "") >= f.from) && (!f.to || (d || "") <= f.to);

// Distinct pickers, built from the rows themselves so nothing offers a value with no rows.
const distinct = (pick) =>
	[...new Set(rowsArr.value.map(pick).filter(Boolean))]
		.sort()
		.map((v) => ({ value: v, label: v }));
const supplierOptions = computed(() => distinct((r) => r.supplier));
const statusOptions = computed(() => distinct((r) => r.status));
const costCodeOptions = computed(() => distinct((r) => r.code));

// ------------------------------------------------- 1. requests to order ---
const requestsToOrder = computed(() =>
	rowsArr.value
		.filter((m) => !f.status || m.status === f.status)
		.filter((m) => inDates(m.required_by))
		.filter((m) => hit(m.name, f.q) || hit(m.project_name, f.q))
		.map((m) => ({
			...m,
			age: daysSince(m.request_date),
			lateBy: m.required_by && m.required_by < todayISO ? daysSince(m.required_by) : 0,
		}))
		.filter((m) => !f.lateOnly || m.lateBy > 0)
		.sort((a, b) => (a.required_by || "~").localeCompare(b.required_by || "~"))
);
const requestsValue = computed(() =>
	requestsToOrder.value.reduce((a, m) => a + (Number(m.value) || 0), 0)
);

// ---------------------------------------------------- 2. delivery chase ---
const deliveryFollowup = computed(() =>
	rowsArr.value
		.filter((p) => !f.supplier || p.supplier === f.supplier)
		.filter((p) => inDates(p.required_by))
		.filter((p) => hit(p.name, f.q) || hit(p.supplier, f.q) || hit(p.project_name, f.q))
		.map((p) => ({
			...p,
			lateBy: p.required_by && p.required_by < todayISO ? daysSince(p.required_by) : 0,
		}))
		.filter((p) => !f.lateOnly || p.lateBy > 0)
		.sort(
			(a, b) =>
				b.lateBy - a.lateBy || (a.required_by || "~").localeCompare(b.required_by || "~")
		)
);
const pendingValue = computed(() =>
	deliveryFollowup.value.reduce((a, p) => a + (Number(p.pending_value) || 0), 0)
);
const overdueCount = computed(() => deliveryFollowup.value.filter((p) => p.lateBy > 0).length);

// -------------------------------------------------------- 3. site stock ---
const siteStock = computed(() =>
	rowsArr.value
		.filter((r) => hit(r.item, f.q) || hit(r.project_name, f.q))
		.filter((r) => !f.inStockOnly || r.available > 0)
		.sort(
			(a, b) =>
				(a.project_name || "").localeCompare(b.project_name || "") ||
				a.item.localeCompare(b.item)
		)
);

// -------------------------------------------------------- 4. rate check ---
const rateCheckRows = computed(() =>
	(raw.value?.rows || [])
		.filter((r) => hit(r.item, f.q) || hit(r.code, f.q) || hit(r.supplier, f.q))
		.filter((r) => !f.overOnly || (r.variance ?? 0) > 0)
);
const rateUnlinked = computed(() => raw.value?.unlinked || 0);

// -------------------------------------------------- 5. purchase register ---
const purchaseRegister = computed(() =>
	rowsArr.value
		.filter((r) => !f.supplier || r.supplier === f.supplier)
		.filter((r) => inDates(r.date))
		.filter((r) => hit(r.item, f.q) || hit(r.po, f.q) || hit(r.supplier, f.q))
);
const registerTotal = computed(() =>
	purchaseRegister.value.reduce((a, r) => a + (Number(r.amount) || 0), 0)
);

// ------------------------------------------- 6. consumption by cost code ---
const consumptionByCostCode = computed(() => {
	const map = new Map();
	for (const c of rowsArr.value) {
		if (f.code && c.code !== f.code) continue;
		if (!inDates(c.date)) continue;
		if (!(hit(c.item, f.q) || hit(c.code, f.q))) continue;
		const key = `${c.project}|${c.code}|${c.item}`;
		if (!map.has(key))
			map.set(key, {
				project: c.project,
				project_name: c.project_name,
				code: c.code,
				item: c.item,
				uom: c.uom,
				qty: 0,
				value: 0,
			});
		const g = map.get(key);
		g.qty += Number(c.qty) || 0;
		g.value += Number(c.value) || 0;
	}
	return [...map.values()].sort(
		(a, b) => a.code.localeCompare(b.code) || a.item.localeCompare(b.item)
	);
});
const consumptionValue = computed(() =>
	consumptionByCostCode.value.reduce((a, r) => a + r.value, 0)
);

// The filter-bar count + labels, per report — each with its own word for a row.
const COUNTS = {
	"requests-to-order": () => ({
		shown: requestsToOrder.value.length,
		total: rowsArr.value.length,
		noun: __("requests"),
		date: __("Needed by"),
		find: __("Request, project…"),
	}),
	"delivery-followup": () => ({
		shown: deliveryFollowup.value.length,
		total: rowsArr.value.length,
		noun: __("orders"),
		date: __("Needed by"),
		find: __("Order, supplier, project…"),
	}),
	"site-stock": () => ({
		shown: siteStock.value.length,
		total: rowsArr.value.length,
		noun: __("items"),
		date: "",
		find: __("Item or store…"),
	}),
	"rate-check": () => ({
		shown: rateCheckRows.value.length,
		total: (raw.value?.rows || []).length,
		noun: __("items"),
		date: "",
		find: __("Item, code, supplier…"),
	}),
	"purchase-register": () => ({
		shown: purchaseRegister.value.length,
		total: rowsArr.value.length,
		noun: __("lines"),
		date: __("Ordered"),
		find: __("Item, order, supplier…"),
	}),
	"consumption-by-cost-code": () => ({
		shown: consumptionByCostCode.value.length,
		total: null,
		noun: __("lines"),
		date: __("Issued"),
		find: __("Item or cost code…"),
	}),
};
const counts = computed(() =>
	COUNTS[slug.value]
		? COUNTS[slug.value]()
		: { shown: null, total: null, noun: __("rows"), date: "", find: __("Search…") }
);

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: meta.value?.title || __("Reports") },
]);

const tone = (v) => (v > 0.5 ? "text-danger-700" : v < -0.5 ? "text-success-700" : "text-ink-700");
const inr = (n) => (n || n === 0 ? Number(n).toLocaleString("en-IN") : n);
</script>

<template>
	<DeskPage
		:title="meta ? meta.title : __('Report not found')"
		:subtitle="meta ? meta.desc : __('No report registered for \'{0}\'', [slug])"
		:breadcrumbs="breadcrumbs"
		:printable="!!meta"
	>
		<div
			v-if="!meta"
			class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-500 rounded-lg"
		>
			{{ __("No report is registered under that name.") }}
			<RouterLink to="/procurement" class="text-brand-700 hover:underline ml-1"
				>{{ __("Back to Procurement →") }}</RouterLink
			>
		</div>

		<template v-else>
			<ReportFilters
				:active="anyFilter"
				:shown="counts.shown"
				:total="counts.total"
				:noun="counts.noun"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>{{ __("Project") }}</span
					>
					<span class="w-56 inline-block">
						<DeskSearchableSelect
							:model-value="projectId"
							:options="projectOptions"
							allow-clear
							:placeholder="__('All projects')"
							:search-placeholder="__('Search projects…')"
							@update:model-value="setProject"
						/>
					</span>
				</label>

				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>{{ __("Find") }}</span
					>
					<DeskInput v-model="f.q" :placeholder="counts.find" class="!w-52" />
				</label>

				<label v-if="slug === 'requests-to-order'" class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>{{ __("Status") }}</span
					>
					<DeskSelect v-model="f.status" class="!w-44">
						<option value="">{{ __("Any") }}</option>
						<option v-for="o in statusOptions" :key="o.value" :value="o.value">
							{{ o.label }}
						</option>
					</DeskSelect>
				</label>

				<label
					v-if="slug === 'delivery-followup' || slug === 'purchase-register'"
					class="flex items-center gap-1.5"
				>
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>{{ __("Supplier") }}</span
					>
					<span class="w-52 inline-block">
						<DeskSearchableSelect
							v-model="f.supplier"
							:options="supplierOptions"
							allow-clear
							:placeholder="__('All suppliers')"
							:search-placeholder="__('Search suppliers…')"
						/>
					</span>
				</label>

				<label
					v-if="slug === 'consumption-by-cost-code'"
					class="flex items-center gap-1.5"
				>
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>{{ __("Cost code") }}</span
					>
					<span class="w-56 inline-block">
						<DeskSearchableSelect
							v-model="f.code"
							:options="costCodeOptions"
							allow-clear
							:placeholder="__('All cost codes')"
							:search-placeholder="__('Search cost codes…')"
						/>
					</span>
				</label>

				<label v-if="counts.date" class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
						counts.date
					}}</span>
					<DeskInput v-model="f.from" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
					<DeskInput v-model="f.to" type="date" class="!w-36" />
				</label>

				<label
					v-if="slug === 'requests-to-order' || slug === 'delivery-followup'"
					class="flex items-center gap-1.5 cursor-pointer"
				>
					<input v-model="f.lateOnly" type="checkbox" class="accent-brand-600" />
					<span class="text-[11px] text-ink-600">{{ __("Overdue only") }}</span>
				</label>
				<label
					v-if="slug === 'rate-check'"
					class="flex items-center gap-1.5 cursor-pointer"
				>
					<input v-model="f.overOnly" type="checkbox" class="accent-brand-600" />
					<span class="text-[11px] text-ink-600">{{ __("Over estimate only") }}</span>
				</label>
				<label
					v-if="slug === 'site-stock'"
					class="flex items-center gap-1.5 cursor-pointer"
				>
					<input v-model="f.inStockOnly" type="checkbox" class="accent-brand-600" />
					<span class="text-[11px] text-ink-600">{{ __("Hide emptied items") }}</span>
				</label>
			</ReportFilters>

			<p v-if="projectId" class="text-[11px] text-ink-500 -mt-1 mb-3">
				{{ __("Includes sub-projects.") }}
			</p>

			<div v-if="loading" class="text-sm text-ink-500 italic py-10 text-center">
				{{ __("Loading…") }}
			</div>
			<div v-else-if="error" class="text-sm text-danger-600 py-10 text-center">
				{{ error }}
			</div>

			<template v-else>
				<!-- 1. Requests waiting to be ordered -->
				<div v-if="slug === 'requests-to-order'">
					<div
						v-if="requestsToOrder.length"
						class="border border-ink-200 overflow-x-auto rounded-lg"
					>
						<table class="w-full text-sm">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2">{{ __("Request") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Project") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Raised") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Needed by") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Items") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Value") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Status") }}</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="m in requestsToOrder"
									:key="m.name"
									class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
								>
									<td class="px-3 py-2">
										<RouterLink
											:to="`/procurement/material-requests/${m.name}`"
											class="text-ink-900 font-medium hover:underline"
											>{{ m.name }}</RouterLink
										>
										<div class="text-[10px] text-ink-500">
											{{ __("{0}d old", [m.age]) }}
										</div>
									</td>
									<td class="px-3 py-2 text-ink-700">{{ m.project_name }}</td>
									<td class="px-3 py-2 text-ink-700">
										{{ fmtDate(m.request_date) }}
									</td>
									<td
										class="px-3 py-2 tabular-nums"
										:class="
											m.lateBy > 0
												? 'text-danger-700 font-medium'
												: 'text-ink-700'
										"
									>
										{{ fmtDate(m.required_by) }}
										<span v-if="m.lateBy > 0" class="text-[10px]">
											· {{ __("{0}d late", [m.lateBy]) }}</span
										>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ m.item_count }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">
										{{ fmtINR(m.value) }}
									</td>
									<td class="px-3 py-2">
										<ProcurementStatusPill :status="m.status" />
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr
									class="bg-ink-50 border-t border-ink-200 font-semibold text-ink-900"
								>
									<td class="px-3 py-2" colspan="5">
										{{
											requestsToOrder.length === 1
												? __("{0} request waiting", [requestsToOrder.length])
												: __("{0} requests waiting", [requestsToOrder.length])
										}}
									</td>
									<td class="px-3 py-2 text-right tabular-nums">
										{{ fmtINR(requestsValue) }}
									</td>
									<td></td>
								</tr>
							</tfoot>
						</table>
					</div>
					<div
						v-else
						class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic rounded-lg"
					>
						<template v-if="anyFilter">{{
							__("No requests match these filters.")
						}}</template>
						<template v-else>{{
							__("Nothing waiting — every request in scope has been ordered.")
						}}</template>
					</div>
				</div>

				<!-- 2. Delivery follow-up -->
				<div v-else-if="slug === 'delivery-followup'">
					<div
						v-if="deliveryFollowup.length"
						class="border border-ink-200 overflow-x-auto rounded-lg"
					>
						<table class="w-full text-sm">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2">{{ __("Order") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Supplier") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Project") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Needed by") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Received") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Still due") }}</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="p in deliveryFollowup"
									:key="p.name"
									class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
								>
									<td class="px-3 py-2">
										<RouterLink
											:to="`/procurement/purchase-orders/${p.name}`"
											class="text-ink-900 font-medium hover:underline"
											>{{ p.name }}</RouterLink
										>
									</td>
									<td class="px-3 py-2 text-ink-700">{{ p.supplier }}</td>
									<td class="px-3 py-2 text-ink-700">
										{{ p.project_name || "—" }}
									</td>
									<td
										class="px-3 py-2 tabular-nums"
										:class="
											p.lateBy > 0
												? 'text-danger-700 font-medium'
												: 'text-ink-700'
										"
									>
										{{ fmtDate(p.required_by) }}
										<span v-if="p.lateBy > 0" class="text-[10px]">
											· {{ __("{0}d late", [p.lateBy]) }}</span
										>
									</td>
									<td class="px-3 py-2 text-right">
										<div class="flex items-center justify-end gap-2">
											<div
												class="w-16 h-1.5 bg-ink-100 overflow-hidden rounded-full"
											>
												<div
													class="h-full"
													:class="
														p.pct >= 100
															? 'bg-success-500'
															: p.pct > 0
															? 'bg-info-500'
															: 'bg-ink-300'
													"
													:style="{ width: p.pct + '%' }"
												></div>
											</div>
											<span class="tabular-nums text-ink-700 w-9 text-right"
												>{{ p.pct }}%</span
											>
										</div>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">
										{{ fmtINR(p.pending_value) }}
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr
									class="bg-ink-50 border-t border-ink-200 font-semibold text-ink-900"
								>
									<td class="px-3 py-2" colspan="5">
										{{
											deliveryFollowup.length === 1
												? __("{0} open order", [deliveryFollowup.length])
												: __("{0} open orders", [deliveryFollowup.length])
										}}
										<span v-if="overdueCount" class="text-danger-700">
											· {{ __("{0} overdue", [overdueCount]) }}</span
										>
									</td>
									<td class="px-3 py-2 text-right tabular-nums">
										{{ fmtINR(pendingValue) }}
									</td>
								</tr>
							</tfoot>
						</table>
					</div>
					<div
						v-else
						class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic rounded-lg"
					>
						<template v-if="anyFilter">{{
							__("No orders match these filters.")
						}}</template>
						<template v-else>{{ __("No open orders in scope.") }}</template>
					</div>
				</div>

				<!-- 3. Material at site -->
				<div v-else-if="slug === 'site-stock'">
					<div
						v-if="siteStock.length"
						class="border border-ink-200 overflow-x-auto rounded-lg"
					>
						<table class="w-full text-sm">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2">{{ __("Project store") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Item") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Received") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Consumed") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("At site") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Unit") }}</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(r, i) in siteStock"
									:key="i"
									class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
								>
									<td class="px-3 py-2 text-ink-700">{{ r.project_name }}</td>
									<td class="px-3 py-2 text-ink-900">{{ r.item }}</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ inr(r.received) }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ inr(r.consumed) }}
									</td>
									<td
										class="px-3 py-2 text-right tabular-nums font-medium"
										:class="
											r.available === 0 ? 'text-warning-700' : 'text-ink-900'
										"
									>
										{{ inr(r.available) }}
									</td>
									<td class="px-3 py-2 text-ink-500">{{ r.uom }}</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div
						v-else
						class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic rounded-lg"
					>
						<template v-if="anyFilter">{{
							__("No items match these filters.")
						}}</template>
						<template v-else>{{ __("Nothing received at site yet in scope.") }}</template>
					</div>
					<p class="text-[11px] text-ink-500 mt-2">
						{{
							__(
								"Received counts posted purchase receipts; consumed counts posted consumption. A cancelled receipt never entered stock."
							)
						}}
					</p>
				</div>

				<!-- 4. Purchase rate vs estimate -->
				<div v-else-if="slug === 'rate-check'">
					<div
						v-if="rateCheckRows.length"
						class="border border-ink-200 overflow-x-auto rounded-lg"
					>
						<table class="w-full text-sm">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2">{{ __("Item") }}</th>
									<th class="text-left font-medium px-3 py-2">
										{{ __("Last bought from") }}
									</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Paid") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Rate Master") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Variance") }}</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="r in rateCheckRows"
									:key="r.item"
									class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
								>
									<td class="px-3 py-2">
										<div class="text-ink-900">{{ r.item }}</div>
										<div class="text-[10px] text-ink-500 font-mono">
											{{ r.code }}
										</div>
									</td>
									<td class="px-3 py-2 text-ink-700">
										{{ r.supplier }}
										<div class="text-[10px] text-ink-500">
											{{ r.po }} · {{ fmtDate(r.order_date) }}
										</div>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">
										{{ fmtINR(r.rate)
										}}<span class="text-[10px] text-ink-500">
											/ {{ r.unit }}</span
										>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ r.estimate ? fmtINR(r.estimate) : "—" }}
									</td>
									<td
										class="px-3 py-2 text-right tabular-nums font-medium"
										:class="
											r.variance === null ? 'text-ink-400' : tone(r.variance)
										"
									>
										<template v-if="r.variance === null">—</template>
										<template v-else
											>{{ r.variance > 0 ? "+" : ""
											}}{{ r.variance.toFixed(1) }}%</template
										>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div
						v-else
						class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic rounded-lg"
					>
						<template v-if="anyFilter">{{
							__("No items match these filters.")
						}}</template>
						<template v-else>{{
							__(
								"No order line in scope carries a rate code, so there is nothing to compare."
							)
						}}</template>
					</div>
					<p v-if="rateUnlinked" class="text-[11px] text-ink-500 mt-2">
						{{
							rateUnlinked === 1
								? __("{0} order line could not be checked — no rate code on the line.", [
										rateUnlinked,
								  ])
								: __("{0} order lines could not be checked — no rate code on the line.", [
										rateUnlinked,
								  ])
						}}
						Linking the item to a Rate Master entry under
						<RouterLink to="/items" class="text-brand-700 hover:underline"
							>Items</RouterLink
						>
						brings it into this report.
					</p>
				</div>

				<!-- 5. Purchase register -->
				<div v-else-if="slug === 'purchase-register'">
					<div
						v-if="purchaseRegister.length"
						class="border border-ink-200 overflow-x-auto rounded-lg"
					>
						<table class="w-full text-sm">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2">{{ __("Date") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Order") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Supplier") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Item") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Qty") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Rate") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Amount") }}</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(r, i) in purchaseRegister"
									:key="i"
									class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
								>
									<td class="px-3 py-2 text-ink-700 whitespace-nowrap">
										{{ fmtDate(r.date) }}
									</td>
									<td class="px-3 py-2">
										<RouterLink
											:to="`/procurement/purchase-orders/${r.po}`"
											class="text-ink-900 hover:underline"
											>{{ r.po }}</RouterLink
										>
										<div class="text-[10px] text-ink-500">
											{{ r.project_name || "—" }}
										</div>
									</td>
									<td class="px-3 py-2 text-ink-700">{{ r.supplier }}</td>
									<td class="px-3 py-2 text-ink-900">{{ r.item }}</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ inr(r.qty) }}
										<span class="text-[10px] text-ink-500">{{ r.uom }}</span>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ fmtINR(r.rate) }}
									</td>
									<td
										class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium"
									>
										{{ fmtINR(r.amount) }}
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr
									class="bg-ink-50 border-t border-ink-200 font-semibold text-ink-900"
								>
									<td class="px-3 py-2" colspan="6">
										{{ __("{0} lines", [purchaseRegister.length]) }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums">
										{{ fmtCompactINR(registerTotal) }}
									</td>
								</tr>
							</tfoot>
						</table>
					</div>
					<div
						v-else
						class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic rounded-lg"
					>
						<template v-if="anyFilter">{{
							__("No lines match these filters.")
						}}</template>
						<template v-else>{{ __("No purchase orders in scope.") }}</template>
					</div>
				</div>

				<!-- 6. Consumption by cost code -->
				<div v-else-if="slug === 'consumption-by-cost-code'">
					<div
						v-if="consumptionByCostCode.length"
						class="border border-ink-200 overflow-x-auto rounded-lg"
					>
						<table class="w-full text-sm">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2">{{ __("Cost code") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Project") }}</th>
									<th class="text-left font-medium px-3 py-2">{{ __("Item") }}</th>
									<th class="text-right font-medium px-3 py-2">{{ __("Issued") }}</th>
									<th class="text-right font-medium px-3 py-2">
										{{ __("At standard rate") }}
									</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(r, i) in consumptionByCostCode"
									:key="i"
									class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
								>
									<td class="px-3 py-2 text-ink-900">{{ r.code }}</td>
									<td class="px-3 py-2 text-ink-700">
										{{ r.project_name || "—" }}
									</td>
									<td class="px-3 py-2 text-ink-700">{{ r.item }}</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">
										{{ inr(r.qty) }}
										<span class="text-[10px] text-ink-500">{{ r.uom }}</span>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ r.value ? fmtINR(r.value) : "—" }}
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr
									class="bg-ink-50 border-t border-ink-200 font-semibold text-ink-900"
								>
									<td class="px-3 py-2" colspan="4">
										{{ __("{0} lines", [consumptionByCostCode.length]) }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums">
										{{ fmtINR(consumptionValue) }}
									</td>
								</tr>
							</tfoot>
						</table>
					</div>
					<div
						v-else
						class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic rounded-lg"
					>
						<template v-if="anyFilter">{{
							__("No lines match these filters.")
						}}</template>
						<template v-else>{{ __("Nothing issued to site yet in scope.") }}</template>
					</div>
					<p class="text-[11px] text-ink-500 mt-2">
						{{
							__(
								"Valued at the item master's standard rate — a list price, not what this particular material cost. Issue valuation needs stock rates, which are not modelled."
							)
						}}
					</p>
				</div>
			</template>
		</template>
	</DeskPage>
</template>
