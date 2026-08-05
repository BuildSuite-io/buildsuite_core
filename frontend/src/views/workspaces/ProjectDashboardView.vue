<script setup>
// Project Dashboard — the Site Execution owner/PM view (S251). Live over
// buildsuite_core.api.project_dashboard, scoped to the whole portfolio or one project:
// KPIs + earned value, project health, cost booked by head, the decision queue, site
// activity (7d), commitments, and a needs-attention list. Everything derived server-side —
// this view renders and re-fetches on scope change.
import { ref, computed, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { getProjectDashboard } from "@/data/projectDashboardApi";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { fmtCompactINR, fmtDate } from "@/utils/format";

const data = ref(null);
const loading = ref(true);
const error = ref("");
const scope = ref(""); // "" = portfolio, else a project id

const todayLabel = new Date().toLocaleDateString("en-IN", {
	weekday: "long",
	day: "2-digit",
	month: "short",
	year: "numeric",
});

async function load() {
	loading.value = true;
	error.value = "";
	try {
		data.value = await getProjectDashboard(scope.value || undefined);
	} catch (err) {
		error.value = err.message || "Failed to load the dashboard.";
	} finally {
		loading.value = false;
	}
}
function setScope(v) {
	scope.value = v || "";
	load();
}
onMounted(load);

const kpis = computed(() => data.value?.kpis || {});
const health = computed(() => data.value?.health || []);
const cost = computed(() => data.value?.cost || { total_actual: 0, heads: [] });
const decision = computed(() => data.value?.decision || []);
const commitments = computed(() => data.value?.commitments || {});
const activity = computed(() => data.value?.activity || { recent: [] });
const attention = computed(() => data.value?.attention || []);
const showAllProjects = computed(() => (data.value?.total_projects || 0) > health.value.length);
const activityQuiet = computed(
	() => !activity.value.entries && !activity.value.man_days && !activity.value.receipts
);

function progressTone(r) {
	if (r.variance > 10) return "bg-danger-500";
	if (r.variance > 0) return "bg-warning-500";
	return "bg-success-500";
}
// One schedule figure per row — late wins when late; else time remaining.
function schedule(r) {
	if (r.progress >= 100) return { text: "Complete", tone: "text-success-700" };
	if (r.delayed > 0) return { text: `${r.delayed}d late`, tone: "text-danger-700 font-medium" };
	if (r.days_to_end === null || r.days_to_end === undefined)
		return { text: "No end date", tone: "text-ink-400" };
	if (r.days_to_end < 0)
		return { text: `${-r.days_to_end}d over`, tone: "text-danger-700 font-medium" };
	return { text: `${r.days_to_end}d left`, tone: "text-ink-700" };
}
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-7xl mx-auto px-6 py-8">
			<!-- Breadcrumb -->
			<div class="text-[11px] text-ink-500 mb-3">
				<RouterLink to="/site-execution" class="hover:underline"
					>Site Execution</RouterLink
				>
				<span class="mx-1">›</span>
				<span class="text-ink-700">Project Dashboard</span>
			</div>

			<!-- Title + scope picker -->
			<div class="flex flex-wrap items-end justify-between gap-4 mb-8">
				<div>
					<div
						class="text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
					>
						{{ scope ? "Project overview" : "Portfolio overview" }}
					</div>
					<h1 class="text-2xl font-semibold text-ink-900 tracking-tight">
						Project Dashboard
					</h1>
					<p class="text-sm text-ink-500 mt-1">{{ todayLabel }}</p>
				</div>
				<div class="flex items-center gap-2">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Scope</span
					>
					<div class="w-56">
						<DeskLinkPicker
							:model-value="scope"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							placeholder="All projects"
							@update:model-value="setScope"
						/>
					</div>
					<button
						v-if="scope"
						type="button"
						class="text-[11px] text-brand-600 hover:underline whitespace-nowrap"
						@click="setScope('')"
					>
						Portfolio
					</button>
				</div>
			</div>

			<div v-if="loading" class="py-20 text-center text-sm text-ink-400">
				Loading portfolio…
			</div>
			<div
				v-else-if="error"
				class="bg-danger-50 border border-danger-200 rounded-lg px-4 py-6 text-sm text-danger-700"
			>
				{{ error }}
			</div>

			<template v-else>
				<!-- ===== KPI strip ===== -->
				<div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
					<div class="bg-white border border-ink-200 rounded-xl p-4">
						<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
							Active projects
						</div>
						<div class="text-2xl font-semibold text-ink-900 mt-1 tabular-nums">
							{{ kpis.active_projects }}
						</div>
						<div
							class="text-[11px] mt-1"
							:class="
								kpis.at_risk ? 'text-danger-700 font-medium' : 'text-success-700'
							"
						>
							{{ kpis.at_risk }} at risk
						</div>
					</div>

					<div class="bg-white border border-ink-200 rounded-xl p-4">
						<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
							Contract value
						</div>
						<div
							class="text-2xl font-semibold text-ink-900 mt-1 tabular-nums whitespace-nowrap"
						>
							{{ fmtCompactINR(kpis.contract_value) }}
						</div>
						<div class="text-[11px] text-ink-400 mt-1">Approved BOQ, else budget</div>
					</div>

					<div class="bg-white border border-ink-200 rounded-xl p-4">
						<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
							Work done
						</div>
						<div
							class="text-2xl font-semibold text-ink-900 mt-1 tabular-nums whitespace-nowrap"
						>
							{{ fmtCompactINR(kpis.work_done) }}
						</div>
						<div class="text-[11px] text-ink-400 mt-1 tabular-nums">
							<template v-if="kpis.boq_with < kpis.boq_total"
								>from {{ kpis.boq_with }} of {{ kpis.boq_total }} with a
								BOQ</template
							>
							<template v-else>{{ kpis.earned_pct }}% of contract value</template>
						</div>
					</div>

					<div class="bg-white border border-ink-200 rounded-xl p-4">
						<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
							Schedule
						</div>
						<div class="flex items-baseline gap-1 mt-1 tabular-nums">
							<span class="text-2xl font-semibold text-ink-900"
								>{{ kpis.avg_progress }}%</span
							>
							<span class="text-sm text-ink-400"
								>vs {{ kpis.avg_expected }}% planned</span
							>
						</div>
						<div
							class="text-[11px] mt-1"
							:class="
								kpis.behind ? 'text-danger-700 font-medium' : 'text-success-700'
							"
						>
							<template v-if="kpis.behind"
								>{{ kpis.behind }} behind · worst {{ kpis.worst_delay }}d</template
							>
							<template v-else>All on or ahead of plan</template>
						</div>
					</div>
				</div>

				<!-- ===== Project health ===== -->
				<div class="bg-white border border-ink-200 rounded-xl overflow-hidden mt-6">
					<div
						class="px-4 py-3 border-b border-ink-200 flex items-center justify-between gap-3"
					>
						<div>
							<h2 class="font-semibold text-ink-900 text-sm">Project health</h2>
							<p class="text-[11px] text-ink-500 mt-0.5">
								Progress against plan · work done against contract value
							</p>
						</div>
						<RouterLink
							v-if="showAllProjects"
							to="/projects"
							class="text-xs text-brand-600 hover:underline flex-shrink-0"
							>All projects →</RouterLink
						>
					</div>

					<div
						class="hidden lg:grid grid-cols-[minmax(240px,1.8fr)_220px_170px_120px] gap-4 px-4 py-2 bg-ink-50 border-b border-ink-100 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
					>
						<span>Project</span>
						<span>Progress vs plan</span>
						<span class="text-right">Work done / value</span>
						<span class="text-right">Schedule</span>
					</div>

					<div class="divide-y divide-ink-100">
						<RouterLink
							v-for="r in health"
							:key="r.id"
							:to="`/projects/${r.id}`"
							class="grid grid-cols-1 lg:grid-cols-[minmax(240px,1.8fr)_220px_170px_120px] gap-4 px-4 py-3.5 hover:bg-ink-50 items-center"
						>
							<div class="min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<span
										v-if="r.reasons.length"
										class="w-1.5 h-1.5 rounded-full bg-danger-500 flex-shrink-0"
										:title="r.reasons.join(' · ')"
									></span>
									<span class="font-medium text-ink-900 text-sm">{{
										r.name
									}}</span>
									<StatusBadge :status="r.status" />
								</div>
								<div class="text-xs text-ink-500 mt-0.5 truncate">
									<span v-if="r.client">{{ r.client }} · </span
									>{{ r.open_tasks }}/{{ r.total_tasks }} tasks open
								</div>
							</div>

							<div>
								<div class="relative h-2 bg-ink-100 rounded-full overflow-hidden">
									<div
										class="h-full rounded-full"
										:class="progressTone(r)"
										:style="`width:${r.progress}%`"
									></div>
									<span
										class="absolute top-0 bottom-0 w-0.5 stage-progress-tick"
										:style="`left:${Math.min(99.5, r.expected)}%`"
										:title="`Expected ${r.expected}% by today`"
									></span>
								</div>
								<div
									class="flex items-center justify-between mt-1 text-[11px] tabular-nums"
								>
									<span class="text-ink-700 font-medium">{{ r.progress }}%</span>
									<span class="text-ink-400">plan {{ r.expected }}%</span>
								</div>
							</div>

							<div class="text-right">
								<template v-if="r.has_boq">
									<div
										class="text-sm text-ink-900 tabular-nums whitespace-nowrap"
									>
										{{ fmtCompactINR(r.earned) }}
									</div>
									<div
										class="text-[11px] text-ink-400 tabular-nums whitespace-nowrap"
									>
										of {{ fmtCompactINR(r.planned) }}
									</div>
								</template>
								<template v-else>
									<div class="text-sm text-ink-400">—</div>
									<div class="text-[11px] text-ink-400 whitespace-nowrap">
										no approved BOQ
									</div>
								</template>
							</div>

							<div class="text-right">
								<div
									class="text-sm tabular-nums whitespace-nowrap"
									:class="schedule(r).tone"
								>
									{{ schedule(r).text }}
								</div>
							</div>
						</RouterLink>

						<div
							v-if="!health.length"
							class="px-4 py-10 text-center text-sm text-ink-400"
						>
							No projects in scope ·
							<RouterLink to="/projects/new" class="text-brand-600 hover:underline"
								>Create one →</RouterLink
							>
						</div>
					</div>
				</div>

				<!-- ===== Cost booked · Decision queue · Site activity ===== -->
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
					<!-- Cost booked by head -->
					<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
						<div class="px-4 py-3 border-b border-ink-200">
							<h2 class="font-semibold text-ink-900 text-sm">Cost booked to date</h2>
							<p class="text-[11px] text-ink-500 mt-0.5">
								Actual spend by head — not the BOQ view above
							</p>
						</div>
						<div class="p-4">
							<div
								class="text-2xl font-semibold text-ink-900 tabular-nums whitespace-nowrap"
							>
								{{ fmtCompactINR(cost.total_actual) }}
							</div>
							<div class="text-[11px] text-ink-400 mb-4">
								across every task in scope
							</div>

							<div v-for="h in cost.heads" :key="h.key" class="mb-3 last:mb-0">
								<div class="flex items-baseline justify-between text-xs mb-1">
									<span class="text-ink-700">{{ h.label }}</span>
									<span v-if="h.pending" class="text-[11px] text-ink-400 italic"
										>no source yet</span
									>
									<span v-else class="text-ink-900 tabular-nums font-medium">{{
										fmtCompactINR(h.value)
									}}</span>
								</div>
								<div class="h-1.5 bg-ink-100 rounded-full overflow-hidden">
									<div
										class="h-full rounded-full"
										:class="h.bar"
										:style="`width:${h.pct}%`"
									></div>
								</div>
							</div>
						</div>
					</div>

					<!-- Decision queue -->
					<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
						<div
							class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
						>
							<div>
								<h2 class="font-semibold text-ink-900 text-sm">Waiting on you</h2>
								<p class="text-[11px] text-ink-500 mt-0.5">
									Approvals across every module
								</p>
							</div>
							<span
								class="text-xs font-semibold px-2 py-0.5 rounded-full tabular-nums"
								:class="
									data.decision_total
										? 'bg-warning-50 text-warning-700'
										: 'bg-success-50 text-success-700'
								"
								>{{ data.decision_total }}</span
							>
						</div>
						<div class="divide-y divide-ink-100">
							<RouterLink
								v-for="d in decision"
								:key="d.key"
								:to="d.to"
								class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
							>
								<span
									class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
									:class="d.tone"
								>
									<svg
										class="w-4 h-4"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.75"
										stroke-linecap="round"
										stroke-linejoin="round"
										aria-hidden="true"
										v-html="getWorkspaceIconPath(d.slug)"
									/>
								</span>
								<div class="flex-1 min-w-0">
									<div class="text-sm text-ink-900">{{ d.label }}</div>
									<div class="text-[11px] text-ink-500 truncate">
										<template v-if="d.count && d.value"
											>{{ fmtCompactINR(d.value) }} {{ d.sub }}</template
										>
										<template v-else-if="d.count">{{ d.sub }}</template>
										<template v-else>Nothing pending</template>
									</div>
								</div>
								<span
									class="text-sm font-semibold tabular-nums flex-shrink-0"
									:class="d.count ? 'text-ink-900' : 'text-ink-300'"
									>{{ d.count }}</span
								>
							</RouterLink>
						</div>
					</div>

					<!-- Site activity -->
					<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
						<div class="px-4 py-3 border-b border-ink-200">
							<h2 class="font-semibold text-ink-900 text-sm">Site activity</h2>
							<p class="text-[11px] text-ink-500 mt-0.5">Last 7 days</p>
						</div>
						<div class="p-4">
							<div class="grid grid-cols-2 gap-3 mb-4">
								<div>
									<div class="text-xl font-semibold text-ink-900 tabular-nums">
										{{ activity.entries }}
									</div>
									<div
										class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-0.5"
									>
										Progress entries
									</div>
								</div>
								<div>
									<div class="text-xl font-semibold text-ink-900 tabular-nums">
										{{ activity.man_days ?? "—" }}
									</div>
									<div
										class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-0.5"
									>
										Man-days
									</div>
								</div>
								<div>
									<div
										class="text-xl font-semibold tabular-nums"
										:class="
											activity.blockers ? 'text-danger-700' : 'text-ink-900'
										"
									>
										{{ activity.blockers }}
									</div>
									<div
										class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-0.5"
									>
										Blockers
									</div>
								</div>
								<div>
									<div class="text-xl font-semibold text-ink-900 tabular-nums">
										{{ activity.receipts }}
									</div>
									<div
										class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-0.5"
									>
										Deliveries
									</div>
								</div>
							</div>

							<p
								v-if="activityQuiet"
								class="text-[11px] text-ink-400 italic mb-3 -mt-1"
							>
								<template v-if="activity.last_activity_date"
									>Nothing reported this week — the last report was
									{{ fmtDate(activity.last_activity_date) }}.</template
								>
								<template v-else>No site reporting yet.</template>
							</p>

							<div class="border-t border-ink-100 pt-3">
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-2"
								>
									Latest reports
								</div>
								<div
									v-for="e in activity.recent"
									:key="e.id"
									class="flex items-center gap-2 py-1.5"
								>
									<UserAvatar :user-id="e.owner" size="xs" />
									<span class="flex-1 min-w-0">
										<span class="block text-xs text-ink-900 truncate">{{
											e.task
										}}</span>
										<span class="block text-[10px] text-ink-500"
											>{{ fmtDate(e.entry_date) }} ·
											{{ Math.round(e.progress) }}%</span
										>
									</span>
									<span
										v-if="e.blocker"
										class="text-[10px] px-1.5 py-0.5 rounded-full bg-danger-50 text-danger-700 flex-shrink-0"
										>Blocked</span
									>
								</div>
								<div
									v-if="!activity.recent.length"
									class="text-xs text-ink-400 italic py-2"
								>
									No progress entries filed yet.
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- ===== Commitments ===== -->
				<div class="bg-white border border-ink-200 rounded-xl overflow-hidden mt-6">
					<div class="px-4 py-3 border-b border-ink-200">
						<h2 class="font-semibold text-ink-900 text-sm">
							Commitments &amp; exposure
						</h2>
						<p class="text-[11px] text-ink-500 mt-0.5">
							Money promised to third parties, and what is still to come
						</p>
					</div>
					<div
						class="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-ink-100"
					>
						<div class="p-4">
							<div
								class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
							>
								Subcontract committed
							</div>
							<div
								class="text-lg font-semibold text-ink-900 mt-1 tabular-nums whitespace-nowrap"
							>
								{{ fmtCompactINR(commitments.committed) }}
							</div>
							<div class="text-[11px] text-ink-400 mt-0.5 tabular-nums">
								{{ fmtCompactINR(commitments.billed) }} billed ·
								{{ fmtCompactINR(commitments.remaining) }} to come
							</div>
						</div>
						<div class="p-4">
							<div
								class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
							>
								On order
							</div>
							<div
								class="text-lg font-semibold text-ink-900 mt-1 tabular-nums whitespace-nowrap"
							>
								{{ fmtCompactINR(commitments.on_order) }}
							</div>
							<div class="text-[11px] text-ink-400 mt-0.5">
								{{ commitments.on_order_count }} open purchase orders
							</div>
						</div>
						<div class="p-4">
							<div
								class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
							>
								Retention held
							</div>
							<div
								class="text-lg font-semibold text-ink-900 mt-1 tabular-nums whitespace-nowrap"
							>
								{{ fmtCompactINR(commitments.retention) }}
							</div>
							<div class="text-[11px] text-ink-400 mt-0.5">
								withheld from subcontractors
							</div>
						</div>
					</div>
				</div>

				<!-- ===== Needs attention ===== -->
				<div class="bg-white border border-ink-200 rounded-xl overflow-hidden mt-6 mb-4">
					<div class="px-4 py-3 border-b border-ink-200">
						<h2 class="font-semibold text-ink-900 text-sm">Needs attention</h2>
						<p class="text-[11px] text-ink-500 mt-0.5">
							Schedule · cost · decisions · supply
						</p>
					</div>
					<div class="divide-y divide-ink-100">
						<RouterLink
							v-for="a in attention"
							:key="a.key"
							:to="a.to"
							class="flex items-start gap-3 px-4 py-3 hover:bg-ink-50"
						>
							<span
								:class="a.tone"
								class="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
							></span>
							<div class="flex-1 min-w-0">
								<div
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ a.kind }}
								</div>
								<div class="text-sm text-ink-900 leading-snug mt-0.5">
									{{ a.title }}
								</div>
								<div class="text-xs text-ink-500 mt-0.5 truncate">
									{{ a.context }}
								</div>
							</div>
							<span class="text-brand-600 text-sm flex-shrink-0">→</span>
						</RouterLink>
						<div v-if="!attention.length" class="px-4 py-10 text-center">
							<div class="text-sm text-ink-700">Nothing needs attention</div>
							<p class="text-xs text-ink-500 mt-1">
								Schedule, cost, decisions and supply are all within tolerance.
							</p>
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>
