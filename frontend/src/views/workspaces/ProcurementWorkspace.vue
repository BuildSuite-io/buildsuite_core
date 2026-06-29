<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Material Requests", icon: "clipboard-list", href: "/app/material-request" },
	{ label: "Purchase Orders", icon: "file-text", href: "/app/purchase-order" },
	{ label: "Purchase Receipts", icon: "check-circle", href: "/app/purchase-receipt" },
	{ label: "Material Consumption", icon: "stock", prevent: true },
	{ label: "Suppliers", icon: "building-2", href: "/app/supplier" },
	{ label: "Items & Rates", icon: "tag", to: "/rate-master" },
];

const reports = [
	{
		label: "Stock Balance",
		icon: "chart-bar",
		href: "/app/query-report/Stock Balance",
		desc: "Item-wise on-hand quantity across warehouses.",
	},
	{
		label: "Stock Ledger",
		icon: "file-text",
		href: "/app/query-report/Stock Ledger",
		desc: "Every stock movement — receipts, issues, transfers.",
	},
	{
		label: "Item-wise Purchase Register",
		icon: "clipboard-list",
		href: "/app/query-report/Item-wise Purchase Register",
		desc: "POs and GRNs grouped by item, with value rollups.",
	},
	{
		label: "PO vs GRN variance",
		icon: "chart-line",
		prevent: true,
		desc: "Ordered vs received — flag short / over deliveries.",
	},
	{
		label: "Supplier-wise Purchase",
		icon: "building-2",
		prevent: true,
		desc: "Spend rollup by supplier across the period.",
	},
	{
		label: "Material Consumption by Project",
		icon: "stock",
		prevent: true,
		desc: "How much of each material each project has consumed.",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Procurement</h1>
			</div>

			<!-- Procurement Dashboard CTA tile -->
			<RouterLink
				to="/procurement-dashboard"
				class="mb-5 block bg-brand-50 border border-brand-200 hover:border-brand-400 hover:shadow-sm p-4 rounded-lg transition-all group"
			>
				<div class="flex items-start gap-4">
					<div
						class="w-11 h-11 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center flex-shrink-0"
					>
						<svg
							class="w-[22px] h-[22px]"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('chart-bar')"
						/>
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<div
								class="text-base font-semibold text-ink-900 group-hover:text-brand-700 transition-colors"
							>
								Procurement Dashboard
							</div>
							<span
								class="text-[9px] px-1.5 py-0.5 bg-brand-100 text-brand-700 font-medium uppercase tracking-wider rounded-sm"
								>Live</span
							>
						</div>
						<div class="text-xs text-brand-700 mt-1 leading-snug">
							Open material requests, on-order value, site receipts and rate
							variances at a glance.
						</div>
					</div>
					<div
						class="text-brand-400 group-hover:text-brand-600 transition-colors text-xl"
					>
						→
					</div>
				</div>
			</RouterLink>

			<!-- Shortcuts grid -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				<WorkspaceShortcut
					v-for="sc in shortcuts"
					:key="sc.label"
					:icon="sc.icon"
					:label="sc.label"
					:to="sc.to"
					:href="sc.href"
					:prevent="sc.prevent"
				/>
			</div>

			<!-- Reports group at the bottom -->
			<div class="mt-8">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
					Reports
				</h2>
				<div class="border-t border-ink-200 mb-3"></div>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<WorkspaceShortcut
						v-for="r in reports"
						:key="r.label"
						:icon="r.icon"
						:label="r.label"
						:description="r.desc"
						:to="r.to"
						:href="r.href"
						:prevent="r.prevent"
					>
						<template #badge>
							<span
								class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider"
								style="border-radius: 2px"
								>Report</span
							>
						</template>
					</WorkspaceShortcut>
				</div>
			</div>
		</div>
	</div>
</template>
