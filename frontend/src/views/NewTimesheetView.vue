<script setup>
// Timesheet entry — one worker, one day: rows of hours against a project and a cost code (where the
// labour cost lands on the project's estimate). Create and edit (draft only) share this form.
//
// A row is costed at the worker's daily rate over ITS project's full day (or the worker's overtime
// rate for an overtime row); the server does the real costing on save and keeps the result, this
// form only previews it with the same arithmetic.

import { ref, computed, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { usePermissions } from "@/composables/usePermissions";
import { getTimesheet, getCostingInfo, saveTimesheet } from "@/data/timesheetApi";
import { getFullDayHours } from "@/data/companyApi";
import { showToast } from "@/utils/appToast";
import { fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const route = useRoute();
const router = useRouter();
const { canCreate, canEdit } = usePermissions();
const { workerOptions } = useFieldEmployeeOptions();
const { projectOptions, projectLabel } = useProjectOptions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);

const localToday = () => new Date().toISOString().slice(0, 10);
let rowSeq = 0;
const blankRow = (project = null) => ({
	key: `r${++rowSeq}`,
	project,
	cost_code: null,
	hours: "",
	is_overtime: false,
	description: "",
});

const form = ref({
	employee: route.query.employee || "",
	date: route.query.date || localToday(),
	note: "",
	rows: [blankRow()],
});
const loading = ref(false);

// --- the header cost code (form-only, never stored) ----------------------------------------------
// It belongs to the first row's project. Picking it sets every row on that project; a row can then be
// coded on its own, until the header is picked again.
const headerProject = computed(() => form.value.rows.find((r) => r.project)?.project || null);
const otherProjects = computed(() =>
	form.value.rows.some((r) => r.project && r.project !== headerProject.value)
);
const common = ref({ project: null, code: null });
const commonCode = computed(() =>
	common.value.project && common.value.project === headerProject.value ? common.value.code : null
);
const sameCode = (a, b) =>
	!!a &&
	!!b &&
	(a.item_code || "") === (b.item_code || "") &&
	(a.group_code || "") === (b.group_code || "");

function setCommonCode(v) {
	common.value = { project: headerProject.value, code: v || null };
	for (const r of form.value.rows)
		if (r.project === headerProject.value) r.cost_code = v || null;
}
const commonHint = computed(() =>
	otherProjects.value
		? __("Applies to every row on {0}. Where the labour cost lands on the estimate.", [
				projectLabel(headerProject.value) || __("the first project"),
		  ])
		: __("Applies to all rows. Where the labour cost lands on the estimate.")
);

// A cost code belongs to one project's estimate: a row moved to another project takes the header code
// when it was picked for that project, and is uncoded otherwise.
function onProject(r, id) {
	if (id === r.project) return;
	r.project = id;
	r.cost_code = common.value.code && common.value.project === id ? common.value.code : null;
}
function addRow() {
	const last = form.value.rows[form.value.rows.length - 1];
	const r = blankRow();
	if (last?.project) onProject(r, last.project);
	form.value.rows.push(r);
}
function removeRow(r) {
	form.value.rows = form.value.rows.filter((x) => x.key !== r.key);
	if (!form.value.rows.length) form.value.rows.push(blankRow());
}

// --- costing preview -----------------------------------------------------------------------------
const info = ref(null);
const fullDays = ref({}); // project -> hours in its full day
async function loadInfo() {
	info.value = null;
	if (!form.value.employee) return;
	try {
		info.value = await getCostingInfo(
			form.value.employee,
			headerProject.value,
			form.value.date
		);
	} catch {
		info.value = null;
	}
}
watch(() => [form.value.employee, headerProject.value, form.value.date], loadInfo);

watch(
	() => form.value.rows.map((r) => r.project),
	async (projects) => {
		for (const p of new Set(projects.filter(Boolean))) {
			if (fullDays.value[p] != null) continue;
			fullDays.value[p] = null; // mark in flight
			try {
				fullDays.value[p] = (await getFullDayHours({ project: p }))?.hours ?? null;
			} catch {
				fullDays.value[p] = undefined;
			}
		}
	},
	{ immediate: true }
);

const dayOf = (r) =>
	fullDays.value[r.project || headerProject.value] || info.value?.full_day_hours || 0;
const rate = (r) => {
	if (!info.value) return 0;
	if (r.is_overtime) return Number(info.value.overtime_rate) || 0;
	const day = dayOf(r);
	return day ? Math.round((Number(info.value.daily_rate) / day) * 100) / 100 : 0;
};
const amount = (r) => Math.round((Number(r.hours) || 0) * rate(r) * 100) / 100;
const totals = computed(() => {
	const rows = form.value.rows;
	const sum = (xs, f) => Math.round(xs.reduce((a, r) => a + f(r), 0) * 100) / 100;
	return {
		hours: sum(rows, (r) => Number(r.hours) || 0),
		ot: sum(
			rows.filter((r) => r.is_overtime),
			(r) => Number(r.hours) || 0
		),
		cost: sum(rows, amount),
	};
});

// Rows nobody touched are not part of the timesheet.
const usedRows = computed(() =>
	form.value.rows.filter((r) => r.project || String(r.hours).trim() !== "" || r.description)
);
const issues = computed(() => {
	const out = [];
	if (!form.value.employee) out.push(__("Pick an employee."));
	if (!form.value.date) out.push(__("Pick a date."));
	if (!usedRows.value.length) out.push(__("Add at least one row of hours."));
	usedRows.value.forEach((r, i) => {
		const n = i + 1;
		if (!r.project) out.push(__("Row {0}: pick a project.", [n]));
		const h = Number(r.hours);
		if (!(h > 0 && h <= 24)) out.push(__("Row {0}: hours must be above 0 and up to 24.", [n]));
	});
	if (totals.value.hours > 24)
		out.push(__("{0} hours in one day is more than 24.", [totals.value.hours]));
	return out;
});

const tried = ref(false);
const saveErrors = ref([]);
const saving = ref(false);
async function save(submit = false) {
	tried.value = true;
	saveErrors.value = [];
	if (issues.value.length) return;
	saving.value = true;
	try {
		const ts = await saveTimesheet({
			name: editingId.value || undefined,
			employee: form.value.employee,
			date: form.value.date,
			note: form.value.note,
			submit,
			rows: usedRows.value.map((r) => ({
				project: r.project,
				cost_code: r.cost_code || null,
				hours: Number(r.hours),
				is_overtime: r.is_overtime ? 1 : 0,
				description: r.description,
			})),
		});
		showToast(submit ? __("Timesheet submitted") : __("Timesheet saved"));
		router.push(`/timesheets/${ts.name}`);
	} catch (err) {
		saveErrors.value = [err.message || __("The timesheet could not be saved.")];
	} finally {
		saving.value = false;
	}
}
const cancel = () => router.back();

const pageTitle = computed(() =>
	isEdit.value ? __("Edit {0}", [editingId.value]) : __("New timesheet")
);
const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Timesheets"), to: "/timesheets" },
	...(isEdit.value
		? [{ label: editingId.value, to: `/timesheets/${editingId.value}` }, { label: __("Edit") }]
		: [{ label: __("New") }]),
]);

