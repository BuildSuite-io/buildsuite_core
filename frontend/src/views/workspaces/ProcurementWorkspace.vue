<script setup>
import { computed } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Material Requests", icon: "clipboard-list", href: "/app/material-request" },
	{ label: "Purchase Orders", icon: "file-text", href: "/app/purchase-order" },
	{ label: "Purchase Receipts", icon: "check-circle", href: "/app/purchase-receipt" },
	{ label: "Material Consumption", icon: "package", prevent: true },
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
		icon: "package",
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
