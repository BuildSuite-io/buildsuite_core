<script setup>
// Workforce landing. Tiles without a `to` render as `prevent` until their page
// exists. Reports stay hardcoded until "workforce" joins the WORKSPACES
// allowlist in buildsuite_core/api/workspace_setting.py.

import { computed } from "vue";
import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

const shortcuts = [
	{ label: "Field Employees", icon: "hard-hat", to: "/field-employees" },
	{ label: "Crews", icon: "users-2", to: "/crews" },
	{ label: "Field Attendance", icon: "clipboard-list", to: "/field-attendance" },
];

const reports = [
	{
		label: "Labour Attendance Register",
		icon: "clipboard-list",
		description: "Per-worker daily wages — Full Day / Half Day / Absent.",
		to: "/labour-attendance",
	},
	{
		label: "Overtime Attendance Register",
		icon: "chart-line",
		description: "Per-worker overtime hours × overtime rate.",
		to: "/overtime-attendance",
	},
];
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Workforce</h1>
			</div>

			<!-- Workforce Dashboard CTA tile -->
			<RouterLink
				to="/workforce-dashboard"
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
						<!-- No "Live" badge yet — the dashboard is still a shell. Add it
						     back when get_dashboard() feeds real numbers. -->
						<div class="flex items-center gap-2">
							<div
								class="text-base font-semibold text-ink-900 group-hover:text-brand-700 transition-colors"
							>
								Workforce Dashboard
							</div>
						</div>
						<div class="text-xs text-brand-700 mt-1 leading-snug">
							Workers, crews, man-days and labour cost at a glance.
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
					:to="sc.to || null"
					:prevent="!sc.to"
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
						v-for="r in reports"
						:key="r.label"
						:icon="r.icon"
						:label="r.label"
						:description="r.description"
						:to="r.to || null"
						:prevent="!r.to"
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
