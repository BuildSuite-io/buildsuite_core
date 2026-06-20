<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { ROLES } from "@/data/roles";
import { useDataStore } from "@/stores";
import LandingShell from "@/layouts/LandingShell.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtCompactINR, fmtDate } from "@/utils/format";

const ROLE_ID = "director";
const role = ROLES.find((r) => r.id === ROLE_ID);
const store = useDataStore();

const today = new Date();
const todayLabel = today.toLocaleDateString("en-IN", {
	weekday: "long",
	day: "2-digit",
	month: "short",
	year: "numeric",
});

// Schedule-based variance per project (stand-in for cost variance until actuals are wired
// — the prompt explicitly allows progress as a stand-in). Sign convention matches the
// existing variancePill helper in BoqView: positive = bad (behind), negative = good (ahead).
function projectVariance(p) {
	const start = new Date(p.startDate).getTime();
	const end = new Date(p.endDate).getTime();
	const total = end - start;
	if (total <= 0) return 0;
	const elapsed = Math.max(0, Math.min(total, today.getTime() - start));
	const expected = (elapsed / total) * 100;
	if (expected <= 0) return 0;
	return ((expected - p.progress) / expected) * 100;
}

function daysToEnd(p) {
	const end = new Date(p.endDate).getTime();
	return Math.ceil((end - today.getTime()) / 86400000);
}

function variancePill(pct) {
	if (Math.abs(pct) < 0.5) return "text-ink-500";
	return pct > 0 ? "text-danger-700" : "text-success-700";
}

const activeRootProjects = computed(() => store.rootProjects.filter((p) => p.status === "Active"));

const avgVariancePct = computed(() => {
	const xs = activeRootProjects.value.map(projectVariance).filter((v) => Number.isFinite(v));
	if (!xs.length) return 0;
	return xs.reduce((a, b) => a + b, 0) / xs.length;
});

const pendingScosValue = computed(() =>
	store.scos
		.filter((s) => s.status === "Pending Approval")
		.reduce((a, s) => a + (s.impact || 0), 0)
);

const projectHealthRows = computed(() =>
	store.rootProjects.slice(0, 6).map((p) => ({
		...p,
		variancePct: projectVariance(p),
		days: daysToEnd(p),
	}))
);
const showProjectsMore = computed(() => store.rootProjects.length > 6);

const topRisks = computed(() => {
	const out = [];
	activeRootProjects.value.forEach((p) => {
		const days = daysToEnd(p);
		if (p.progress < 30 && days > 0 && days <= 90) {
			out.push({
				key: `sched-${p.id}`,
				dot: "bg-danger-500",
				kind: "Schedule risk",
				title: `${p.progress}% complete with ${days} days to deadline`,
				project: p.name,
				to: `/projects/${p.id}`,
			});
		}
		const v = projectVariance(p);
		if (v > 10) {
			out.push({
				key: `cost-${p.id}`,
				dot: "bg-warning-500",
				kind: "Cost / pace risk",
				title: `${v.toFixed(1)}% behind expected pace`,
				project: p.name,
				to: `/projects/${p.id}`,
			});
		}
	});
	store.scos
		.filter((s) => s.status === "Pending Approval")
		.forEach((s) => {
			const daysAgo = Math.ceil(
				(today.getTime() - new Date(s.raisedDate).getTime()) / 86400000
			);
			if (daysAgo > 7) {
				const proj = store.projectById(s.projectId);
				out.push({
					key: `sco-${s.id}`,
					dot: "bg-info-500",
					kind: "Decision risk",
					title: `${s.title} — ${daysAgo}d awaiting decision`,
					project: proj?.name || "—",
					to: "/sco",
				});
			}
		});
	return out.slice(0, 3);
});

const highValueApprovals = computed(() =>
	store.scos
		.filter((s) => s.status === "Pending Approval" && (s.impact || 0) > 1000000)
		.sort((a, b) => (b.impact || 0) - (a.impact || 0))
);
</script>

