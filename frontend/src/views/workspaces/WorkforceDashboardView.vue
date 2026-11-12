<script setup>
// Workforce dashboard — workers, crews, man-days and labour cost at a glance. Mirrors the demo:
// KPI strip + recent attendance + recent labour cost.

import { computed, ref, onMounted, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { fmtDate, fmtCompactINR } from "@/utils/format";
import { getWorkforceDashboard } from "@/data/workforceApi";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { DOCSTATUS_LABELS } from "@/utils/workforceForms";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { __, currentLang } from "@/utils/translate";

const router = useRouter();

const today = computed(() =>
	new Date().toLocaleDateString(currentLang(), {
		weekday: "long",
		month: "short",
		day: "numeric",
	})
);

const loading = ref(true);
const error = ref("");
const kpis = ref(null);

async function loadDashboard() {
	loading.value = true;
	error.value = "";
	try {
		kpis.value = await getWorkforceDashboard();
	} catch (e) {
		error.value = e.message || __("Could not load the dashboard.");
	} finally {
		loading.value = false;
	}
}
onMounted(loadDashboard);
// Scoped to the working company, so reload when the switcher changes.
watch(useActiveCompany(), loadDashboard);

const recentAttendance = computed(() => kpis.value?.recent_attendance || []);
const recentLabour = computed(() => kpis.value?.recent_labour || []);
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1 flex items-center gap-2">
					<RouterLink to="/workforce" class="hover:text-brand-700">{{
						__("Workforce")
					}}</RouterLink>
					<span class="text-ink-300">/</span><span>{{ __("Dashboard") }}</span>
					<span class="text-ink-300 mx-2">·</span><span>{{ today }}</span>
				</div>
				<h1 class="text-2xl font-semibold text-ink-900">
					{{ __("Workforce Dashboard") }}
				</h1>
				<p class="text-xs text-ink-500 mt-1">
					{{ __("Workers, crews, man-days and labour cost at a glance.") }}
				</p>
			</div>

			<div v-if="loading" class="text-sm text-ink-500 py-8">{{ __("Loading…") }}</div>
			<div v-else-if="error" class="text-sm text-danger-700 py-8">{{ error }}</div>

			<template v-else-if="kpis">
				<!-- KPI strip -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Active workers") }}
						</div>
						<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
							{{ kpis.active_workers }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							{{ __("In the Field Employee master") }}
						</div>
					</div>
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Active crews") }}
						</div>
						<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
							{{ kpis.active_crews }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							{{ __("Gangs across projects") }}
						</div>
					</div>
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Man-days logged") }}
						</div>
						<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
							{{ kpis.man_days }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							{{ __("From certified attendance") }}
						</div>
					</div>
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Labour cost") }}
						</div>
						<div class="text-2xl font-semibold text-info-700 tabular-nums mt-1.5">
							{{ fmtCompactINR(kpis.labour_cost) }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">
							{{ __("From attendance and timesheets") }}
						</div>
					</div>
				</div>

				<!-- Recent panels -->
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
					<div
						class="card p-0 bg-white border border-ink-200 overflow-hidden rounded-xl"
					>
						<div
							class="px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-brand-50 to-white flex items-center gap-2"
						>
							<WorkspaceIcon
								slug="clipboard-list"
								:size="16"
								:stroke-width="1.75"
								class="text-brand-700"
							/>
							<h2 class="text-sm font-semibold text-ink-900">
								{{ __("Recent attendance") }}
							</h2>
							<RouterLink
								to="/field-attendance"
								class="ml-auto text-xs text-brand-700 hover:underline"
								>{{ __("View all") }} →</RouterLink
							>
						</div>
						<ul v-if="recentAttendance.length" class="divide-y divide-ink-100">
							<li
								v-for="a in recentAttendance"
								:key="a.name"
								class="px-4 py-3 hover:bg-brand-50/30 cursor-pointer"
								@click="router.push(`/field-attendance/${a.name}`)"
							>
								<div class="flex items-baseline justify-between gap-2">
									<span class="text-sm text-ink-900 font-medium truncate">{{
										a.project_name || a.project
									}}</span>
									<span class="text-xs tabular-nums text-ink-700"
										>{{ a.employees_count || 0 }} {{ __("workers") }}</span
									>
								</div>
								<div
									class="text-[11px] text-ink-500 mt-0.5 flex items-center gap-1.5 flex-wrap"
								>
									<StatusBadge
										:status="DOCSTATUS_LABELS[a.docstatus] || 'Draft'"
									/>
									<span class="text-ink-400">· {{ fmtDate(a.date) }}</span>
									<span class="font-mono text-ink-400">· {{ a.name }}</span>
								</div>
							</li>
						</ul>
						<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
							{{ __("No attendance yet.") }}
						</div>
					</div>

					<div
						class="card p-0 bg-white border border-ink-200 overflow-hidden rounded-xl"
					>
						<div
							class="px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-info-50 to-white flex items-center gap-2"
						>
							<WorkspaceIcon
								slug="chart-bar"
								:size="16"
								:stroke-width="1.75"
								class="text-info-700"
							/>
							<h2 class="text-sm font-semibold text-ink-900">
								{{ __("Recent labour cost") }}
							</h2>
							<RouterLink
								to="/labour-attendance"
								class="ml-auto text-xs text-brand-700 hover:underline"
								>{{ __("View all") }} →</RouterLink
							>
						</div>
						<ul v-if="recentLabour.length" class="divide-y divide-ink-100">
							<li v-for="la in recentLabour" :key="la.name" class="px-4 py-3">
								<div class="flex items-baseline justify-between gap-2">
									<span class="text-sm text-ink-900 font-medium truncate">{{
										la.employee_name
									}}</span>
									<span class="text-xs tabular-nums text-ink-900 font-medium">{{
										fmtCompactINR(la.daily_wage_calculated)
									}}</span>
								</div>
								<div class="text-[11px] text-ink-500 mt-0.5 truncate">
									{{ la.project_name || la.project
									}}<template v-if="la.cost_code_label">
										· {{ la.cost_code_label }}</template
									>
									<span class="text-ink-400"
										>· {{ fmtDate(la.attendance_date) }} ·
										{{ la.status }}</span
									>
								</div>
							</li>
						</ul>
						<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
							{{
								__(
									"No labour attendance generated yet — submit a Field Attendance."
								)
							}}
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>
