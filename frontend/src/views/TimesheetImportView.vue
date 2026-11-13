<script setup>
// Timesheets from a spreadsheet: pick a project / date / cost code to pre-fill the template, download
// it, fill in hours, upload it. The upload is previewed first (one timesheet per worker per day, plus
// the rows left out and why); nothing is saved until you create them.

import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { usePermissions } from "@/composables/usePermissions";
import {
	timesheetTemplateUrl,
	previewTimesheetImport,
	createTimesheets,
} from "@/data/timesheetApi";
import { showToast } from "@/utils/appToast";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { canCreate } = usePermissions();
const { projectOptions } = useProjectOptions();

// --- the template ---------------------------------------------------------------------------------
const tplProject = ref("");
const tplDate = ref("");
const tplCode = ref(null);
function onTplProject(v) {
	tplProject.value = v || "";
	tplCode.value = null; // a code belongs to one project's estimate
}
const templateHref = computed(() =>
	timesheetTemplateUrl({
		project: tplProject.value,
		costCode: tplCode.value,
		date: tplDate.value,
	})
);

// --- the upload -----------------------------------------------------------------------------------
const plan = ref(null);
const fileName = ref("");
const busy = ref(false);
const error = ref("");

async function onFile(e) {
	const file = e.target.files?.[0];
	if (!file) return;
	fileName.value = file.name;
	plan.value = null;
	error.value = "";
	busy.value = true;
	try {
		plan.value = await previewTimesheetImport(file);
		if (!plan.value.header_found) {
			error.value = __(
				"No heading row found. The file needs at least Hours and one more column from the template."
			);
		}
	} catch (err) {
		error.value = err.message || __("The file could not be read.");
	} finally {
		busy.value = false;
		e.target.value = "";
	}
}

const ready = computed(() => (plan.value?.groups || []).filter((g) => !g.problem));
const problems = computed(() => (plan.value?.groups || []).filter((g) => g.problem));

async function create(submit) {
	busy.value = true;
	try {
		const res = await createTimesheets(ready.value, submit);
		if (res.failed?.length) {
			error.value = res.failed.map((f) => f.reason).join(" ");
		}
		if (res.created?.length) {
			showToast(__("{0} timesheets created", [res.created.length]));
			if (!res.failed?.length) router.push("/timesheets");
		}
	} catch (err) {
		error.value = err.message || __("The timesheets could not be created.");
	} finally {
		busy.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Timesheets"), to: "/timesheets" },
	{ label: __("Import") },
];
</script>

<template>
	<DeskPage
		:title="__('Import timesheets')"
		:subtitle="__('One row per worker per project and cost code per day.')"
		:breadcrumbs="breadcrumbs"
	>
		<div v-if="!canCreate('fieldAttendance')" class="text-sm text-ink-600 py-6">
			{{ __("You do not have permission to enter timesheets.") }}
		</div>
		<template v-else>
			<DeskSection :title="__('1. Download the template')" :cols="3">
				<DeskField
					:label="__('Project')"
					:hint="__('Optional. Lists its workers and its estimate\'s cost codes.')"
				>
					<DeskSearchableSelect
						:model-value="tplProject"
						:options="projectOptions"
						:placeholder="__('Every project')"
						:search-placeholder="__('Search projects…')"
						allow-clear
						@update:model-value="onTplProject"
					/>
				</DeskField>
				<DeskField :label="__('Date')" :hint="__('Optional. Filled in on every row.')">
					<DeskInput v-model="tplDate" type="date" />
				</DeskField>
				<DeskField
					:label="__('Cost code')"
					:hint="__('Optional. Filled in on every row.')"
				>
					<CostCodePicker
						v-model="tplCode"
						:project-id="tplProject"
						:placeholder="
							tplProject ? __('— Pick cost code —') : __('— Pick a project first —')
						"
					/>
				</DeskField>
				<div class="md:col-span-3">
					<a :href="templateHref" class="desk-save-btn !text-xs inline-block" download>
						{{ __("Download template") }}
					</a>
				</div>
			</DeskSection>

			<DeskSection :title="__('2. Upload it')" :cols="1" class="mt-6">
				<input
					type="file"
					accept=".xlsx,.csv"
					class="text-xs"
					:disabled="busy"
					data-timesheet-file
					@change="onFile"
				/>
				<p v-if="fileName" class="text-[11px] text-ink-500 mt-1">{{ fileName }}</p>
			</DeskSection>

			<div
				v-if="error"
				class="mt-4 border border-danger-200 bg-danger-50 px-4 py-3 text-xs text-danger-700"
				style="border-radius: 8px"
			>
				{{ error }}
			</div>

			<template v-if="plan?.header_found">
				<div
					v-if="plan.legacy_task"
					class="mt-4 border border-warning-200 bg-warning-50 px-4 py-3 text-xs text-ink-900"
					style="border-radius: 8px"
					data-legacy-task
				>
					{{
						__(
							"This file has the old Task column. Its hours come in without a cost code; download the new template to code them."
						)
					}}
				</div>

				<DeskSection :title="__('3. Check and create')" :cols="1" class="mt-6">
					<p class="text-xs text-ink-600">
						{{ __("{0} timesheets ready", [ready.length]) }}
						<template v-if="problems.length">
							· {{ __("{0} with a problem", [problems.length]) }}</template
						>
						<template v-if="plan.skipped.length">
							· {{ __("{0} rows left out", [plan.skipped.length]) }}</template
						>
						<template v-if="plan.blank">
							· {{ __("{0} blank rows ignored", [plan.blank]) }}</template
						>
					</p>

					<table
						v-if="plan.groups.length"
						class="w-full text-xs mt-3 border border-ink-200"
					>
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">{{ __("Worker") }}</th>
								<th class="text-left px-3 py-2">{{ __("Date") }}</th>
								<th class="text-right px-3 py-2">{{ __("Rows") }}</th>
								<th class="text-right px-3 py-2">{{ __("Hours") }}</th>
								<th class="text-left px-3 py-2"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="g in plan.groups"
								:key="g.key"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2 text-ink-900">{{ g.employee_name }}</td>
								<td class="px-3 py-2">{{ fmtDate(g.date) }}</td>
								<td class="px-3 py-2 text-right tabular-nums">
									{{ g.rows.length }}
								</td>
								<td class="px-3 py-2 text-right tabular-nums">{{ g.hours }}</td>
								<td
									class="px-3 py-2"
									:class="g.problem ? 'text-danger-700' : 'text-success-700'"
								>
									{{ g.problem || __("Ready") }}
								</td>
							</tr>
						</tbody>
					</table>

					<ul
						v-if="plan.skipped.length"
						class="mt-3 list-disc pl-5 text-xs text-danger-700 space-y-0.5"
					>
						<li v-for="s in plan.skipped" :key="s.row_no">
							{{ __("Row {0}", [s.row_no]) }}: {{ s.reason }}
						</li>
					</ul>

					<div class="mt-4 flex gap-2">
						<button
							type="button"
							class="desk-save-btn !text-xs"
							:disabled="busy || !ready.length"
							@click="create(false)"
						>
							{{ __("Create {0} draft timesheets", [ready.length]) }}
						</button>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
							style="border-radius: 6px"
							:disabled="busy || !ready.length"
							@click="create(true)"
						>
							{{ __("Create and submit") }}
						</button>
					</div>
				</DeskSection>
			</template>
		</template>
	</DeskPage>
</template>