<template>
	<LandingShell>
		<div class="max-w-7xl mx-auto px-6 py-10">
			<!-- Greeting strip -->
			<div class="flex items-center gap-3 mb-2">
				<span :class="role.color" class="w-2.5 h-2.5 rounded-full"></span>
				<p class="text-xs text-ink-500 uppercase tracking-wider font-medium">
					{{ role.shortName }} · Portfolio overview
				</p>
			</div>
			<h1 class="text-2xl font-semibold text-ink-900 tracking-tight">Good morning</h1>
			<p class="text-sm text-ink-500 mt-1">{{ todayLabel }}</p>

			<!-- KPI strip -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
				<div class="bg-white border border-ink-200 rounded-xl p-4">
					<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
						Active projects
					</div>
					<div class="text-2xl font-semibold text-ink-900 mt-1">
						{{ store.activeProjectsCount }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-xl p-4">
					<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
						Total order book
					</div>
					<div class="text-2xl font-semibold text-ink-900 mt-1">
						{{ fmtCompactINR(store.totalOrderBook) }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-xl p-4">
					<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
						Avg variance
					</div>
					<div
						class="text-2xl font-semibold mt-1 tabular-nums"
						:class="variancePill(avgVariancePct)"
					>
						{{ avgVariancePct > 0 ? "+" : "" }}{{ avgVariancePct.toFixed(1) }}%
					</div>
					<div class="text-[11px] text-ink-400 mt-0.5">
						{{ avgVariancePct > 0 ? "behind" : "ahead of" }} plan, schedule basis
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-xl p-4">
					<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
						Open SCOs · value
					</div>
					<div class="text-2xl font-semibold text-warning-700 mt-1">
						{{ fmtCompactINR(pendingScosValue) }}
					</div>
					<div class="text-[11px] text-ink-400 mt-0.5">
						{{ store.pendingScosCount }} pending decisions
					</div>
				</div>
			</div>

			<!-- Project health + Top risks -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
				<!-- Project health (2 cols) -->
				<div
					class="lg:col-span-2 bg-white border border-ink-200 rounded-xl overflow-hidden"
				>
					<div
						class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
					>
						<h2 class="font-semibold text-ink-900 text-sm">Project health</h2>
						<RouterLink
							v-if="showProjectsMore"
							to="/projects"
							class="text-xs text-brand-600 hover:underline"
							>View all →</RouterLink
						>
					</div>
					<div class="divide-y divide-ink-100">
						<RouterLink
							v-for="p in projectHealthRows"
							:key="p.id"
							:to="`/projects/${p.id}`"
							class="block px-4 py-3.5 hover:bg-ink-50"
						>
							<div class="flex items-center gap-3">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 flex-wrap">
										<span class="font-medium text-ink-900 text-sm">{{
											p.name
										}}</span>
										<StatusBadge :status="p.status" />
									</div>
									<div class="text-xs text-ink-500 mt-0.5">
										{{ p.client }} · {{ fmtCompactINR(p.budget) }} ·
										{{
											p.days > 0
												? `${p.days}d to deadline`
												: `${-p.days}d overdue`
										}}
									</div>
								</div>
								<div class="w-44 flex-shrink-0">
									<div class="flex items-center gap-2">
										<div
											class="flex-1 h-1.5 bg-ink-100 rounded-full overflow-hidden"
										>
											<div
												class="h-full"
												:class="
													p.progress > 80
														? 'bg-success-500'
														: p.progress > 40
														? 'bg-brand-500'
														: 'bg-warning-500'
												"
												:style="`width:${p.progress}%`"
											></div>
										</div>
										<span
											class="text-xs text-ink-700 tabular-nums w-10 text-right"
											>{{ p.progress }}%</span
										>
									</div>
									<div
										class="text-[11px] mt-1 text-right tabular-nums"
										:class="variancePill(p.variancePct)"
									>
										{{ p.variancePct > 0 ? "+" : ""
										}}{{ p.variancePct.toFixed(1) }}% variance
									</div>
								</div>
							</div>
						</RouterLink>
						<div
							v-if="!projectHealthRows.length"
							class="px-4 py-8 text-center text-sm text-ink-400"
						>
							No projects yet ·
							<RouterLink to="/projects/new" class="text-brand-600 hover:underline"
								>Create one →</RouterLink
							>
						</div>
					</div>
				</div>

				<!-- Top risks -->
				<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
					<div class="px-4 py-3 border-b border-ink-200">
						<h2 class="font-semibold text-ink-900 text-sm">Top risks</h2>
						<p class="text-[11px] text-ink-500 mt-0.5">Schedule · cost · decisions</p>
					</div>
					<div class="divide-y divide-ink-100">
						<RouterLink
							v-for="r in topRisks"
							:key="r.key"
							:to="r.to"
							class="block px-4 py-3 hover:bg-ink-50"
						>
							<div class="flex items-start gap-2.5">
								<span
									:class="r.dot"
									class="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
								></span>
								<div class="flex-1 min-w-0">
									<div
										class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
									>
										{{ r.kind }}
									</div>
									<div class="text-sm text-ink-900 leading-snug mt-0.5">
										{{ r.title }}
									</div>
									<div class="text-xs text-ink-500 mt-0.5 truncate">
										{{ r.project }}
									</div>
								</div>
							</div>
						</RouterLink>
						<div v-if="!topRisks.length" class="px-4 py-8 text-center">
							<div class="text-2xl mb-1">✓</div>
							<div class="text-sm text-ink-700">No critical risks detected</div>
							<p class="text-xs text-ink-500 mt-1">
								Schedule, cost, and decisions all within tolerance.
							</p>
						</div>
					</div>
				</div>
			</div>

			<!-- High-value approvals -->
			<div class="bg-white border border-ink-200 rounded-xl overflow-hidden mt-6">
				<div class="px-4 py-3 border-b border-ink-200 flex items-center justify-between">
					<h2 class="font-semibold text-ink-900 text-sm">High-value approvals</h2>
					<span class="text-[11px] text-ink-500">SCO impact &gt; ₹10 L</span>
				</div>
				<div class="divide-y divide-ink-100">
					<RouterLink
						v-for="s in highValueApprovals"
						:key="s.id"
						to="/sco"
						class="flex items-center gap-4 px-4 py-3 hover:bg-ink-50"
					>
						<div
							class="w-8 h-8 rounded-lg bg-warning-50 text-warning-700 flex items-center justify-center text-sm"
						>
							🔁
						</div>
						<div class="flex-1 min-w-0">
							<div class="font-medium text-ink-900 text-sm truncate">
								{{ s.title }}
							</div>
							<div class="text-xs text-ink-500 mt-0.5 font-mono">
								{{ s.id }} · raised {{ fmtDate(s.raisedDate) }}
							</div>
						</div>
						<div class="text-right flex-shrink-0">
							<div class="text-sm font-semibold text-ink-900 tabular-nums">
								{{ fmtCompactINR(s.impact) }}
							</div>
							<div class="text-[11px] text-ink-500">
								{{ s.recoverable ? "recoverable" : "absorbed" }}
							</div>
						</div>
						<span class="text-brand-600 text-sm flex-shrink-0">Review →</span>
					</RouterLink>
					<div
						v-if="!highValueApprovals.length"
						class="px-4 py-8 text-center text-sm text-ink-400"
					>
						No high-value approvals pending.
					</div>
				</div>
			</div>
		</div>
	</LandingShell>
</template>
