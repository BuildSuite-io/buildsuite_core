<script setup>
// Delay Analysis — bespoke Site Execution report (the flat Query Report can't express it).
// Scope from ?project=; three views over the project + its sub-projects:
//   • Stages       — completion, slip (days past planned end while incomplete), downstream.
//   • Silent tasks — active tasks with no progress entry in the last 3 days (or ever).
//   • Weekly trend — progress entries filed / completions per week over 6 weeks.
// The server computes the full sets (buildsuite_core.api.delay_analysis); the per-view
// filters here narrow them client-side, with a live "N of M" count so a narrowed view is
// never mistaken for the whole set.
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getDelayAnalysis } from "@/data/delayAnalysisApi";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate } from "@/utils/format";

const route = useRoute();
const router = useRouter();

const projectId = ref(route.query.project || "");
const delayView = ref("stages");
const loading = ref(false);
const data = ref({ stages: [], silent_tasks: [], weekly_trend: [] });

// --- filters (client-side, over the loaded sets) ---
const BLANK = { q: "", from: "", to: "", lateOnly: false };
const f = reactive({ ...BLANK });
function clearFilters() {
	Object.assign(f, BLANK);
}
const anyFilter = computed(() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]));
const hit = (hay, needle) =>
	!needle ||
	String(hay || "")
		.toLowerCase()
		.includes(needle.trim().toLowerCase());
const inDates = (d) => (!f.from || (d || "") >= f.from) && (!f.to || (d || "") <= f.to);

const stagesShown = computed(() =>
	data.value.stages
		.filter((r) => hit(r.stage_name, f.q))
		.filter((r) => inDates(r.planned_end))
		.filter((r) => !f.lateOnly || r.overdue > 0)
);
const silentShown = computed(() => data.value.silent_tasks.filter((r) => hit(r.subject, f.q)));

// Per-view filter-bar config: which count to show, and the search placeholder.
const viewMeta = computed(() => {
	if (delayView.value === "silent") {
		return {
			shown: silentShown.value.length,
			total: data.value.silent_tasks.length,
			noun: "tasks",
			find: "Task…",
		};
	}
	if (delayView.value === "stages") {
		return {
			shown: stagesShown.value.length,
			total: data.value.stages.length,
			noun: "stages",
			find: "Stage…",
		};
	}
	return { shown: null, total: null, noun: "", find: "" }; // trend — a chart of everything
});

async function load(pid) {
	if (!pid) {
		data.value = { stages: [], silent_tasks: [], weekly_trend: [] };
		return;
	}
	loading.value = true;
	try {
		data.value = (await getDelayAnalysis(pid)) || {
			stages: [],
			silent_tasks: [],
			weekly_trend: [],
		};
	} catch (err) {
		showToast(err.message || "Failed to load Delay Analysis", "error");
		data.value = { stages: [], silent_tasks: [], weekly_trend: [] };
	} finally {
		loading.value = false;
	}
}
watch(projectId, (id) => {
	clearFilters(); // a filter from the previous project shouldn't leak onto the next
	router.replace({ path: route.path, query: { ...route.query, project: id || undefined } });
	load(id);
});
load(projectId.value);

const TABS = [
	["stages", "Stages"],
	["silent", "Silent tasks"],
	["trend", "Weekly trend"],
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Site Execution", to: "/site-execution" },
	{ label: "Delay Analysis" },
];
</script>

