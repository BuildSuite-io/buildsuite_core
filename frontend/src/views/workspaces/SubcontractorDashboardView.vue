<script setup>
// Subcontractor Dashboard — rolls the Work Order, Subcontractor, Measurement
// Book and Subcontractor Bill slices into KPI cards + recent-activity panels.
// Mirrors the prototype's SubcontractorDashboardView. All lists come through
// useDocTypeList (get_list), so counts + totals are permission-scoped to the
// projects the signed-in user can see.

import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR, fmtCompactINR } from "@/utils/format";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const { projectName } = useProjectNames();

const wosRes = useDocTypeList("Subcontractor Work Order", {
	fields: [
		"name",
		"subcontractor_name",
		"project",
		"date",
		"delivery_type",
		"total_value",
		"status",
		"modified",
	],
	orderBy: "modified desc",
	pageLength: 0,
	cache: "buildsuite-subcontract-wo-dashboard",
});
const subsRes = useDocTypeList("Supplier", {
	fields: ["name", "supplier_name", "disabled"],
	filters: [["supplier_type", "=", "Subcontractor"]],
	orderBy: "supplier_name asc",
	pageLength: 0,
	cache: "buildsuite-subcontractor-dashboard",
});
const mbsRes = useDocTypeList("Measurement Book", {
	fields: ["name", "project", "work_order", "date", "measured_total", "status"],
	orderBy: "date desc",
	pageLength: 0,
	cache: "buildsuite-measurement-book-dashboard",
});
const billsRes = useDocTypeList("Subcontractor Bill", {
	fields: [
		"name",
		"ra_no",
		"subcontractor_name",
		"project",
		"work_order",
		"date",
		"status",
		"gross",
		"retention_amount",
		"net_payable",
		"modified",
	],
	orderBy: "modified desc",
	pageLength: 0,
	cache: "buildsuite-subcontractor-bill-dashboard",
});

const wos = computed(() => wosRes.data || []);
const subs = computed(() => subsRes.data || []);
const bills = computed(() => billsRes.data || []);
const recentMBs = computed(() => (mbsRes.data || []).slice(0, 5));
const recentWorkOrders = computed(() => wos.value.slice(0, 6));
const recentBills = computed(() => bills.value.slice(0, 6));

const openWos = computed(() =>
	wos.value.filter((w) => w.status === "Awarded" || w.status === "In Progress")
);
const openWosValue = computed(() =>
	openWos.value.reduce((a, w) => a + (Number(w.total_value) || 0), 0)
);
const activeSubs = computed(() => subs.value.filter((s) => !s.disabled).length);

const totalBilledToDate = computed(() =>
	bills.value.reduce((a, b) => a + (Number(b.gross) || 0), 0)
);
const totalRetentionHeld = computed(() =>
	bills.value.reduce((a, b) => a + (Number(b.retention_amount) || 0), 0)
);