onMounted(async () => {
	if (!isEdit.value) {
		if (!canCreate("fieldAttendance")) router.replace("/timesheets");
		return;
	}
	loading.value = true;
	try {
		const ts = await getTimesheet(editingId.value);
		if (ts.docstatus !== 0 || !canEdit("fieldAttendance")) {
			router.replace(`/timesheets/${editingId.value}`);
			return;
		}
		form.value = {
			employee: ts.employee,
			date: ts.date,
			note: ts.note || "",
			rows: ts.rows.map((r) => ({
				key: `r${++rowSeq}`,
				project: r.project,
				cost_code: r.cost_code,
				hours: r.hours,
				is_overtime: !!r.is_overtime,
				description: r.description || "",
			})),
		};
		// When the form opens, the header shows the code if all rows on that project share one.
		const hp = headerProject.value;
		if (hp) {
			const onIt = form.value.rows.filter((r) => r.project === hp);
			if (onIt.every((r) => sameCode(r.cost_code, onIt[0].cost_code))) {
				common.value = { project: hp, code: onIt[0].cost_code };
			}
		}
		loadInfo();
	} catch (err) {
		showToast(err.message || __("Could not load the timesheet."), "error");
		router.replace("/timesheets");
	} finally {
		loading.value = false;
	}
});
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<div v-if="loading" class="text-sm text-ink-500 py-8">{{ __("Loading…") }}</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="isEdit ? __('Save changes') : __('Save draft')"
					@save="save(false)"
					@cancel="cancel"
				>
					<template #menu>
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
							style="border-radius: 6px"
							:disabled="saving"
							@click="save(true)"
						>
							{{ __("Save and submit") }}
						</button>
					</template>
				</DeskActionBar>
			</template>

			<DeskSection :title="__('Header')" :cols="3">
				<DeskField :label="__('Employee')" required>
					<DeskSearchableSelect
						v-model="form.employee"
						:options="workerOptions"
						:placeholder="__('Pick an employee…')"
						:search-placeholder="__('Search by name or code…')"
					/>
				</DeskField>
				<DeskField :label="__('Date')" required>
					<DeskInput v-model="form.date" type="date" />
				</DeskField>
				<DeskField :label="__('Cost code')" :hint="commonHint">
					<CostCodePicker
						:model-value="commonCode"
						:project-id="headerProject || ''"
						:placeholder="
							headerProject
								? __('— Pick cost code —')
								: __('— Pick a row\'s project first —')
						"
						@update:model-value="setCommonCode"
					/>
				</DeskField>
				<div v-if="info" class="md:col-span-3 text-xs text-ink-600" data-costing-line>
					{{ info.trade || __("Worker") }} · {{ fmtINR(info.hourly_rate) }}
					{{ __("an hour") }}
					<span class="text-ink-500"
						>({{ __("daily rate") }} {{ fmtINR(info.daily_rate) }} ÷
						{{ info.full_day_hours }} h,
						{{ __("the full day") }}
						<template v-if="headerProject"
							>{{ __("on") }} {{ info.project_name }}</template
						>)</span
					>
					· {{ __("overtime") }} {{ fmtINR(info.overtime_rate) }} {{ __("an hour") }}
				</div>
			</DeskSection>

			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						{{ __("Hours") }}
					</h3>
					<span class="text-xs text-ink-500">{{
						__("One row per project and cost code worked on.")
					}}</span>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 1040px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-2 py-2 w-8">#</th>
								<th class="text-left px-2 py-2 w-56">{{ __("Project") }}</th>
								<th class="text-left px-2 py-2 w-64">{{ __("Cost code") }}</th>
								<th class="text-right px-2 py-2 w-20">{{ __("Hours") }}</th>
								<th class="text-center px-2 py-2 w-12">{{ __("OT") }}</th>
								<th class="text-left px-2 py-2" style="min-width: 200px">
									{{ __("Description") }}
								</th>
								<th class="text-right px-2 py-2 w-24">{{ __("Rate / hr") }}</th>
								<th class="text-right px-2 py-2 w-24">{{ __("Amount") }}</th>
								<th class="w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(r, i) in form.rows"
								:key="r.key"
								class="border-t border-ink-100 align-top"
							>
								<td class="px-2 py-2 text-ink-500 tabular-nums">{{ i + 1 }}</td>
								<td class="px-2 py-1.5">
									<div class="w-56">
										<DeskSearchableSelect
											:model-value="r.project"
											:options="projectOptions"
											:placeholder="__('Project…')"
											:search-placeholder="__('Search projects…')"
											@update:model-value="(v) => onProject(r, v)"
										/>
									</div>
								</td>
								<td class="px-2 py-1.5">
									<div class="w-64">
										<CostCodePicker
											v-model="r.cost_code"
											:project-id="r.project || ''"
											:placeholder="
												r.project
													? __('— Not coded —')
													: __('— Pick the project first —')
											"
										/>
									</div>
								</td>
								<td class="px-2 py-1.5">
									<input
										v-model="r.hours"
										type="number"
										min="0"
										max="24"
										step="0.25"
										class="desk-input !text-xs text-right tabular-nums"
										:aria-label="`${__('Hours')}, ${__('row')} ${i + 1}`"
									/>
								</td>
								<td class="px-2 py-2 text-center">
									<input
										v-model="r.is_overtime"
										type="checkbox"
										class="accent-brand-600"
										:aria-label="`${__('Overtime')}, ${__('row')} ${i + 1}`"
									/>
								</td>
								<td class="px-2 py-1.5">
									<input
										v-model="r.description"
										type="text"
										class="desk-input !text-xs"
										:placeholder="__('What was done')"
										:aria-label="`${__('Description')}, ${__('row')} ${i + 1}`"
									/>
								</td>
								<td class="px-2 py-2 text-right tabular-nums text-ink-600">
									{{ info ? fmtINR(rate(r)) : "—" }}
								</td>
								<td class="px-2 py-2 text-right tabular-nums text-ink-900">
									{{ info ? fmtINR(amount(r)) : "—" }}
								</td>
								<td class="px-1 py-2 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-700"
										:aria-label="`${__('Remove row')} ${i + 1}`"
										@click="removeRow(r)"
									>
										&times;
									</button>
								</td>
							</tr>
						</tbody>
						<tfoot class="border-t border-ink-200">
							<tr>
								<td colspan="3" class="px-2 py-2">
									<button
										type="button"
										class="text-xs text-brand-700 hover:underline"
										@click="addRow"
									>
										{{ __("+ Add row") }}
									</button>
								</td>
								<td
									class="px-2 py-2 text-right tabular-nums font-semibold"
									:class="totals.hours > 24 ? 'text-danger-700' : 'text-ink-900'"
								>
									{{ totals.hours }}
								</td>
								<td
									class="px-2 py-2 text-center text-[11px] text-ink-500 tabular-nums"
								>
									{{ totals.ot ? totals.ot + " OT" : "" }}
								</td>
								<td colspan="2" class="px-2 py-2 text-right text-ink-500">
									{{ __("Labour cost") }}
								</td>
								<td
									class="px-2 py-2 text-right tabular-nums font-semibold text-ink-900"
								>
									{{ fmtINR(totals.cost) }}
								</td>
								<td></td>
							</tr>
						</tfoot>
					</table>
				</div>
			</section>

			<DeskSection :title="__('Note')" :cols="1" class="mt-6">
				<DeskField
					:label="__('Note')"
					:hint="__('Optional. Anything the person reviewing this should know.')"
				>
					<DeskInput v-model="form.note" />
				</DeskField>
			</DeskSection>

			<div
				v-if="(tried && issues.length) || saveErrors.length"
				class="mt-4 border border-danger-200 bg-danger-50 px-4 py-3"
				style="border-radius: 8px"
			>
				<div class="text-xs font-semibold text-danger-700 mb-1">
					{{ __("Not saved yet:") }}
				</div>
				<ul class="list-disc pl-5 text-xs text-danger-700 space-y-0.5">
					<li v-for="(e, i) in saveErrors.length ? saveErrors : issues" :key="i">
						{{ e }}
					</li>
				</ul>
			</div>
		</DeskForm>
	</DeskPage>
</template>
