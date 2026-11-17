<script setup>
// Labour Cost Summary — hours, man-days and what labour cost, by project, cost code or worker,
// from submitted attendance AND timesheets.
//
// Every figure comes from buildsuite_core.api.labour_cost_summary, which reads the two registers
// (Labour and Overtime Attendance) where both submitted sheets and submitted timesheets write.
//
//   Hours        regular hours only; overtime is separate (OT hrs)
//   Man-days     each row's regular hours over the full day kept on it, added up
//   Regular cost the Labour register's wage; OT cost the Overtime register's

import { computed, reactive, ref, watch } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { getLabourCostSummary } from "@/data/workforceApi";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { fmtINR, fmtDate } from "@/utils/format";
import { fmtManDays } from "@/utils/fullDay";
import { __ } from "@/utils/translate";

// --------------------------------------------------------------- filters ---
const BLANK = { project: "", worker: "", from: "", to: "", source: "" };
const f = reactive({ ...BLANK });
const groupBy = ref("project"); // project | code | worker
const anyFilter = computed(() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]));
function clearFilters() {
	Object.assign(f, BLANK);
}

// ------------------------------------------------------------------ data ---
const data = ref(null);
const error = ref("");
const loading = ref(false);
let ticket = 0;

async function load() {
	const mine = ++ticket;
	loading.value = true;
	error.value = "";
	try {
		const res = await getLabourCostSummary({
			project: f.project,
			worker: f.worker,
			from_date: f.from,
			to_date: f.to,
			source: f.source,
			group_by: groupBy.value,
		});
		if (mine === ticket) data.value = res;
	} catch (e) {
		if (mine === ticket) error.value = e.message;
	} finally {
		if (mine === ticket) loading.value = false;
	}
}
watch([() => ({ ...f }), groupBy, useActiveCompany()], load, { immediate: true, deep: true });

const rows = computed(() => data.value?.rows || []);
const totals = computed(() => data.value?.totals || {});
const drafts = computed(() => data.value?.drafts || 0);
const projectOptions = computed(() => data.value?.projects || []);
const workerOptions = computed(() => data.value?.workers || []);

const period = computed(() => {
	const p = data.value?.period || {};
	if (!p.from) return "";
	return p.from === p.to ? fmtDate(p.from) : `${fmtDate(p.from)} – ${fmtDate(p.to)}`;
});

// ------------------------------------------------------------- formatting ---
const dash = (n) => !(Math.abs(Number(n) || 0) > 0.0001);
const hrs = (n) =>
	dash(n)
		? "—"
		: (Number(n) || 0).toLocaleString("en-IN", {
				minimumFractionDigits: 1,
				maximumFractionDigits: 1,
		  });
const md = (n) => (dash(n) ? "—" : fmtManDays(n));
const money = (n) => (dash(n) ? "—" : fmtINR(n));
const share = (n) => (dash(n) ? "—" : `${Number(n).toFixed(0)}%`);
// Past a fifth of the bill, overtime is worth a look (as in Site Attendance Summary).
const shareClass = (n) => (n > 20 ? "text-warning-700 font-medium" : "text-ink-500");

const GROUPS = [
	["project", "By project"],
	["code", "By cost code"],
	["worker", "By worker"],
];
const firstLabel = computed(
	() => ({ project: __("Project"), code: __("Cost code"), worker: __("Worker") }[groupBy.value])
);
const noun = computed(
	() =>
		({ project: __("projects"), code: __("cost codes"), worker: __("workers") }[groupBy.value])
);

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Labour Cost Summary") },
];
</script>