// Billed-to-date rolled up per work order, so each WO row can show progress.
const billedByWorkOrder = computed(() => {
	const map = {};
	for (const b of bills.value) {
		if (!b.work_order) continue;
		map[b.work_order] = (map[b.work_order] || 0) + (Number(b.gross) || 0);
	}
	return map;
});
function woBilled(name) {
	return billedByWorkOrder.value[name] || 0;
}
function woPercent(wo) {
	const total = Number(wo.total_value) || 0;
	if (total <= 0) return 0;
	return Math.round((woBilled(wo.name) / total) * 100);
}
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<!-- Header strip -->
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1 flex items-center gap-2">
					<RouterLink to="/subcontract" class="hover:text-brand-700"
						>Subcontractors</RouterLink
					>
					<span class="text-ink-300">/</span>
					<span>Dashboard</span>
					<span class="text-ink-300 mx-2">·</span>
					<span>{{ today }}</span>
				</div>
				<h1 class="text-2xl font-semibold text-ink-900">Subcontractor Dashboard</h1>
				<p class="text-xs text-ink-500 mt-1">
					Open commitments, billing momentum, and certified measurements at a glance.
				</p>
			</div>

			<!-- KPI strip -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
				<div class="p-4 bg-white border border-ink-200 rounded-lg">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Open work orders
					</div>
					<div class="flex items-baseline gap-2 mt-1.5">
						<div class="text-2xl font-semibold text-ink-900 tabular-nums">
							{{ openWos.length }}
						</div>
						<div class="text-xs text-ink-500 tabular-nums">
							{{ fmtCompactINR(openWosValue) }}
						</div>
					</div>
					<div class="text-[10px] text-ink-400 mt-1">Awarded · In Progress</div>
				</div>
				<div class="p-4 bg-white border border-ink-200 rounded-lg">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Billed to date
					</div>
					<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
						{{ fmtCompactINR(totalBilledToDate) }}
					</div>
					<div class="text-[10px] text-ink-400 mt-1">Sum across all bills</div>
				</div>
				<div class="p-4 bg-white border border-ink-200 rounded-lg">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Retention held
					</div>
					<div class="text-2xl font-semibold text-warning-700 tabular-nums mt-1.5">
						{{ fmtCompactINR(totalRetentionHeld) }}
					</div>
					<div class="text-[10px] text-ink-400 mt-1">
						Withheld pending defect-liability period
					</div>
				</div>
				<div class="p-4 bg-white border border-ink-200 rounded-lg">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Active subcontractors
					</div>
					<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
						{{ activeSubs }}
					</div>
					<div class="text-[10px] text-ink-400 mt-1">In the master</div>
				</div>
			</div>

			<!-- Recent work orders + Recent bills -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
				<!-- Recent work orders -->
				<div class="bg-white border border-ink-200 overflow-hidden rounded-xl">
					<div
						class="px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-brand-50 to-white flex items-center gap-2"
					>
						<svg
							class="w-4 h-4 text-brand-700"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							v-html="getWorkspaceIconPath('clipboard-list')"
						/>
						<h2 class="text-sm font-semibold text-ink-900">Recent work orders</h2>
						<RouterLink
							to="/subcontractor-work-orders"
							class="ml-auto text-xs text-brand-700 hover:underline"
							>View all →</RouterLink
						>
					</div>
					<ul v-if="recentWorkOrders.length" class="divide-y divide-ink-100">
						<li v-for="wo in recentWorkOrders" :key="wo.name" class="px-4 py-3">
							<div class="flex items-baseline justify-between gap-2">
								<RouterLink
									:to="`/subcontractor-work-orders/${wo.name}`"
									class="text-sm text-ink-900 font-medium hover:text-brand-700 truncate"
								>
									{{ wo.subcontractor_name || wo.name }}
								</RouterLink>
								<span class="text-xs tabular-nums text-ink-700">{{
									fmtCompactINR(wo.total_value)
								}}</span>
							</div>
							<div
								class="text-[11px] text-ink-500 mt-0.5 truncate flex items-center gap-1.5 flex-wrap"
							>
								<StatusBadge :status="wo.status" size="xs" />
								<span>· {{ projectName(wo.project) }}</span>
								<span class="text-ink-400">· {{ fmtDate(wo.date) }}</span>
								<span v-if="wo.delivery_type" class="text-ink-400"
									>· {{ wo.delivery_type }}</span
								>
							</div>
							<div class="text-[11px] text-ink-500 mt-0.5">
								<span class="text-ink-700 tabular-nums">{{ woPercent(wo) }}%</span>
								billed ·
								<span class="tabular-nums">{{
									fmtCompactINR(woBilled(wo.name))
								}}</span>
							</div>
						</li>
					</ul>
					<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
						{{
							wosRes.loading ? "Loading work orders…" : "No work orders raised yet."
						}}
					</div>
				</div>

				<!-- Recent bills -->
				<div class="bg-white border border-ink-200 overflow-hidden rounded-xl">
					<div
						class="px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-warning-50 to-white flex items-center gap-2"
					>
						<svg
							class="w-4 h-4 text-warning-700"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							v-html="getWorkspaceIconPath('file-text')"
						/>
						<h2 class="text-sm font-semibold text-ink-900">
							Recent subcontractor bills
						</h2>
						<RouterLink
							to="/subcontractor-bills"
							class="ml-auto text-xs text-brand-700 hover:underline"
							>View all →</RouterLink
						>
					</div>
					<ul v-if="recentBills.length" class="divide-y divide-ink-100">
						<li v-for="b in recentBills" :key="b.name" class="px-4 py-3">
							<div class="flex items-baseline justify-between gap-2">
								<RouterLink
									:to="`/subcontractor-bills/${b.name}`"
									class="text-sm text-ink-900 font-medium hover:text-brand-700 truncate"
								>
									RA {{ b.ra_no }} · {{ b.subcontractor_name || b.name }}
								</RouterLink>
								<span class="text-xs tabular-nums text-ink-700">{{
									fmtCompactINR(b.gross)
								}}</span>
							</div>
							<div
								class="text-[11px] text-ink-500 mt-0.5 truncate flex items-center gap-1.5 flex-wrap"
							>
								<StatusBadge :status="b.status" size="xs" />
								<span>· {{ projectName(b.project) }}</span>
								<span class="text-ink-400">· {{ fmtDate(b.date) }}</span>
							</div>
							<div class="text-[11px] text-ink-500 mt-0.5 tabular-nums">
								Retention
								<span class="text-warning-700 font-medium">{{
									fmtINR(b.retention_amount)
								}}</span>
								· Net payable
								<span class="text-ink-900 font-medium">{{
									fmtINR(b.net_payable)
								}}</span>
							</div>
						</li>
					</ul>
					<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
						{{ billsRes.loading ? "Loading bills…" : "No bills raised yet." }}
					</div>
				</div>
			</div>

			<!-- Recent measurement books -->
			<div class="bg-white border border-ink-200 overflow-hidden rounded-xl mb-6">
				<div
					class="px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-info-50/40 to-white flex items-center gap-2"
				>
					<svg
						class="w-4 h-4 text-info-700"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						stroke-linecap="round"
						stroke-linejoin="round"
						v-html="getWorkspaceIconPath('chart-bar')"
					/>
					<h2 class="text-sm font-semibold text-ink-900">Recent measurement books</h2>
					<RouterLink
						to="/measurement-books"
						class="ml-auto text-xs text-brand-700 hover:underline"
						>View all →</RouterLink
					>
				</div>
				<ul v-if="recentMBs.length" class="divide-y divide-ink-100">
					<li
						v-for="mb in recentMBs"
						:key="mb.name"
						class="px-4 py-3 flex items-center gap-3"
					>
						<div class="flex-1 min-w-0">
							<div class="flex items-baseline gap-2">
								<RouterLink
									:to="`/measurement-books/${mb.name}`"
									class="text-sm text-ink-900 font-medium hover:text-brand-700 truncate"
									>{{ mb.name }}</RouterLink
								>
								<StatusBadge :status="mb.status" size="xs" />
							</div>
							<div class="text-[11px] text-ink-500 mt-0.5 truncate">
								{{ projectName(mb.project) }} ·
								<RouterLink
									:to="`/subcontractor-work-orders/${mb.work_order}`"
									class="text-brand-700 hover:underline"
									>{{ mb.work_order }}</RouterLink
								>
								· {{ fmtDate(mb.date) }}
							</div>
						</div>
						<div
							class="text-sm font-semibold text-info-700 tabular-nums whitespace-nowrap"
						>
							{{ Number(mb.measured_total || 0).toLocaleString("en-IN") }}
						</div>
					</li>
				</ul>
				<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
					{{
						mbsRes.loading
							? "Loading measurement books…"
							: "No measurements recorded yet."
					}}
				</div>
			</div>
		</div>
	</div>
</template>
