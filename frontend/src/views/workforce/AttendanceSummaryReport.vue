<script setup>
// Site Attendance Summary — the HR roll-up. The Labour and Overtime Attendance
// Registers are ledgers (one row per worker per day); nobody answers "what did
// Block A cost in labour last month" by scrolling hundreds of rows. This rolls
// both registers up together — labour and overtime — grouped by site or worker.
//
// Both registers are DERIVED from submitted Field Attendance, so nothing here is
// typed and nothing can disagree with the sheets. A draft sheet is in neither
// register, so it is not here either.

import { computed, reactive, ref } from "vue";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { fmtINR, fmtDate } from "@/utils/format";

const { projectName } = useProjectNames();

// Both registers, full set — submitted (and draft) rows, aggregated client-side.
const labourRes = useDocTypeList("Labour Attendance Register", {
	fields: [
		"name",
		"attendance_date",
		"employee",
		"employee_name",
		"project",
		"status",
		"daily_wage_calculated",
	],
	filters: [["docstatus", "<", 2]],
	orderBy: "attendance_date desc",
	pageLength: 0,
});
const overtimeRes = useDocTypeList("Overtime Attendance Register", {
	fields: [
		"name",
		"overtime_date",
		"employee",
		"employee_name",
		"project",
		"overtime_hours",
		"overtime_wage_calculated",
	],
	filters: [["docstatus", "<", 2]],
	orderBy: "overtime_date desc",
	pageLength: 0,
});

const labourRows = computed(() => labourRes.data || []);
const overtimeRows = computed(() => overtimeRes.data || []);

// Worker id → name, taken from whichever register row carries it.
const workerNames = computed(() => {
	const m = {};
	for (const r of [...labourRows.value, ...overtimeRows.value]) {
		if (r.employee && r.employee_name) m[r.employee] = r.employee_name;
	}
	return m;
});
const feName = (id) => workerNames.value[id] || id || "—";

// --------------------------------------------------------------- filters ---
const BLANK = { project: "", worker: "", from: "", to: "" };
const f = reactive({ ...BLANK });
const groupBy = ref("project"); // project | worker
const anyFilter = computed(() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]));
function clearFilters() {
	Object.assign(f, BLANK);
}

const projectOptions = computed(() =>
	[...new Set([...labourRows.value, ...overtimeRows.value].map((r) => r.project))]
		.filter(Boolean)
		.map((id) => ({ value: id, label: projectName(id) }))
		.sort((a, b) => a.label.localeCompare(b.label))
);
const workerOptions = computed(() =>
	[...new Set([...labourRows.value, ...overtimeRows.value].map((r) => r.employee))]
		.filter(Boolean)
		.map((id) => ({ value: id, label: feName(id) }))
		.sort((a, b) => a.label.localeCompare(b.label))
);

const keep = (r, dateField) => {
	const d = r[dateField] || "";
	if (f.project && r.project !== f.project) return false;
	if (f.worker && r.employee !== f.worker) return false;
	if (f.from && d < f.from) return false;
	if (f.to && d > f.to) return false;
	return true;
};
const labour = computed(() => labourRows.value.filter((r) => keep(r, "attendance_date")));
const overtime = computed(() => overtimeRows.value.filter((r) => keep(r, "overtime_date")));