<template>
	<DeskPage title="Delay Analysis" :breadcrumbs="breadcrumbs" printable>
		<p class="text-xs text-ink-500 mb-3">
			Stages slipping, what sits downstream, silent tasks and the weekly completion trend.
		</p>

		<!-- Scope + filters -->
		<ReportFilters
			:active="anyFilter"
			:shown="viewMeta.shown"
			:total="viewMeta.total"
			:noun="viewMeta.noun"
			@clear="clearFilters"
		>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>Project</span
				>
				<span class="w-56 inline-block">
					<DeskLinkPicker
						v-model="projectId"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						placeholder="Pick a project…"
					/>
				</span>
			</label>

			<!-- The three delay views — a view switch rather than a filter, but it belongs
				 with the other controls. -->
			<div v-if="projectId" class="flex border border-ink-200 rounded-md overflow-hidden">
				<button
					v-for="v in TABS"
					:key="v[0]"
					type="button"
					class="px-3 py-1 text-xs border-l border-ink-200 first:border-l-0"
					:class="
						delayView === v[0]
							? 'bg-brand-50 text-brand-700 font-medium'
							: 'bg-white text-ink-600 hover:bg-ink-50'
					"
					@click="delayView = v[0]"
				>
					{{ v[1] }}
				</button>
			</div>

			<template v-if="projectId">
				<!-- Weekly trend is a chart of everything — nothing to narrow. -->
				<label v-if="delayView !== 'trend'" class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Find</span
					>
					<DeskInput v-model="f.q" :placeholder="viewMeta.find" class="!w-52" />
				</label>

				<label v-if="delayView === 'stages'" class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Planned end</span
					>
					<DeskInput v-model="f.from" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">to</span>
					<DeskInput v-model="f.to" type="date" class="!w-36" />
				</label>

				<label
					v-if="delayView === 'stages'"
					class="flex items-center gap-1.5 cursor-pointer"
				>
					<input v-model="f.lateOnly" type="checkbox" class="accent-brand-600" />
					<span class="text-[11px] text-ink-600">Slipping only</span>
				</label>
			</template>
		</ReportFilters>

		<div v-if="!projectId" class="text-sm text-ink-500 italic py-10 text-center">
			Pick a project to run this report.
		</div>

		<template v-else>
			<!-- Stages -->
			<div
				v-if="delayView === 'stages'"
				class="bg-white border border-ink-200 rounded-lg overflow-x-auto"
			>
				<table class="w-full text-xs" style="min-width: 720px">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2">Stage</th>
							<th class="text-left px-3 py-2">Planned</th>
							<th class="text-right px-3 py-2">Complete</th>
							<th class="text-right px-3 py-2">Slip</th>
							<th class="text-left px-3 py-2">Downstream</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="r in stagesShown" :key="r.name" class="border-t border-ink-100">
							<td class="px-3 py-2 text-ink-900">{{ r.stage_name }}</td>
							<td class="px-3 py-2 text-ink-500 whitespace-nowrap">
								{{ fmtDate(r.planned_start) }} → {{ fmtDate(r.planned_end) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								<template v-if="r.pct !== null">{{ r.pct }}%</template>
								<span v-else class="text-ink-400">—</span>
								<span class="text-[10px] text-ink-400 ml-1"
									>({{ r.done_count }}/{{ r.task_count }})</span
								>
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								<span v-if="r.overdue" class="text-danger-700 font-medium"
									>{{ r.overdue }}d</span
								>
								<span v-else class="text-success-700">—</span>
							</td>
							<td class="px-3 py-2 text-ink-600">
								{{ r.downstream.length ? r.downstream.join(", ") : "—" }}
							</td>
						</tr>
						<tr v-if="!stagesShown.length">
							<td colspan="5" class="px-3 py-8 text-center text-ink-400 italic">
								{{
									data.stages.length
										? "No stages match the filters."
										: "No stages planned on this project."
								}}
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- Silent tasks -->
			<div
				v-else-if="delayView === 'silent'"
				class="bg-white border border-ink-200 rounded-lg overflow-x-auto"
			>
				<table class="w-full text-xs" style="min-width: 560px">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2">Task</th>
							<th class="text-left px-3 py-2">Status</th>
							<th class="text-left px-3 py-2">Last entry</th>
							<th class="text-right px-3 py-2">Days silent</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="r in silentShown" :key="r.task" class="border-t border-ink-100">
							<td class="px-3 py-2 text-ink-900">{{ r.subject }}</td>
							<td class="px-3 py-2"><StatusBadge :status="r.status" size="xs" /></td>
							<td class="px-3 py-2 text-ink-500">
								{{ r.last ? fmtDate(r.last) : "Never" }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums"
								:class="
									(r.days ?? 99) >= 7
										? 'text-danger-700 font-medium'
										: 'text-warning-700'
								"
							>
								{{ r.days ?? "—" }}
							</td>
						</tr>
						<tr v-if="!silentShown.length">
							<td colspan="4" class="px-3 py-8 text-center text-ink-400 italic">
								{{
									data.silent_tasks.length
										? "No tasks match the filters."
										: "Every active task has reported in the last 3 days."
								}}
							</td>
						</tr>
					</tbody>
				</table>
			</div>

			<!-- Weekly trend -->
			<div v-else class="bg-white border border-ink-200 rounded-lg p-4">
				<div class="space-y-2.5">
					<div
						v-for="w in data.weekly_trend"
						:key="w.label"
						class="flex items-center gap-3"
					>
						<span class="text-[11px] text-ink-500 w-24 flex-shrink-0">{{
							fmtDate(w.label)
						}}</span>
						<div class="flex-1 h-3 bg-ink-100 rounded-full overflow-hidden">
							<div
								class="h-full bg-brand-500 rounded-full"
								:style="`width:${w.pct}%`"
							></div>
						</div>
						<span class="text-[11px] tabular-nums text-ink-700 w-32 text-right"
							>{{ w.entries }} entries · {{ w.completed }} completed</span
						>
					</div>
				</div>
				<p class="text-[11px] text-ink-400 mt-3">
					Progress entries filed per week, most recent last.
				</p>
			</div>
		</template>
	</DeskPage>
</template>
