<script setup>
import { computed, ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { getWorkspaceReports } from "@/data/workspaceSettingApi";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Material Requests", icon: "clipboard-list", to: "/procurement/material-requests" },
	{ label: "Purchase Orders", icon: "file-text", to: "/procurement/purchase-orders" },
	{ label: "Purchase Receipts", icon: "check-circle", to: "/procurement/receipts" },
	// Supplier bills (money out) — opens the Bills register, where direct supplier bills
	// are listed and a new one can be raised. Matches the prototype's "Supplier Bills" tile.
	{ label: "Supplier Bills", icon: "wallet", to: "/project-finance/bills" },
	{
		label: "Material Consumption",
		icon: "stock",
		href: "/app/stock-entry?stock_entry_type=Material Issue",
	},
	{ label: "Suppliers", icon: "building-2", href: "/app/supplier" },
	{ label: "Items", icon: "tag", to: "/items" },
];

// Report tiles are configured per workspace in Workspace Setting.
const reports = ref([]);
onMounted(async () => {
	try {
		reports.value = await getWorkspaceReports("procurement");
	} catch {
		reports.value = [];
	}
});
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
			<div v-if="reports.length" class="mt-8">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
					Reports
				</h2>
				<div class="border-t border-ink-200 mb-3"></div>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<WorkspaceShortcut
						v-for="(r, i) in reports"
						:key="i"
						:icon="r.icon"
						:label="r.label"
						:description="r.description"
						:to="r.external ? null : r.route"
						:href="r.external ? r.route : null"
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
