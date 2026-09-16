<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import WorkspaceRecordsSection from "@/components/workspaces/WorkspaceRecordsSection.vue";
import WorkspaceReportsSection from "@/components/workspaces/WorkspaceReportsSection.vue";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Material Requests", icon: "clipboard-list", to: "/procurement/material-requests", cap: "materialRequest" },
	{ label: "Purchase Orders", icon: "file-text", to: "/procurement/purchase-orders", cap: "purchaseOrder" },
	{ label: "Purchase Receipts", icon: "check-circle", to: "/procurement/receipts", cap: "purchaseReceipt" },
	// Supplier bills (money out) — opens the Bills register, where direct supplier bills
	// are listed and a new one can be raised. Matches the prototype's "Supplier Bills" tile.
	{ label: "Supplier Bills", icon: "wallet", to: "/project-finance/bills", cap: "supplierBill" },
	{ label: "Material Consumption", icon: "stock", to: "/material-consumption", cap: "materialConsumption" },
	{ label: "Suppliers", icon: "building-2", href: "/app/supplier", cap: "supplier" },
	{ label: "Items", icon: "tag", to: "/items", cap: "item" },
];

// Report tiles are configured per workspace in Workspace Setting.
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
					:cap="sc.cap"
				/>
			</div>

			<WorkspaceRecordsSection workspace="procurement" />

			<WorkspaceReportsSection workspace="procurement" />
		</div>
	</div>
</template>
