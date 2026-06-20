<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { ROLES } from "@/data/roles";
import { useDataStore } from "@/stores";
import LandingShell from "@/layouts/LandingShell.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { fmtCompactINR, fmtDate } from "@/utils/format";

const ROLE_ID = "pm";
const role = ROLES.find((r) => r.id === ROLE_ID);
const store = useDataStore();

// Prototype assumption: when the active role is PM, treat USR-002 (Hemanth M.)
// as "me" for the purpose of filtering "my projects" / "my approvals". When the
// prototype gains real auth, this becomes store.user.id.
const PM_USER_ID = "USR-002";

const today = new Date();
const todayLabel = today.toLocaleDateString("en-IN", {
	weekday: "long",
	day: "2-digit",
	month: "short",
	year: "numeric",
});

function daysToEnd(p) {
	return Math.ceil((new Date(p.endDate).getTime() - today.getTime()) / 86400000);
}
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
function variancePill(pct) {
	if (Math.abs(pct) < 0.5) return "text-ink-500";
	return pct > 0 ? "text-danger-700" : "text-success-700";
}

const myProjects = computed(() => store.projects.filter((p) => p.pm === PM_USER_ID));

// All project ids the PM is responsible for: their own + subprojects of their projects.
const myProjectIds = computed(() => {
	const ids = new Set();
	myProjects.value.forEach((p) => {
		ids.add(p.id);
		store.projects.filter((c) => c.parentId === p.id).forEach((c) => ids.add(c.id));
	});
	return ids;
});

const myActiveCount = computed(() => myProjects.value.filter((p) => p.status === "Active").length);

const projectCards = computed(() =>
	myProjects.value.map((p) => {
		const tasks = store.tasksByProject(p.id);
		const scos = store.scosByProject(p.id);
		return {
			...p,
			days: daysToEnd(p),
			openTasksCount: tasks.filter((t) => t.status !== "Completed").length,
			pendingScosCount: scos.filter((s) => s.status === "Pending Approval").length,
			variancePct: projectVariance(p),
		};
	})
);

const myPendingScos = computed(() =>
	store.scos.filter(
		(s) => s.status === "Pending Approval" && myProjectIds.value.has(s.projectId)
	)
);

const approvals = computed(() => {
	const rows = myPendingScos.value.map((s) => {
		const proj = store.projectById(s.projectId);
		const daysAgo = Math.ceil((today.getTime() - new Date(s.raisedDate).getTime()) / 86400000);
		return {
			key: `sco-${s.id}`,
			kind: "SC",
			kindClass: "bg-warning-50 text-warning-700",
			title: s.title,
			project: proj?.name || "—",
			amount: s.impact,
			raisedBy: s.raisedBy,
			daysAgo,
			to: "/sco",
		};
	});
	// Order most urgent (oldest pending) first
	rows.sort((a, b) => b.daysAgo - a.daysAgo);
	return rows;
});

const criticalTasks = computed(() => {
	return store.tasks
		.filter((t) => t.status !== "Completed")
		.filter(
			(t) =>
				t.assignee === PM_USER_ID ||
				(t.priority === "High" && myProjectIds.value.has(t.projectId))
		)
		.sort((a, b) => new Date(a.endDate).getTime() - new Date(b.endDate).getTime())
		.slice(0, 8);
});

const pendingApprovalsCount = computed(() => approvals.value.length);
</script>

