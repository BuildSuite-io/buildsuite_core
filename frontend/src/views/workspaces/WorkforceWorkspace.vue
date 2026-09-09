<script setup>
// Workforce landing — greeting, a DocType shortcuts grid, and a Reports group.

import { computed, ref, onMounted } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceReports } from "@/data/workspaceSettingApi";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Field Employees", icon: "hard-hat", to: "/field-employees", cap: "fieldEmployee" },
	{ label: "Crews", icon: "users-2", to: "/crews", cap: "crew" },
	{ label: "Field Attendance", icon: "clipboard-list", to: "/field-attendance", cap: "fieldAttendance" },
];

// Report tiles are configured per workspace in Workspace Setting.
const reports = ref([]);
onMounted(async () => {
	try {
		reports.value = await getWorkspaceReports("workforce");
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
				<h1 class="text-2xl font-semibold text-ink-900">Workforce</h1>
			</div>

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
