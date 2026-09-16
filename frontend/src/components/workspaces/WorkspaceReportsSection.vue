<script setup>
// The "Reports" group for a workspace — report tiles configured per workspace in
// Workspace Setting, each opening the report's route (in-app or, when `external`, a
// Desk URL). Extracted from the individual workspace landings (Estimation, Procurement,
// Workforce, Subcontract, Site Execution) so they share one implementation — including
// the loading skeleton, which replaces the previous blank-gap-then-pop-in.
//
// `enabled` lets a caller gate the whole group behind an extra condition (Project Finance
// only shows reports once ledger finance is available); it stays hidden while false.
import { ref, computed, onMounted } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import TileGridSkeleton from "@/components/workspaces/TileGridSkeleton.vue";
import { getWorkspaceReports } from "@/data/workspaceSettingApi";

const props = defineProps({
	workspace: { type: String, required: true },
	enabled: { type: Boolean, default: true },
	// Top margin utility — landings use mt-8; a caller mid-layout can pass e.g. "mb-4".
	spacing: { type: String, default: "mt-8" },
});

const reports = ref([]);
const loading = ref(true);

onMounted(async () => {
	try {
		reports.value = await getWorkspaceReports(props.workspace);
	} catch {
		reports.value = [];
	} finally {
		loading.value = false;
	}
});

const show = computed(() => props.enabled && (loading.value || reports.value.length > 0));
</script>

<template>
	<div v-if="show" :class="spacing">
		<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">Reports</h2>
		<div class="border-t border-ink-200 mb-3"></div>
		<TileGridSkeleton v-if="loading" :count="3" with-description />
		<div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
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
</template>
