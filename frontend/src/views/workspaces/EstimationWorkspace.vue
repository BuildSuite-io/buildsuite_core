<script setup>
// Estimation workspace — date + title, BOQ shortcut, and a "Setup" group.
// Setup has Rate Master + Assembly for now (Estimate Templates come later).

import { computed, ref, onMounted } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceReports } from "@/data/workspaceSettingApi";

const today = computed(() =>
	new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" }),
);

// Report tiles are configured per workspace in Workspace Setting.
const reports = ref([]);
onMounted(async () => {
	try {
		reports.value = await getWorkspaceReports("estimation");
	} catch {
		reports.value = [];
	}
});

const ESTIMATES = [{ to: "/boq", icon: "chart-bar", label: "BOQ" }];
const SETUP = [
	{
		to: "/rate-master",
		icon: "tag",
		label: "Rate Master",
		description: "Price book for materials, labour, and equipment.",
	},
	{
		to: "/assembly",
		icon: "layout-grid",
		label: "Assembly",
		description: "Rate-analysis recipes built from rate-master resources.",
	},
	{
		to: "/estimate-template",
		icon: "file-text",
		label: "Estimate Template",
		description: "Reusable BOQ skeletons of assemblies and resources.",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Estimation</h1>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-8">
				<WorkspaceShortcut
					v-for="sc in ESTIMATES"
					:key="sc.to"
					:to="sc.to"
					:icon="sc.icon"
					:label="sc.label"
				/>
			</div>

			<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
				Setup
			</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				<WorkspaceShortcut
					v-for="sc in SETUP"
					:key="sc.to"
					:to="sc.to"
					:icon="sc.icon"
					:label="sc.label"
					:description="sc.description"
				/>
			</div>

			<!-- Reports group — configured in Workspace Setting -->
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
