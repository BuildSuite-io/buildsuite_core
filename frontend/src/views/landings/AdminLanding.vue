<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { ROLES } from "@/data/roles";
import { WORKSPACE_META, workspaceMetric } from "@/data/workspaces";
import { useDataStore } from "@/stores";
import LandingShell from "@/layouts/LandingShell.vue";
import { fmtDate } from "@/utils/format";

const ROLE_ID = "admin";
const role = ROLES.find((r) => r.id === ROLE_ID);
const store = useDataStore();

const today = new Date();
const todayLabel = today.toLocaleDateString("en-IN", {
	weekday: "long",
	day: "2-digit",
	month: "short",
	year: "numeric",
});

// Workspace launcher — Admin sees all 12. Group by BuildSuite vs ERPNext per §12.2.
const buildsuiteTiles = computed(() =>
	store.visibleWorkspaces
		.filter((slug) => WORKSPACE_META[slug]?.group === "buildsuite")
		.map((slug) => ({ slug, ...WORKSPACE_META[slug], metric: workspaceMetric(slug, store) }))
);
const erpnextTiles = computed(() =>
	store.visibleWorkspaces
		.filter((slug) => WORKSPACE_META[slug]?.group === "erpnext")
		.map((slug) => ({ slug, ...WORKSPACE_META[slug], metric: workspaceMetric(slug, store) }))
);

// Recent activity feed — composed from any store entity that carries a meaningful
// timestamp. Sorted desc by date, capped at 5. No fake data here; if the store is
// empty the section shows an empty state.
const recentActivity = computed(() => {
	const events = [];
	store.projects.forEach((p) => {
		if (p.createdAt)
			events.push({
				key: `proj-${p.id}`,
				kind: "Project",
				kindClass: "bg-info-50 text-info-700",
				title: `Project created: ${p.name}`,
				date: p.createdAt,
				to: `/projects/${p.id}`,
			});
	});
	store.scos.forEach((s) => {
		if (s.raisedDate) {
			const proj = store.projectById(s.projectId);
			events.push({
				key: `sco-raise-${s.id}`,
				kind: "SCO",
				kindClass: "bg-warning-50 text-warning-700",
				title: `SCO raised: ${s.title}`,
				date: s.raisedDate,
				sub: proj?.name,
				to: "/sco",
			});
		}
	});
	store.boqs.forEach((b) => {
		if (b.approvedDate) {
			const proj = store.projectById(b.projectId);
			events.push({
				key: `boq-appr-${b.id}`,
				kind: "BOQ",
				kindClass: "bg-success-50 text-success-700",
				title: `BOQ revision ${b.revision} approved`,
				date: b.approvedDate,
				sub: proj?.name,
				to: `/boq/${b.id}`,
			});
		} else if (b.preparedDate) {
			const proj = store.projectById(b.projectId);
			events.push({
				key: `boq-prep-${b.id}`,
				kind: "BOQ",
				kindClass: "bg-ink-100 text-ink-600",
				title: `BOQ revision ${b.revision} drafted`,
				date: b.preparedDate,
				sub: proj?.name,
				to: `/boq/${b.id}`,
			});
		}
	});
	return events
		.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
		.slice(0, 5);
});

// System health — illustrative for now. The localStorage key and "last reset" would be
// real once we track a reset timestamp; for the prototype these are descriptive.
const systemHealth = [
	{ label: "Data store", value: "localStorage · buildsuite:data:v1", tone: "ok" },
	{ label: "Role preference", value: "localStorage · buildsuite:role", tone: "ok" },
	{ label: "Last reset", value: "never (this session)", tone: "ok" },
	{ label: "Build", value: "Vue 3 · Vite 5 · Pinia · Tailwind", tone: "ok" },
];
</script>