// ----------------------------------------------------------------- rollup ---
// Man-days rather than a row count: a half day is half a day of work, and
// counting it as one would overstate what the site actually got.
function blank(key, label) {
	return {
		key,
		label,
		people: new Set(),
		dates: new Set(),
		full: 0,
		half: 0,
		absent: 0,
		wages: 0,
		otHours: 0,
		otWages: 0,
	};
}
const rows = computed(() => {
	const by = new Map();
	const bucket = (r) => {
		const k = groupBy.value === "project" ? r.project : r.employee;
		if (!by.has(k)) {
			by.set(k, blank(k, groupBy.value === "project" ? projectName(k) : feName(k)));
		}
		return by.get(k);
	};

	for (const la of labour.value) {
		const b = bucket(la);
		b.people.add(la.employee);
		if (la.attendance_date) b.dates.add(la.attendance_date);
		if (la.status === "Full Day") b.full++;
		else if (la.status === "Half Day") b.half++;
		else b.absent++;
		b.wages += Number(la.daily_wage_calculated) || 0;
	}
	for (const ot of overtime.value) {
		const b = bucket(ot);
		b.people.add(ot.employee);
		if (ot.overtime_date) b.dates.add(ot.overtime_date);
		b.otHours += Number(ot.overtime_hours) || 0;
		b.otWages += Number(ot.overtime_wage_calculated) || 0;
	}

	return [...by.values()]
		.map((b) => ({
			...b,
			workers: b.people.size,
			days: b.dates.size,
			manDays: b.full + b.half * 0.5,
			total: b.wages + b.otWages,
			// How much of the labour bill is overtime — the number that tells HR
			// whether a site is running hot or just running.
			otShare: b.wages + b.otWages > 0 ? (b.otWages / (b.wages + b.otWages)) * 100 : 0,
		}))
		.sort((a, b) => b.total - a.total);
});

const totals = computed(() =>
	rows.value.reduce(
		(a, r) => ({
			workers: a.workers + r.workers,
			manDays: a.manDays + r.manDays,
			absent: a.absent + r.absent,
			wages: a.wages + r.wages,
			otHours: a.otHours + r.otHours,
			otWages: a.otWages + r.otWages,
			total: a.total + r.total,
		}),
		{ workers: 0, manDays: 0, absent: 0, wages: 0, otHours: 0, otWages: 0, total: 0 }
	)
);

// Distinct people across the whole filtered set — summing per-row counts would
// double-count anyone who worked on two sites.
const distinctWorkers = computed(
	() => new Set([...labour.value, ...overtime.value].map((r) => r.employee)).size
);

const period = computed(() => {
	const all = [
		...labour.value.map((r) => r.attendance_date),
		...overtime.value.map((r) => r.overtime_date),
	]
		.filter(Boolean)
		.sort();
	if (!all.length) return "";
	return all[0] === all[all.length - 1]
		? fmtDate(all[0])
		: `${fmtDate(all[0])} – ${fmtDate(all[all.length - 1])}`;
});

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Site Attendance Summary" },
];
</script>

