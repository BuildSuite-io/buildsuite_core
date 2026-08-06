<script setup>
// Project Progress Report — Daily / Weekly / Monthly (S167). Vue-styled report
// surface rendered inside DeskShell. All rollups are computed server-side against a
// moving date window (buildsuite_core.api.progress_report); this view is a thin
// renderer. The window is set via query params: ?period=daily|weekly|monthly[&date=…].
//
// PDF export: window.print() + the global @media print rule in style.css hides the
// DeskShell chrome (.report-root / .print:hidden). The user picks "Save as PDF".
import { computed, ref, watch } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtINR, fmtCompactINR, fmtDate } from "@/utils/format";
import { getProgressReport } from "@/data/progressReportApi";

const route = useRoute();
const router = useRouter();

const VALID_PERIODS = ["daily", "weekly", "monthly"];
const projectId = computed(() => route.params.id);
const period = ref(VALID_PERIODS.includes(route.query.period) ? route.query.period : "weekly");
const reportDate = ref(/^\d{4}-\d{2}-\d{2}$/.test(route.query.date) ? route.query.date : "");

const report = ref(null);
const loading = ref(true);
const error = ref("");

async function load() {
	loading.value = true;
	error.value = "";
	try {
		report.value = await getProgressReport(
			projectId.value,
			period.value,
			reportDate.value || undefined
		);
		// Adopt the server-resolved window end as the picker value.
		if (!reportDate.value && report.value?.date) reportDate.value = report.value.date;
	} catch (err) {
		error.value = err.message || "Failed to load the progress report.";
		report.value = null;
	} finally {
		loading.value = false;
	}
}
load();

// Mirror controls to the URL (deep-link / print context) and re-fetch.
watch([period, reportDate], () => {
	router.replace({
		query: { period: period.value, ...(reportDate.value ? { date: reportDate.value } : {}) },
	});
	load();
});

const project = computed(() => report.value?.project);
const window_ = computed(() => report.value?.window || {});
const lookAhead = computed(() => report.value?.look_ahead || {});
const stats = computed(() => report.value?.task_stats || {});
const kpis = computed(() => report.value?.kpis || {});
const labour = computed(() => kpis.value.labour || {});
const materials = computed(() => report.value?.materials || {});

const periodLabel = computed(
	() =>
		({ daily: "Daily report", weekly: "Weekly report", monthly: "Monthly report" }[
			period.value
		])
);

function plural(n, one, many) {
	return n === 1 ? one : many;
}
const summarySentences = computed(() => {
	if (!report.value) return [];
	const t = stats.value;
	const k = kpis.value;
	const out = [];
	out.push(
		`Of ${t.total} tasks, ${t.completed} complete, ${t.in_progress} in progress, ${t.yet_to_start} not started` +
			`${t.delayed ? `, ${t.delayed} in delay` : ""}${
				t.blocked ? `, ${t.blocked} blocked` : ""
			}.`
	);
	if (k.tasks_completed)
		out.push(
			`${k.tasks_completed} ${plural(
				k.tasks_completed,
				"task",
				"tasks"
			)} completed in this period.`
		);
	if (k.entries)
		out.push(
			`${k.entries} progress ${plural(k.entries, "entry", "entries")} filed; ${
				labour.value.total
			} ` +
				`${plural(labour.value.total, "labour-day", "labour-days")} deployed (${
					labour.value.skilled
				} skilled / ${labour.value.unskilled} unskilled).`
		);
	if (k.deliveries)
		out.push(`${k.deliveries} ${plural(k.deliveries, "delivery", "deliveries")} received.`);
	if (k.blockers)
		out.push(
			`${k.blockers} ${plural(k.blockers, "blocker", "blockers")} raised — see Issues.`
		);
	if (k.scope_changes)
		out.push(
			`${k.scope_changes} scope ${plural(k.scope_changes, "change", "changes")} raised.`
		);
	if (t.overdue)
		out.push(`${t.overdue} ${plural(t.overdue, "task is", "tasks are")} currently overdue.`);
	return out;
});

function grnTone(s) {
	if (["Completed", "To Bill"].includes(s)) return "bg-success-50 text-success-700";
	if (s === "Draft") return "bg-ink-100 text-ink-700";
	return "bg-warning-50 text-warning-700";
}
function generatedOnLabel() {
	return new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}