<template>
	<LandingShell>
		<div class="max-w-6xl mx-auto px-6 py-10">
			<!-- Greeting -->
			<div class="flex items-center gap-3 mb-2">
				<span :class="role.color" class="w-2.5 h-2.5 rounded-full"></span>
				<p class="text-xs text-ink-500 uppercase tracking-wider font-medium">
					{{ role.shortName }} · System overview
				</p>
			</div>
			<h1 class="text-2xl font-semibold text-ink-900 tracking-tight">All systems</h1>
			<p class="text-sm text-ink-500 mt-1">
				{{ todayLabel }} ·
				<span class="text-ink-700 font-medium">{{ store.team.length }} users</span> ·
				<span class="text-ink-700 font-medium">{{ store.projects.length }} projects</span>
				·
				<span class="text-ink-700 font-medium">12 workspaces installed</span>
			</p>

			<!-- Workspace launcher -->
			<section class="mt-10">
				<div class="flex items-baseline justify-between mb-3">
					<h2 class="text-sm font-semibold text-ink-900">BuildSuite Core</h2>
					<span class="text-[11px] text-ink-500"
						>{{ buildsuiteTiles.length }} workspace{{
							buildsuiteTiles.length === 1 ? "" : "s"
						}}</span
					>
				</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
					<RouterLink
						v-for="t in buildsuiteTiles"
						:key="t.slug"
						:to="t.to"
						class="block bg-white border border-ink-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-fp-md transition-all"
					>
						<div class="flex items-start gap-3">
							<div
								class="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center text-xl flex-shrink-0"
							>
								{{ t.icon }}
							</div>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-semibold text-ink-900">{{ t.name }}</div>
								<div class="text-[11px] text-ink-500 mt-0.5 leading-snug">
									{{ t.desc }}
								</div>
								<div
									v-if="t.metric"
									class="text-[11px] text-brand-700 font-medium mt-2"
								>
									{{ t.metric }}
								</div>
							</div>
						</div>
					</RouterLink>
				</div>
			</section>

			<section class="mt-8">
				<div class="flex items-baseline justify-between mb-3">
					<div>
						<h2 class="text-sm font-semibold text-ink-500">ERPNext</h2>
					</div>
					<span class="text-[11px] text-ink-500"
						>{{ erpnextTiles.length }} workspace{{
							erpnextTiles.length === 1 ? "" : "s"
						}}</span
					>
				</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
					<RouterLink
						v-for="t in erpnextTiles"
						:key="t.slug"
						:to="t.to"
						class="block bg-white border border-ink-200 rounded-xl p-4 hover:border-ink-300 transition-all"
					>
						<div class="flex items-start gap-3">
							<div
								class="w-10 h-10 rounded-lg bg-ink-50 flex items-center justify-center text-xl flex-shrink-0 opacity-80"
							>
								{{ t.icon }}
							</div>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-semibold text-ink-700">{{ t.name }}</div>
								<div class="text-[11px] text-ink-500 mt-0.5 leading-snug">
									{{ t.desc }}
								</div>
								<div
									v-if="t.metric"
									class="text-[11px] text-ink-500 font-medium mt-2"
								>
									{{ t.metric }}
								</div>
							</div>
						</div>
					</RouterLink>
				</div>
			</section>

			<!-- Recent activity + System health -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-10">
				<div
					class="lg:col-span-2 bg-white border border-ink-200 rounded-xl overflow-hidden"
				>
					<div class="px-4 py-3 border-b border-ink-200">
						<h2 class="font-semibold text-ink-900 text-sm">Recent activity</h2>
						<p class="text-[11px] text-ink-500 mt-0.5">Last 5 events from the store</p>
					</div>
					<div class="divide-y divide-ink-100">
						<RouterLink
							v-for="e in recentActivity"
							:key="e.key"
							:to="e.to"
							class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
						>
							<span
								:class="e.kindClass"
								class="w-10 h-6 rounded flex items-center justify-center text-[10px] font-semibold tracking-wider"
								>{{ e.kind }}</span
							>
							<div class="flex-1 min-w-0">
								<div class="text-sm text-ink-900 truncate">{{ e.title }}</div>
								<div v-if="e.sub" class="text-xs text-ink-500 mt-0.5 truncate">
									{{ e.sub }}
								</div>
							</div>
							<span class="text-xs text-ink-500 flex-shrink-0">{{
								fmtDate(e.date)
							}}</span>
						</RouterLink>
						<div
							v-if="!recentActivity.length"
							class="px-4 py-8 text-center text-sm text-ink-400"
						>
							No activity yet.
						</div>
					</div>
				</div>

				<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
					<div class="px-4 py-3 border-b border-ink-200">
						<h2 class="font-semibold text-ink-900 text-sm">System health</h2>
					</div>
					<div class="divide-y divide-ink-100">
						<div
							v-for="h in systemHealth"
							:key="h.label"
							class="flex items-start gap-2.5 px-4 py-3"
						>
							<span
								class="w-2 h-2 rounded-full mt-1.5 flex-shrink-0 bg-success-500"
							></span>
							<div class="flex-1 min-w-0">
								<div
									class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
								>
									{{ h.label }}
								</div>
								<div class="text-xs text-ink-700 mt-0.5 break-words">
									{{ h.value }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</LandingShell>
</template>
