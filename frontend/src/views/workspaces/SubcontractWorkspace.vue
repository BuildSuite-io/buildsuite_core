<script setup>
// Subcontract workspace landing — mirrors the prototype's
// SubcontractorWorkspace: greeting strip, a prominent Subcontractor
// Dashboard CTA, a DocType shortcuts grid, and a Reports group.
//
// First pass ships Subcontractors + Work Orders. Measurement Books and
// RA Bills land in a later pass — their tiles are omitted until then.

import { computed } from "vue";
import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Subcontractors", icon: "users-2", to: "/subcontractors" },
	{ label: "Work Orders", icon: "clipboard-list", to: "/subcontractor-work-orders" },
];

const reports = [
	{
		label: "Work Order Register",
		icon: "clipboard-list",
		to: "/subcontractor-work-orders",
		desc: "Every WO across projects with status + committed value.",
	},
	{
		label: "Subcontractor Ledger",
		icon: "chart-line",
		prevent: true,
		desc: "Per-sub view: WOs committed + bills paid + retention held.",
	},
	{
		label: "Cost code variance",
		icon: "chart-bar",
		prevent: true,
		desc: "Planned vs Committed vs Actual per BOQ group code.",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Subcontractors</h1>
			</div>

			<!-- Subcontractor Dashboard CTA tile -->
			<RouterLink
				to="/subcontract-dashboard"
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
								Subcontractor Dashboard
							</div>
							<span
								class="text-[9px] px-1.5 py-0.5 bg-brand-100 text-brand-700 font-medium uppercase tracking-wider rounded-sm"
								>Live</span
							>
						</div>
						<div class="text-xs text-brand-700 mt-1 leading-snug">
							Open commitments, work order momentum and active subcontractors at a
							glance.
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
				/>
			</div>

			<!-- Reports group -->
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