<template>
	<DeskPage
		:title="__('Labour Cost Summary')"
		:subtitle="
			__(
				'Hours, man-days and what labour cost each project, from submitted attendance and timesheets.'
			)
		"
		:breadcrumbs="breadcrumbs"
		printable
	>
		<ReportFilters :active="anyFilter" :shown="rows.length" :noun="noun" @clear="clearFilters">
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Project")
				}}</span>
				<span class="w-52 inline-block">
					<DeskSearchableSelect
						v-model="f.project"
						:options="projectOptions"
						allow-clear
						:placeholder="__('All projects')"
						:search-placeholder="__('Search…')"
					/>
				</span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Worker")
				}}</span>
				<span class="w-48 inline-block">
					<DeskSearchableSelect
						v-model="f.worker"
						:options="workerOptions"
						allow-clear
						:placeholder="__('All workers')"
						:search-placeholder="__('Search…')"
					/>
				</span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Period")
				}}</span>
				<DeskInput v-model="f.from" type="date" class="!w-36" :aria-label="__('From')" />
				<span class="text-[11px] text-ink-400">{{ __("to") }}</span>
				<DeskInput v-model="f.to" type="date" class="!w-36" :aria-label="__('To')" />
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">{{
					__("Captured as")
				}}</span>
				<DeskSelect v-model="f.source" class="!w-32" :aria-label="__('Captured as')">
					<option value="">{{ __("All") }}</option>
					<option value="Attendance">{{ __("Attendance") }}</option>
					<option value="Timesheet">{{ __("Timesheet") }}</option>
				</DeskSelect>
			</label>
			<div
				class="flex border border-ink-200 rounded-md overflow-hidden"
				role="group"
				:aria-label="__('Group by')"
			>
				<button
					v-for="g in GROUPS"
					:key="g[0]"
					type="button"
					class="px-3 py-1 text-xs border-l border-ink-200 first:border-l-0"
					:class="
						groupBy === g[0]
							? 'bg-brand-50 text-brand-700 font-medium'
							: 'bg-white text-ink-600 hover:bg-ink-50'
					"
					:aria-pressed="groupBy === g[0]"
					@click="groupBy = g[0]"
				>
					{{ __(g[1]) }}
				</button>
			</div>
		</ReportFilters>

		<div
			v-if="error"
			class="border border-danger-200 bg-danger-50 text-danger-700 text-sm px-4 py-3"
			style="border-radius: 8px"
		>
			{{ error }}
		</div>

		<template v-else-if="rows.length">
			<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						{{ __("Workers") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums"
						data-tile="workers"
					>
						{{ totals.workers }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						{{ __("Hours") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums"
						data-tile="hours"
					>
						{{ hrs(totals.hours) }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						{{ __("Man-days") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums"
						data-tile="man-days"
					>
						{{ md(totals.man_days) }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						{{ __("Overtime") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums"
						data-tile="overtime"
					>
						{{ hrs(totals.ot_hours) }}
						<span class="text-[11px] font-normal text-ink-500">{{ __("hrs") }}</span>
					</div>
				</div>
				<div
					class="bg-white border border-ink-200 px-3 py-2 col-span-2 md:col-span-1"
					style="border-radius: 6px"
				>
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						{{ __("Labour cost") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums"
						data-tile="labour-cost"
					>
						{{ fmtINR(totals.total) }}
					</div>
				</div>
			</div>
			<p v-if="period" class="text-[11px] text-ink-500 mb-3">
				{{ __("Covering {0}.", [period]) }}
			</p>

			<div class="bg-white border border-ink-200 overflow-x-auto" style="border-radius: 8px">
				<table class="w-full text-xs" style="min-width: 900px" data-report-table>
					<thead
						class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200"
					>
						<tr>
							<th class="text-left px-3 py-2">{{ firstLabel }}</th>
							<th v-if="groupBy === 'code'" class="text-left px-3 py-2">
								{{ __("Project") }}
							</th>
							<th class="text-right px-3 py-2">
								{{ groupBy === "worker" ? __("Projects") : __("Workers") }}
							</th>
							<th v-if="groupBy === 'worker'" class="text-right px-3 py-2">
								{{ __("Days worked") }}
							</th>
							<th class="text-right px-3 py-2">{{ __("Hours") }}</th>
							<th class="text-right px-3 py-2">{{ __("Man-days") }}</th>
							<th class="text-right px-3 py-2">{{ __("Regular cost") }}</th>
							<th class="text-right px-3 py-2">{{ __("OT hrs") }}</th>
							<th class="text-right px-3 py-2">{{ __("OT cost") }}</th>
							<th class="text-right px-3 py-2">{{ __("Total") }}</th>
							<th class="text-right px-3 py-2">{{ __("OT share") }}</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="r in rows"
							:key="r.key"
							class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50"
						>
							<td class="px-3 py-2">
								<div
									class="text-ink-900 font-medium"
									:class="[
										groupBy === 'code' && !r.uncoded ? 'font-mono' : '',
										r.uncoded ? 'italic text-ink-600' : '',
									]"
								>
									{{ r.label }}
								</div>
								<div v-if="r.sub" class="text-[10px] text-ink-500">
									{{ r.sub }}
								</div>
							</td>
							<td v-if="groupBy === 'code'" class="px-3 py-2 text-ink-700">
								{{ r.project_label }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">
								{{ groupBy === "worker" ? r.projects : r.workers }}
							</td>
							<td
								v-if="groupBy === 'worker'"
								class="px-3 py-2 text-right tabular-nums text-ink-700"
							>
								{{ r.days_worked || "—" }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ hrs(r.hours) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
								{{ md(r.man_days) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">
								{{ money(r.regular_cost) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">
								{{ hrs(r.ot_hours) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">
								{{ money(r.ot_cost) }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums text-ink-900 font-semibold"
							>
								{{ money(r.total) }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums"
								:class="shareClass(r.ot_share)"
							>
								{{ share(r.ot_share) }}
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="bg-ink-50 border-t border-ink-200 font-semibold text-ink-900">
							<td class="px-3 py-2">{{ __("Total") }}</td>
							<td v-if="groupBy === 'code'"></td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ groupBy === "worker" ? totals.projects : totals.workers }}
							</td>
							<td
								v-if="groupBy === 'worker'"
								class="px-3 py-2 text-right tabular-nums"
							>
								{{ totals.days_worked || "—" }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ hrs(totals.hours) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ md(totals.man_days) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ money(totals.regular_cost) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ hrs(totals.ot_hours) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ money(totals.ot_cost) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ money(totals.total) }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums"
								:class="shareClass(totals.ot_share)"
							>
								{{ share(totals.ot_share) }}
							</td>
						</tr>
					</tfoot>
				</table>
			</div>

			<p class="text-[11px] text-ink-500 mt-2" data-report-footer>
				{{
					__(
						"Man-days = hours ÷ the full day on each sheet. Attendance and timesheet entries are both counted; drafts aren't."
					)
				}}
				<template v-if="drafts">
					{{
						drafts === 1
							? __("1 draft not counted yet.")
							: __("{0} drafts not counted yet.", [drafts])
					}}
				</template>
			</p>
		</template>

		<div
			v-else-if="!loading"
			class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic"
			style="border-radius: 8px"
		>
			<template v-if="anyFilter">{{ __("Nothing matches these filters.") }}</template>
			<template v-else>{{
				__("No attendance or timesheets have been submitted yet.")
			}}</template>
			<div v-if="drafts" class="not-italic text-[11px] text-ink-500 mt-1">
				{{
					drafts === 1
						? __("1 draft not counted yet.")
						: __("{0} drafts not counted yet.", [drafts])
				}}
			</div>
		</div>
	</DeskPage>
</template>
