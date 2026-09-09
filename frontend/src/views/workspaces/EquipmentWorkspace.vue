<script setup>
// Equipment (plant & machinery) workspace landing — mirrors the demo. The Machinery /
// Machinery Usage shortcuts and the Equipment Dashboard tile navigate; the two report tiles
// open the Machinery Utilisation (usage log) and Equipment Register (machinery) reports.
import { computed } from "vue";
import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Machinery Register", icon: "wrench", to: "/machinery", cap: "machinery" },
	{ label: "Machinery Usage", icon: "clipboard-list", to: "/machinery-usage", cap: "machineryUsage" },
];

// Fuel & running cost was dropped (prototype S314): fuel is captured per usage entry and
// already carried in the utilisation total, so a separate report would only re-slice one column.
const reports = [
	{
		label: "Machinery utilisation",
		icon: "chart-bar",
		description: "Plant usage + cost by project / task.",
		to: "/machinery-usage",
	},
	{
		label: "Equipment register",
		icon: "wrench",
		description: "Owned + hired plant with rates.",
		to: "/machinery",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Equipment</h1>
			</div>

			<!-- Equipment Dashboard CTA tile -->
			<RouterLink
				to="/equipment-dashboard"
				class="mb-5 block bg-brand-50 border border-brand-200 hover:border-brand-400 hover:shadow-sm p-4 rounded-lg group transition-all"
			>
				<div class="flex items-start gap-4">
					<div
						class="w-11 h-11 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center flex-shrink-0"
					>
						<svg
							class="w-5 h-5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
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
								Equipment Dashboard
							</div>
							<span
								class="text-[9px] px-1.5 py-0.5 bg-brand-100 text-brand-700 font-medium uppercase tracking-wider"
								style="border-radius: 2px"
								>Live</span
							>
						</div>
						<div class="text-xs text-brand-700 mt-1 leading-snug">
							Plant register, utilisation and equipment cost at a glance.
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
					:cap="sc.cap"
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
						v-for="(r, i) in reports"
						:key="i"
						:icon="r.icon"
						:label="r.label"
						:description="r.description"
						:to="r.prevent ? null : r.to"
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
