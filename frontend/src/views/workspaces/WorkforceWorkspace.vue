<script setup>
// Workforce landing — greeting, a DocType shortcuts grid, and a Reports group.

import { computed } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import WorkspaceReportsSection from "@/components/workspaces/WorkspaceReportsSection.vue";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Field Employees", icon: "hard-hat", to: "/field-employees", cap: "fieldEmployee" },
	{ label: "Crews", icon: "users-2", to: "/crews", cap: "crew" },
	{ label: "Field Attendance", icon: "clipboard-list", to: "/field-attendance", cap: "fieldAttendance" },
];

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

			<WorkspaceReportsSection workspace="workforce" />
		</div>
	</div>
</template>