function printReport() {
	window.print();
}
function backToProject() {
	router.push(`/projects/${projectId.value}`);
}
</script>

<template>
	<div class="bg-white min-h-full report-root">
		<!-- Control bar (hidden in print) -->
		<header
			class="report-controls border-b border-ink-200 bg-white sticky top-0 z-10 print:hidden"
		>
			<div class="max-w-5xl mx-auto px-6 py-3 flex items-center gap-3 flex-wrap">
				<button
					type="button"
					class="text-xs text-ink-600 hover:text-ink-900 flex items-center gap-1"
					@click="backToProject"
				>
					<span>←</span><span>Back to project</span>
				</button>
				<span class="text-ink-300">|</span>
				<div class="flex border border-ink-200 rounded overflow-hidden">
					<button
						v-for="p in VALID_PERIODS"
						:key="p"
						type="button"
						class="px-3 py-1 text-xs capitalize border-l border-ink-200 first:border-l-0"
						:class="
							period === p
								? 'bg-brand-50 text-brand-700 font-medium'
								: 'bg-white text-ink-600 hover:bg-ink-50'
						"
						@click="period = p"
					>
						{{ p }}
					</button>
				</div>
				<label class="text-xs text-ink-500">As of</label>
				<input
					v-model="reportDate"
					type="date"
					class="text-xs px-2 py-1 border border-ink-200 rounded bg-white focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
				/>
				<button
					type="button"
					class="ml-auto text-xs px-3 py-1.5 rounded bg-ink-900 text-white hover:bg-ink-800 flex items-center gap-1.5"
					title="Opens the browser print dialog. Pick 'Save as PDF' to export."
					@click="printReport"
				>
					<svg
						width="14"
						height="14"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<polyline points="6 9 6 2 18 2 18 9" />
						<path
							d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
						/>
						<rect x="6" y="14" width="12" height="8" />
					</svg>
					<span>Export PDF</span>
				</button>
			</div>
		</header>

		<div v-if="loading" class="max-w-5xl mx-auto px-6 py-16 text-center text-sm text-ink-400">
			Building report…
		</div>
		<div v-else-if="error" class="max-w-5xl mx-auto px-6 py-16 text-center">
			<div class="text-sm text-danger-700">{{ error }}</div>
			<RouterLink
				to="/projects"
				class="text-brand-700 hover:underline text-sm mt-2 inline-block"
				>← Back to projects</RouterLink
			>
		</div>

		<main v-else-if="project" class="report-content max-w-5xl mx-auto px-6 py-8">
			<!-- Cover header -->
			<section class="report-section mb-6 pb-4 border-b border-ink-200">
				<div class="text-xs text-ink-500 mb-1">{{ periodLabel }} · {{ project.code }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">{{ project.name }}</h1>
				<div class="text-sm text-ink-600 mt-1">{{ project.client }}</div>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-xs">
					<div>
						<div class="text-ink-500 uppercase tracking-wider text-[10px]">Period</div>
						<div class="text-ink-900 font-medium mt-0.5">
							{{ fmtDate(window_.start) }} → {{ fmtDate(window_.end) }}
						</div>
					</div>
					<div>
						<div class="text-ink-500 uppercase tracking-wider text-[10px]">
							Project Manager
						</div>
						<div class="text-ink-900 font-medium mt-0.5">
							{{ project.pm_name || "—" }}
						</div>
					</div>
					<div>
						<div class="text-ink-500 uppercase tracking-wider text-[10px]">
							Project timeline
						</div>
						<div class="text-ink-900 font-medium mt-0.5">
							{{ fmtDate(project.start_date) }} → {{ fmtDate(project.end_date) }}
						</div>
					</div>
					<div>
						<div class="text-ink-500 uppercase tracking-wider text-[10px]">Status</div>
						<div class="mt-0.5"><StatusBadge :status="project.status" /></div>
					</div>
				</div>
			</section>

			<!-- Executive summary -->
			<section class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Executive summary
				</h2>
				<div
					class="p-4 bg-brand-50/40 border border-brand-100 rounded-lg text-sm text-ink-800 leading-relaxed"
				>
					<p v-for="(s, i) in summarySentences" :key="i" class="mb-1 last:mb-0">
						{{ s }}
					</p>
				</div>
			</section>

			<!-- Period KPIs -->
			<section class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Key metrics
				</h2>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Tasks completed
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ kpis.tasks_completed }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">in this period</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Progress entries
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ kpis.entries }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">site updates filed</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Labour-days
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ labour.total }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">
							{{ labour.skilled }} skilled · {{ labour.unskilled }} unskilled
						</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Deliveries received
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ kpis.deliveries }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">goods receipts</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Materials ordered
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ fmtCompactINR(kpis.po_value) }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">
							{{ kpis.po_count }} PO{{ kpis.po_count === 1 ? "" : "s" }} placed
						</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Blockers raised
						</div>
						<div
							class="text-xl font-semibold tabular-nums mt-1"
							:class="kpis.blockers ? 'text-danger-700' : 'text-ink-900'"
						>
							{{ kpis.blockers }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">via progress entries</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Scope changes
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ kpis.scope_changes }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">
							{{ kpis.scos_approved }} approved · {{ kpis.scos_pending }} pending
						</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Attachments added
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ kpis.attachments }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">files uploaded</div>
					</div>
				</div>
			</section>

			<!-- Task activity -->
			<section class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Task activity
				</h2>
				<div
					v-if="report.task_activity.length"
					class="border border-ink-200 rounded-lg overflow-hidden"
				>
					<table class="w-full text-xs">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">Task</th>
								<th class="text-left px-3 py-2">Status</th>
								<th class="text-right px-3 py-2">Progress</th>
								<th class="text-left px-3 py-2">Last update</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="t in report.task_activity"
								:key="t.id"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2 text-ink-900">{{ t.name }}</td>
								<td class="px-3 py-2"><StatusBadge :status="t.status" /></td>
								<td class="px-3 py-2 text-right tabular-nums text-ink-700">
									{{ t.progress }}%
								</td>
								<td class="px-3 py-2 text-ink-500">
									{{ fmtDate(t.last_update) }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div v-else class="text-xs text-ink-500 italic">
					No task activity recorded in this period.
				</div>
			</section>

			<!-- Stages -->
			<section class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Stages
				</h2>
				<div v-if="report.stages.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
					<div
						v-for="s in report.stages"
						:key="s.id"
						class="p-3 border border-ink-200 rounded-lg"
					>
						<div class="flex items-center justify-between gap-2 mb-1">
							<div class="text-sm font-medium text-ink-900 truncate">
								{{ s.name }}
							</div>
							<StatusBadge :status="s.workflow_state" />
						</div>
						<div v-if="s.planned_start" class="text-[11px] text-ink-500">
							{{ fmtDate(s.planned_start) }} → {{ fmtDate(s.planned_end) }}
						</div>
						<div v-if="s.description" class="text-xs text-ink-700 mt-1">
							{{ s.description }}
						</div>
					</div>
				</div>
				<div v-else class="text-xs text-ink-500 italic">No stages touch this period.</div>
			</section>

			<!-- Materials -->
			<section class="report-section mb-6 page-break-inside-avoid">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Materials
				</h2>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Material requests raised
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ materials.mr_count }}
						</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Purchase orders placed
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ materials.po_count }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">
							{{ fmtCompactINR(materials.po_value) }} committed
						</div>
					</div>
					<div class="p-3 border border-ink-200 rounded-lg">
						<div class="text-[10px] uppercase tracking-wider text-ink-500">
							Goods received on site
						</div>
						<div class="text-xl font-semibold text-ink-900 tabular-nums mt-1">
							{{ materials.grn_count }}
						</div>
						<div class="text-[10px] text-ink-400 mt-0.5">site GRNs</div>
					</div>
				</div>
				<div
					v-if="materials.grns.length"
					class="border border-ink-200 rounded-lg overflow-hidden"
				>
					<table class="w-full text-xs">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">Date</th>
								<th class="text-left px-3 py-2">Item</th>
								<th class="text-left px-3 py-2">Supplier</th>
								<th class="text-right px-3 py-2">Qty</th>
								<th class="text-left px-3 py-2">Status</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(g, i) in materials.grns"
								:key="i"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2 text-ink-500 whitespace-nowrap">
									{{ fmtDate(g.date) }}
								</td>
								<td class="px-3 py-2 text-ink-900">{{ g.item }}</td>
								<td class="px-3 py-2 text-ink-700">{{ g.supplier }}</td>
								<td class="px-3 py-2 text-right tabular-nums">
									{{ g.qty }} {{ g.uom }}
								</td>
								<td class="px-3 py-2">
									<span
										class="text-[10px] px-2 py-0.5 rounded-full font-medium"
										:class="grnTone(g.status)"
										>{{ g.status }}</span
									>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- Scope changes -->
			<section v-if="report.scope_changes.length" class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Scope changes
				</h2>
				<div class="border border-ink-200 rounded-lg overflow-hidden">
					<table class="w-full text-xs">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">Raised</th>
								<th class="text-left px-3 py-2">Title</th>
								<th class="text-left px-3 py-2">Status</th>
								<th class="text-right px-3 py-2">Cost impact</th>
								<th class="text-left px-3 py-2">Recoverable</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="s in report.scope_changes"
								:key="s.id"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2 text-ink-500 whitespace-nowrap">
									{{ fmtDate(s.raised_date) }}
								</td>
								<td class="px-3 py-2 text-ink-900">{{ s.title }}</td>
								<td class="px-3 py-2"><StatusBadge :status="s.status" /></td>
								<td class="px-3 py-2 text-right tabular-nums">
									{{ fmtINR(s.impact) }}
								</td>
								<td class="px-3 py-2 text-ink-700">
									{{ s.recoverable ? "Yes" : "No" }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<!-- Issues / blockers -->
			<section v-if="report.blockers.length" class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Issues raised
				</h2>
				<ul class="space-y-2">
					<li
						v-for="b in report.blockers"
						:key="b.id"
						class="p-3 border border-danger-200 bg-danger-50/30 rounded-lg flex gap-3"
					>
						<span class="text-danger-700 text-base flex-shrink-0">🚩</span>
						<div class="flex-1 min-w-0">
							<div class="text-sm font-medium text-ink-900">{{ b.task }}</div>
							<div class="text-xs text-ink-700 mt-1 whitespace-pre-line">
								{{ b.note }}
							</div>
							<div class="text-[11px] text-ink-500 mt-1">
								{{ fmtDate(b.entry_date) }} · {{ b.owner }}
							</div>
						</div>
					</li>
				</ul>
			</section>

			<!-- Look-ahead -->
			<section class="report-section mb-6">
				<h2
					class="text-sm font-semibold text-ink-900 mb-2 uppercase tracking-wider text-[11px]"
				>
					Coming up · {{ fmtDate(lookAhead.start) }} → {{ fmtDate(lookAhead.end) }}
				</h2>
				<div
					v-if="report.look_ahead_tasks.length"
					class="border border-ink-200 rounded-lg overflow-hidden"
				>
					<table class="w-full text-xs">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">Due</th>
								<th class="text-left px-3 py-2">Task</th>
								<th class="text-left px-3 py-2">Status</th>
								<th class="text-right px-3 py-2">Progress</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(t, i) in report.look_ahead_tasks"
								:key="i"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2 text-ink-500 whitespace-nowrap">
									{{ fmtDate(t.due) }}
								</td>
								<td class="px-3 py-2 text-ink-900">{{ t.name }}</td>
								<td class="px-3 py-2"><StatusBadge :status="t.status" /></td>
								<td class="px-3 py-2 text-right tabular-nums text-ink-700">
									{{ t.progress }}%
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div v-else class="text-xs text-ink-500 italic">
					No tasks due in the look-ahead window.
				</div>
			</section>

			<footer
				class="report-section mt-8 pt-4 border-t border-ink-200 text-[11px] text-ink-500 flex items-center justify-between"
			>
				<div>Generated {{ generatedOnLabel() }}</div>
				<div>BuildSuite Core · {{ project.code }}</div>
			</footer>
		</main>
	</div>
</template>

<style scoped>
.page-break-inside-avoid {
	page-break-inside: avoid;
}
@media print {
	.report-section {
		page-break-inside: avoid;
	}
	.report-section h2 {
		break-after: avoid-page;
	}
}
</style>
