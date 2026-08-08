<script setup>
// Workforce dashboard — shell only. Fill the em-dashes by adding
// buildsuite_core/api/workforce.py::get_dashboard(), copying api/equipment.py.

import { computed } from "vue";
import { RouterLink } from "vue-router";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const today = computed(() =>
	new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
);
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1 flex items-center gap-2">
					<RouterLink to="/workforce" class="hover:text-brand-700">Workforce</RouterLink>
					<span class="text-ink-300">/</span>
					<span>Dashboard</span>
					<span class="text-ink-300 mx-2">·</span>
					<span>{{ today }}</span>
				</div>
				<h1 class="text-2xl font-semibold text-ink-900">Workforce Dashboard</h1>
				<p class="text-xs text-ink-500 mt-1">
					Workers, crews, man-days and labour cost at a glance.
				</p>
			</div>

			<!-- ===== KPI strip ===== -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
				<div class="card p-4 bg-white border border-ink-200">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Active workers
					</div>
					<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">—</div>
					<div class="text-[10px] text-ink-400 mt-1">In the Field Employee master</div>
				</div>

				<div class="card p-4 bg-white border border-ink-200">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Active crews
					</div>
					<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">—</div>
					<div class="text-[10px] text-ink-400 mt-1">Gangs across projects</div>
				</div>

				<div class="card p-4 bg-white border border-ink-200">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Man-days logged
					</div>
					<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">—</div>
					<div class="text-[10px] text-ink-400 mt-1">From certified attendance</div>
				</div>

				<div class="card p-4 bg-white border border-ink-200">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Labour cost
					</div>
					<div class="text-2xl font-semibold text-info-700 tabular-nums mt-1.5">—</div>
					<div class="text-[10px] text-ink-400 mt-1">Task-level, from attendance</div>
				</div>
			</div>

			<!-- ===== Panels ===== -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<!-- Recent attendance -->
				<div class="card border border-ink-200">
					<div
						class="flex items-center gap-2 px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-brand-50 to-white"
					>
						<svg
							class="w-4 h-4 text-brand-700"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('clipboard-list')"
						/>
						<h2 class="text-sm font-semibold text-ink-900">Recent attendance</h2>
					</div>
					<div class="px-4 py-6 text-sm text-ink-400">No attendance yet.</div>
				</div>

				<!-- Recent labour cost -->
				<div class="card border border-ink-200">
					<div
						class="flex items-center gap-2 px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-info-50 to-white"
					>
						<svg
							class="w-4 h-4 text-info-700"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('chart-bar')"
						/>
						<h2 class="text-sm font-semibold text-ink-900">Recent labour cost</h2>
					</div>
					<div class="px-4 py-6 text-sm text-ink-400">
						No labour attendance generated yet — submit a Field Attendance.
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