<template>
	<DeskPage
		title="Site Attendance Summary"
		subtitle="Days worked, overtime and what the labour cost — rolled up from submitted attendance."
		:breadcrumbs="breadcrumbs"
		printable
	>
		<ReportFilters
			:active="anyFilter"
			:shown="rows.length"
			:noun="groupBy === 'project' ? 'sites' : 'workers'"
			@clear="clearFilters"
		>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Site</span>
				<span class="w-52 inline-block">
					<DeskSearchableSelect
						v-model="f.project"
						:options="projectOptions"
						allow-clear
						placeholder="All sites"
						search-placeholder="Search…"
					/>
				</span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Worker</span>
				<span class="w-48 inline-block">
					<DeskSearchableSelect
						v-model="f.worker"
						:options="workerOptions"
						allow-clear
						placeholder="Everyone"
						search-placeholder="Search…"
					/>
				</span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Period</span>
				<DeskInput v-model="f.from" type="date" class="!w-36" />
				<span class="text-[11px] text-ink-400">to</span>
				<DeskInput v-model="f.to" type="date" class="!w-36" />
			</label>
			<div class="flex border border-ink-200 rounded-md overflow-hidden">
				<button
					v-for="g in [
						['project', 'By site'],
						['worker', 'By worker'],
					]"
					:key="g[0]"
					type="button"
					class="px-3 py-1 text-xs border-l border-ink-200 first:border-l-0"
					:class="
						groupBy === g[0]
							? 'bg-brand-50 text-brand-700 font-medium'
							: 'bg-white text-ink-600 hover:bg-ink-50'
					"
					@click="groupBy = g[0]"
				>
					{{ g[1] }}
				</button>
			</div>
		</ReportFilters>

		<template v-if="rows.length">
			<!-- Headline figures -->
			<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Workers</div>
					<div class="text-base font-semibold text-ink-900 tabular-nums">{{ distinctWorkers }}</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Man-days</div>
					<div class="text-base font-semibold text-ink-900 tabular-nums">{{ totals.manDays }}</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Overtime</div>
					<div class="text-base font-semibold text-ink-900 tabular-nums">
						{{ totals.otHours }} <span class="text-[11px] font-normal text-ink-500">hrs</span>
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Absences</div>
					<div
						class="text-base font-semibold tabular-nums"
						:class="totals.absent ? 'text-warning-700' : 'text-ink-900'"
					>
						{{ totals.absent }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Labour cost</div>
					<div class="text-base font-semibold text-ink-900 tabular-nums">{{ fmtINR(totals.total) }}</div>
				</div>
			</div>
			<p v-if="period" class="text-[11px] text-ink-500 mb-3">Covering {{ period }}.</p>

			<div class="bg-white border border-ink-200 overflow-x-auto" style="border-radius: 8px">
				<table class="w-full text-xs" style="min-width: 900px">
					<thead
						class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200"
					>
						<tr>
							<th class="text-left px-3 py-2">{{ groupBy === "project" ? "Site" : "Worker" }}</th>
							<th class="text-right px-3 py-2">{{ groupBy === "project" ? "Workers" : "Sites" }}</th>
							<th class="text-right px-3 py-2">Days</th>
							<th class="text-right px-3 py-2">Full</th>
							<th class="text-right px-3 py-2">Half</th>
							<th class="text-right px-3 py-2">Absent</th>
							<th class="text-right px-3 py-2">Man-days</th>
							<th class="text-right px-3 py-2">Wages</th>
							<th class="text-right px-3 py-2">OT hrs</th>
							<th class="text-right px-3 py-2">OT wages</th>
							<th class="text-right px-3 py-2">Total</th>
							<th class="text-right px-3 py-2">OT share</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="r in rows"
							:key="r.key"
							class="border-b border-ink-100 last:border-b-0 hover:bg-brand-50/40"
						>
							<td class="px-3 py-2">
								<div class="text-ink-900 font-medium">{{ r.label }}</div>
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ r.workers }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ r.days }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ r.full }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ r.half || "—" }}</td>
							<td
								class="px-3 py-2 text-right tabular-nums"
								:class="r.absent ? 'text-warning-700 font-medium' : 'text-ink-400'"
							>
								{{ r.absent || "—" }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">{{ r.manDays }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ fmtINR(r.wages) }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ r.otHours || "—" }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">
								{{ r.otWages ? fmtINR(r.otWages) : "—" }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-semibold">
								{{ fmtINR(r.total) }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums"
								:class="r.otShare > 20 ? 'text-warning-700 font-medium' : 'text-ink-500'"
							>
								{{ r.otShare ? r.otShare.toFixed(0) + "%" : "—" }}
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="bg-ink-50 border-t border-ink-200 font-semibold text-ink-900">
							<td class="px-3 py-2">Total</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ groupBy === "project" ? distinctWorkers : "" }}
							</td>
							<td colspan="4"></td>
							<td class="px-3 py-2 text-right tabular-nums">{{ totals.manDays }}</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(totals.wages) }}</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ totals.otHours }}</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(totals.otWages) }}</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(totals.total) }}</td>
							<td></td>
						</tr>
					</tfoot>
				</table>
			</div>

			<p class="text-[11px] text-ink-500 mt-2">
				A half day counts as half a man-day. Both halves come from submitted attendance sheets — a
				sheet left in draft is in neither register, so it is not here either.
			</p>
		</template>

		<div
			v-else
			class="border border-ink-200 px-5 py-10 text-center text-sm text-ink-400 italic"
			style="border-radius: 8px"
		>
			<template v-if="anyFilter">Nothing matches these filters.</template>
			<template v-else>No attendance has been submitted yet.</template>
		</div>
	</DeskPage>
</template>
