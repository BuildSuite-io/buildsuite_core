<script setup>
import { computed, ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { fmtCompactINR, fmtDate } from "@/utils/format";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { getProcurementDashboard } from "@/data/procurementApi";

const today = computed(() =>
	new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
);

const loading = ref(true);
const error = ref("");
const kpis = ref(null);

onMounted(loadDashboard);

async function loadDashboard() {
	loading.value = true;
	error.value = "";
	try {
		kpis.value = await getProcurementDashboard();
	} catch (e) {
		error.value = e.message || "Could not load the dashboard.";
	} finally {
		loading.value = false;
	}
}

function plural(n) {
	return n === 1 ? "" : "s";
}

// Needs-action rows, composed from the API's needs_action block.
const actionRows = computed(() => {
	const na = kpis.value?.needs_action;
	if (!na) return [];
	const overdue = na.deliveries_overdue;
	let overdueSub = "—";
	if (overdue.count && overdue.first) {
		const f = overdue.first;
		overdueSub = `${f.item || "material"} from ${f.supplier} · req. ${fmtDate(f.required_by)}`;
	}
	return [
		{
			key: "approved",
			tone: "info",
			icon: "check-circle",
			label: "Approved requests to order",
			sub: na.approved_to_order.count
				? `Oldest waiting ${na.approved_to_order.oldest_days} day${plural(
						na.approved_to_order.oldest_days
				  )}`
				: "All caught up",
			count: na.approved_to_order.count,
		},
		{
			key: "overdue",
			tone: "danger",
			icon: "refresh-ccw",
			label: "Deliveries overdue",
			sub: overdueSub,
			count: overdue.count,
		},
		{
			key: "partial",
			tone: "warning",
			icon: "chart-bar",
			label: "Partial deliveries",
			sub: na.partial_deliveries.count
				? `${na.partial_deliveries.count} PO${plural(
						na.partial_deliveries.count
				  )} between 1–99% received`
				: "No partial deliveries pending",
			count: na.partial_deliveries.count,
		},
		{
			key: "unbilled",
			tone: "ink",
			icon: "file-text",
			label: "Received, not billed",
			sub: na.received_not_billed.count
				? `${na.received_not_billed.count} GRN${plural(
						na.received_not_billed.count
				  )} awaiting supplier invoice`
				: "All receipts billed",
			count: na.received_not_billed.count,
		},
	];
});

function toneClasses(tone) {
	switch (tone) {
		case "danger":
			return { chip: "bg-danger-50 text-danger-700", count: "text-danger-700" };
		case "warning":
			return { chip: "bg-warning-50 text-warning-700", count: "text-warning-700" };
		case "info":
			return { chip: "bg-info-50 text-info-700", count: "text-info-700" };
		default:
			return { chip: "bg-ink-100 text-ink-700", count: "text-ink-700" };
	}
}

function grnTone(status) {
	if (status === "Full") return "bg-success-50 text-success-700";
	if (status === "Partial") return "bg-warning-50 text-warning-700";
	if (status === "Short") return "bg-danger-50 text-danger-700";
	return "bg-ink-100 text-ink-700";
}
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<!-- Header strip — breadcrumb + date eyebrow + title -->
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1 flex items-center gap-2">
					<RouterLink to="/procurement" class="hover:text-brand-700"
						>Procurement</RouterLink
					>
					<span class="text-ink-300">/</span>
					<span>Dashboard</span>
					<span class="text-ink-300 mx-2">·</span>
					<span>{{ today }}</span>
				</div>
				<h1 class="text-2xl font-semibold text-ink-900">Procurement Dashboard</h1>
				<p class="text-xs text-ink-500 mt-1">
					Open material requests, on-order value, site receipts and rate variances at a
					glance.
				</p>
			</div>

			<!-- Loading / error states -->
			<div v-if="loading" class="text-sm text-ink-500 py-8">Loading…</div>
			<div v-else-if="error" class="text-sm text-danger-700 py-8">{{ error }}</div>

			<template v-else-if="kpis">
				<!-- ===== KPI strip ===== -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
					<!-- 1 — Open material requests -->
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Open material requests
						</div>
						<div class="flex items-baseline gap-2 mt-1.5">
							<div class="text-2xl font-semibold text-ink-900 tabular-nums">
								{{ kpis.open_material_requests.count }}
							</div>
							<div class="text-xs text-ink-500 tabular-nums">
								{{ fmtCompactINR(kpis.open_material_requests.value) }}
							</div>
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							Pending + Approved + Partially Ordered
						</div>
					</div>

					<!-- 2 — On order · awaiting delivery -->
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							On order · awaiting delivery
						</div>
						<div class="flex items-baseline gap-2 mt-1.5">
							<div class="text-2xl font-semibold text-ink-900 tabular-nums">
								{{ kpis.on_order.count }}
							</div>
							<div class="text-xs text-ink-500 tabular-nums">
								{{ fmtCompactINR(kpis.on_order.value) }}
							</div>
						</div>
						<div class="text-[10px] text-ink-400 mt-1">POs not yet fully received</div>
					</div>

					<!-- 3 — Received this week -->
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Received this week
						</div>
						<div class="text-2xl font-semibold text-success-700 tabular-nums mt-1.5">
							{{ kpis.received_this_week.count }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							Goods receipts in last 7 days
						</div>
					</div>

					<!-- 4 — Above estimated rate -->
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Above estimated rate
						</div>
						<div
							class="text-2xl font-semibold tabular-nums mt-1.5"
							:class="
								kpis.above_estimated_rate.count > 0
									? 'text-warning-700'
									: 'text-ink-900'
							"
						>
							{{ kpis.above_estimated_rate.count }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							PO line items priced above Rate Master
						</div>
					</div>
				</div>

				<!-- ===== Needs action + Recent receipts band ===== -->
				<div class="grid grid-cols-1 lg:grid-cols-[1.35fr_1fr] gap-4 mb-6">
					<!-- Left — Needs action -->
					<div
						class="card p-0 bg-white border border-ink-200 overflow-hidden rounded-xl"
					>
						<div
							class="px-4 py-3 border-b border-ink-100 flex items-center gap-2 bg-gradient-to-r from-success-50 to-white"
						>
							<svg
								class="w-4 h-4 text-success-700"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('check-circle')"
							/>
							<h2 class="text-sm font-semibold text-ink-900">Needs action</h2>
							<span class="ml-auto text-[11px] text-ink-500">Today</span>
						</div>
						<ul class="divide-y divide-ink-100">
							<li
								v-for="row in actionRows"
								:key="row.key"
								class="px-4 py-3 flex items-center gap-3"
							>
								<span
									:class="[
										'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
										toneClasses(row.tone).chip,
									]"
								>
									<svg
										class="w-4 h-4"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.75"
										stroke-linecap="round"
										stroke-linejoin="round"
										aria-hidden="true"
										v-html="getWorkspaceIconPath(row.icon)"
									/>
								</span>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-medium text-ink-900 truncate">
										{{ row.label }}
									</div>
									<div class="text-[11px] text-ink-500 truncate mt-0.5">
										{{ row.sub }}
									</div>
								</div>
								<span
									:class="[
										'text-base font-semibold tabular-nums flex-shrink-0',
										toneClasses(row.tone).count,
									]"
									>{{ row.count }}</span
								>
								<span class="text-ink-300">›</span>
							</li>
						</ul>
					</div>

					<!-- Right — Recent site receipts -->
					<div
						class="card p-0 bg-white border border-ink-200 overflow-hidden rounded-xl"
					>
						<div class="px-4 py-3 border-b border-ink-100 flex items-center gap-2">
							<svg
								class="w-4 h-4 text-ink-500"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('paperclip')"
							/>
							<h2 class="text-sm font-semibold text-ink-900">
								Recent site receipts
							</h2>
							<a
								href="/app/purchase-receipt"
								class="ml-auto text-xs text-brand-700 hover:underline"
								>View all →</a
							>
						</div>
						<ul v-if="kpis.recent_receipts.length" class="divide-y divide-ink-100">
							<li
								v-for="grn in kpis.recent_receipts"
								:key="grn.name"
								class="px-4 py-3 flex items-center gap-3"
							>
								<div class="flex-1 min-w-0">
									<div
										class="text-sm font-medium flex items-center gap-1.5 min-w-0"
									>
										<span class="text-ink-900 truncate">
											{{ grn.items[0]?.item || "—" }}
											<span class="text-ink-500 font-normal">·</span>
											<span class="text-ink-500 font-normal tabular-nums"
												>{{ grn.items[0]?.qty }}
												{{ grn.items[0]?.uom }}</span
											>
										</span>
										<span
											v-if="grn.item_count > 1"
											class="flex-shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-ink-100 text-ink-700 whitespace-nowrap"
											>+{{ grn.item_count - 1 }} more</span
										>
									</div>
									<div class="text-[11px] text-ink-500 mt-0.5 truncate">
										{{ grn.project }} · {{ grn.supplier }} ·
										{{ fmtDate(grn.posting_date) }} · {{ grn.name }}
									</div>
								</div>
								<span
									:class="[
										'text-[10px] px-2 py-0.5 rounded-full font-medium flex-shrink-0',
										grnTone(grn.status),
									]"
									>{{ grn.status }}</span
								>
							</li>
						</ul>
						<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
							No goods receipts recorded yet.
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>