<template>
	<LandingShell>
		<div class="max-w-5xl mx-auto px-6 py-10">
			<!-- Greeting strip -->
			<div class="flex items-center gap-3 mb-2">
				<span :class="role.color" class="w-2.5 h-2.5 rounded-full"></span>
				<p class="text-xs text-ink-500 uppercase tracking-wider font-medium">
					{{ role.shortName }} · My projects
				</p>
			</div>
			<h1 class="text-2xl font-semibold text-ink-900 tracking-tight">Good morning</h1>
			<p class="text-sm text-ink-500 mt-1">
				{{ todayLabel }} ·
				<span class="text-ink-700 font-medium"
					>{{ myActiveCount }} active project{{ myActiveCount === 1 ? "" : "s" }}</span
				>
				·
				<span class="text-ink-700 font-medium"
					>{{ pendingApprovalsCount }} pending approval{{
						pendingApprovalsCount === 1 ? "" : "s"
					}}</span
				>
			</p>

			<!-- My projects -->
			<h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">My projects</h2>
			<div v-if="projectCards.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
				<RouterLink
					v-for="p in projectCards"
					:key="p.id"
					:to="`/projects/${p.id}`"
					class="block bg-white border border-ink-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-fp-md transition-all"
				>
					<div class="flex items-start justify-between gap-3 mb-3">
						<div class="min-w-0">
							<div class="flex items-center gap-2 flex-wrap">
								<span class="font-medium text-ink-900 text-sm">{{ p.name }}</span>
								<StatusBadge :status="p.status" />
							</div>
							<div class="text-xs text-ink-500 mt-0.5">{{ p.client }}</div>
						</div>
						<div class="text-right flex-shrink-0">
							<div class="text-[11px] text-ink-500">
								{{ p.days > 0 ? `${p.days}d to deadline` : `${-p.days}d overdue` }}
							</div>
							<div
								class="text-[11px] tabular-nums mt-0.5"
								:class="variancePill(p.variancePct)"
							>
								{{ p.variancePct > 0 ? "+" : "" }}{{ p.variancePct.toFixed(1) }}%
							</div>
						</div>
					</div>
					<div class="flex items-center gap-2 mb-3">
						<div class="flex-1 h-1.5 bg-ink-100 rounded-full overflow-hidden">
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
						<span class="text-xs text-ink-700 tabular-nums w-10 text-right"
							>{{ p.progress }}%</span
						>
					</div>
					<div class="flex items-center gap-4 text-xs text-ink-500">
						<span
							>{{ p.openTasksCount }} open task{{
								p.openTasksCount === 1 ? "" : "s"
							}}</span
						>
						<span>·</span>
						<span
							:class="p.pendingScosCount > 0 ? 'text-warning-700 font-medium' : ''"
						>
							{{ p.pendingScosCount }} pending SCO{{
								p.pendingScosCount === 1 ? "" : "s"
							}}
						</span>
						<span class="ml-auto text-ink-400">{{ fmtCompactINR(p.budget) }}</span>
					</div>
				</RouterLink>
			</div>
			<div
				v-else
				class="bg-white border border-ink-200 rounded-xl px-4 py-8 text-center text-sm text-ink-500"
			>
				No projects assigned to you.
				<RouterLink to="/projects/new" class="text-brand-600 hover:underline"
					>Create one →</RouterLink
				>
			</div>

			<!-- Pending approvals -->
			<h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Pending approvals</h2>
			<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
				<div class="divide-y divide-ink-100">
					<RouterLink
						v-for="a in approvals"
						:key="a.key"
						:to="a.to"
						class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
					>
						<span
							:class="a.kindClass"
							class="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-semibold tracking-wider"
							>{{ a.kind }}</span
						>
						<div class="flex-1 min-w-0">
							<div class="text-sm font-medium text-ink-900 truncate">
								{{ a.title }}
							</div>
							<div class="text-xs text-ink-500 mt-0.5 truncate">
								{{ a.project }} · raised {{ a.daysAgo }}d ago
							</div>
						</div>
						<div class="text-right flex-shrink-0">
							<div class="text-sm font-semibold text-ink-900 tabular-nums">
								{{ fmtCompactINR(a.amount) }}
							</div>
						</div>
						<UserAvatar :user-id="a.raisedBy" size="xs" />
						<span class="text-brand-600 text-sm flex-shrink-0">Review →</span>
					</RouterLink>
					<div
						v-if="!approvals.length"
						class="px-4 py-6 text-center text-sm text-ink-400"
					>
						No SCO approvals waiting on you.
					</div>
					<!-- Stubs for the other two approval kinds — flagged as not yet wired -->
					<div class="flex items-center gap-3 px-4 py-3 bg-ink-50/50">
						<span
							class="w-8 h-8 rounded-lg bg-ink-100 text-ink-400 flex items-center justify-center text-[10px] font-semibold tracking-wider"
							>MR</span
						>
						<div class="flex-1 min-w-0">
							<div class="text-sm text-ink-500">Material requests</div>
							<div class="text-xs text-ink-400 mt-0.5">
								0 pending · Procurement (M4) — coming soon
							</div>
						</div>
					</div>
					<div class="flex items-center gap-3 px-4 py-3 bg-ink-50/50">
						<span
							class="w-8 h-8 rounded-lg bg-ink-100 text-ink-400 flex items-center justify-center text-[10px] font-semibold tracking-wider"
							>PC</span
						>
						<div class="flex-1 min-w-0">
							<div class="text-sm text-ink-500">Petty cash requests</div>
							<div class="text-xs text-ink-400 mt-0.5">
								0 pending · Project Finance (M8) — coming soon
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Today's critical tasks -->
			<h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Today's critical tasks</h2>
			<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
				<div class="divide-y divide-ink-100">
					<RouterLink
						v-for="t in criticalTasks"
						:key="t.id"
						:to="`/tasks/${t.id}`"
						class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
					>
						<span
							class="w-2 h-2 rounded-full flex-shrink-0"
							:class="t.status === 'In Progress' ? 'bg-brand-500' : 'bg-ink-300'"
						></span>
						<div class="flex-1 min-w-0">
							<div class="text-sm text-ink-900 truncate">{{ t.name }}</div>
							<div class="text-xs text-ink-500 mt-0.5 truncate">
								Due {{ fmtDate(t.endDate) }} · {{ t.priority }} priority
							</div>
						</div>
						<div class="flex items-center gap-2 flex-shrink-0">
							<div class="w-16 h-1.5 bg-ink-100 rounded-full overflow-hidden">
								<div
									class="h-full bg-brand-500"
									:style="`width:${t.progress}%`"
								></div>
							</div>
							<span class="text-xs text-ink-700 tabular-nums w-8 text-right"
								>{{ t.progress }}%</span
							>
						</div>
						<UserAvatar :user-id="t.assignee" size="xs" />
					</RouterLink>
					<div
						v-if="!criticalTasks.length"
						class="px-4 py-8 text-center text-sm text-ink-400"
					>
						No critical tasks · you're caught up.
					</div>
				</div>
			</div>
		</div>
	</LandingShell>
</template>
