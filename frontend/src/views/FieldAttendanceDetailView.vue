<script setup>
// Field Attendance detail — view / edit / delete, draft only. A submitted sheet
// renders read-only: the doctype has no `cancel` permission.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useWorkflow } from "@/composables/useWorkflow";
import { useFormErrors } from "@/composables/useFormErrors";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { useAttendanceSheet } from "@/composables/useAttendanceSheet";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import {
	amendFieldAttendance,
	cancelFieldAttendance,
	getFieldAttendance,
	saveFieldAttendance,
	submitFieldAttendance,
} from "@/data/fieldAttendanceApi";
import {
	ATTENDANCE_STATUSES,
	DOCSTATUS_LABELS,
	validateFieldAttendance,
} from "@/utils/workforceForms";
import { fmtDate } from "@/utils/format";
import { isPermissionDenied } from "@/utils/frappeError";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import AccessDenied from "@/components/AccessDenied.vue";
import AttendanceFormFields from "@/components/AttendanceFormFields.vue";
import AttendanceTableActions from "@/components/AttendanceTableActions.vue";
import AttendanceEmployeeTable from "@/components/AttendanceEmployeeTable.vue";
import AttendanceBulkSelectModal from "@/components/AttendanceBulkSelectModal.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { projectLabel } = useProjectOptions();
const {
	active: wfActive,
	state: wfState,
	transitions: wfTransitions,
	refresh: refreshWorkflow,
	applyAction: applyWorkflowAction,
} = useWorkflow("Field Attendance");
const { errors, applyServerErrors, setErrors } = useFormErrors({
	project: "project",
	date: "date",
	employee_list: "employee_list",
});

const doc = ref(null);
const loading = ref(true);
const loadError = ref(null);
const editing = ref(false);
const saving = ref(false);
const bulkOpen = ref(false);
const form = ref({});

const accessDenied = computed(() => isPermissionDenied(loadError.value));

// The API returns the child rows; a list read would not.
async function load() {
	loading.value = true;
	loadError.value = null;
	try {
		doc.value = await getFieldAttendance(props.id);
		await refreshWorkflow(props.id);
	} catch (err) {
		doc.value = null;
		loadError.value = err;
	} finally {
		loading.value = false;
	}
}
// Not onMounted — the router reuses this component when only :id changes.
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => doc.value?.docstatus === 0);
const isSubmitted = computed(() => doc.value?.docstatus === 1);
const isCancelled = computed(() => doc.value?.docstatus === 2);
const busy = ref(false);
// A workflow owns the status label once active.
const docStatusLabel = computed(() =>
	wfActive.value
		? wfState.value || DOCSTATUS_LABELS[doc.value?.docstatus]
		: DOCSTATUS_LABELS[doc.value?.docstatus] || "Draft"
);
const rows = computed(() => doc.value?.employee_list || []);

const {
	inTable,
	addRow,
	addWorkers,
	setHeaderStatus,
	setHeaderOvertime,
	setHeaderComments,
	rosterToAdd,
	rosterTitle,
	addProjectRoster,
} = useAttendanceSheet(() => form.value);

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		project: d.project || "",
		date: d.date || "",
		status: d.status || "Present",
		overtime_hours: d.overtime_hours ?? 0,
		comments: d.comments || "",
		employee_list: (d.employee_list || []).map((r) => ({
			name: r.name,
			employee: r.employee,
			employee_name: r.employee_name,
			status: r.status,
			overtime_hours: r.overtime_hours,
			comments: r.comments,
			labour_rate: r.labour_rate,
			overtime_rate: r.overtime_rate,
		})),
	};
}

function startEdit() {
	form.value = snapshot();
	setErrors({});
	editing.value = true;
}
function cancelEdit() {
	editing.value = false;
}

function validate() {
	const e = validateFieldAttendance(form.value);
	setErrors(e);
	return Object.keys(e).length === 0;
}

async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		doc.value = await saveFieldAttendance({ name: props.id, ...form.value });
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update attendance", "error");
	} finally {
		saving.value = false;
	}
}

async function run(fn, okMsg) {
	busy.value = true;
	try {
		await fn();
		await load();
		showToast(okMsg);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Action failed", "error");
	} finally {
		busy.value = false;
	}
}

async function onSubmit() {
	const ok = await confirmDialog({
		title: `Submit ${props.id}?`,
		message:
			"This posts the attendance and generates the Labour and Overtime registers. A posted sheet is cancelled, not edited.",
		confirmLabel: "Submit",
	});
	if (ok) await run(() => submitFieldAttendance(props.id), "Attendance submitted");
}

async function onCancelSheet() {
	const ok = await confirmDialog({
		title: `Cancel ${props.id}?`,
		message:
			"This reverses the sheet — its Labour and Overtime register entries are cancelled with it. Amend afterwards to raise a corrected copy.",
		confirmLabel: "Cancel sheet",
		destructive: true,
	});
	if (ok) await run(() => cancelFieldAttendance(props.id), "Attendance cancelled");
}

async function onAmend() {
	busy.value = true;
	try {
		const copy = await amendFieldAttendance(props.id);
		router.push(`/field-attendance/${copy.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Could not amend", "error");
	} finally {
		busy.value = false;
	}
}

async function onWorkflowAction(action) {
	busy.value = true;
	try {
		await applyWorkflowAction(props.id, action);
		await load();
		showToast(`${action} done.`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Action failed", "error");
	} finally {
		busy.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${props.id}?`,
		message: "This draft attendance sheet will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Field Attendance", props.id);
		router.push("/field-attendance");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete attendance", "error");
	}
}

const subtitle = computed(() => {
	const d = doc.value;
	if (!d) return "";
	const project = d.project_name || projectLabel(d.project) || d.project;
	return `${project} · ${fmtDate(d.date)}`;
});

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Field Attendance", to: "/field-attendance" },
	{ label: props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.name"
		:subtitle="subtitle"
		:status="docStatusLabel"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="!editing && isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<button
				v-if="!editing && isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
			<button
				v-if="!editing && !wfActive && isDraft"
				type="button"
				class="desk-save-btn !text-xs"
				:disabled="busy"
				@click="onSubmit"
			>
				Submit
			</button>
			<button
				v-if="!editing && !wfActive && isSubmitted"
				type="button"
				class="text-xs px-2.5 py-1 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onCancelSheet"
			>
				Cancel
			</button>
			<button
				v-if="!editing && !wfActive && isCancelled"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onAmend"
			>
				Amend
			</button>
			<button
				v-for="t in !editing && wfActive ? wfTransitions : []"
				:key="t.action"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onWorkflowAction(t.action)"
			>
				{{ t.action }}
			</button>
			<button
				v-if="editing"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="cancelEdit"
			>
				Cancel
			</button>
			<button
				v-if="editing"
				type="button"
				class="desk-save-btn !text-xs"
				:disabled="saving"
				@click="saveEdit"
			>
				{{ saving ? "Saving…" : "Save" }}
			</button>
		</template>

		<!-- View mode -->
		<div v-if="!editing">
			<div
				v-if="!isDraft"
				class="mb-4 px-3 py-2 bg-ink-50 border border-ink-200 text-xs text-ink-600"
				style="border-radius: 6px"
			>
				This sheet is {{ docStatusLabel.toLowerCase() }} and can no longer be edited here.
			</div>

			<DeskSection title="Header" :cols="3">
				<DeskField label="Project">
					<div class="text-sm text-ink-900">
						{{ doc.project_name || projectLabel(doc.project) || "—" }}
					</div>
				</DeskField>
				<DeskField label="Date">
					<div class="text-sm text-ink-700">{{ fmtDate(doc.date) || "—" }}</div>
				</DeskField>
				<DeskField label="Status">
					<div class="text-sm text-ink-700">{{ doc.status || "—" }}</div>
				</DeskField>

				<DeskField label="Overtime hours">
					<div class="text-sm tabular-nums text-ink-700">
						{{ doc.overtime_hours || 0 }}
					</div>
				</DeskField>
				<div class="md:col-span-3">
					<DeskField label="Comments">
						<div class="text-sm text-ink-700">{{ doc.comments || "—" }}</div>
					</DeskField>
				</div>
			</DeskSection>

			<AttendanceEmployeeTable :rows="rows" :statuses="ATTENDANCE_STATUSES" />

			<p v-if="isDraft" class="text-[11px] text-ink-400 mt-3">
				Submit to post the attendance and generate the Labour and Overtime registers.
			</p>
		</div>

		<!-- Edit mode -->
		<div v-else>
			<AttendanceFormFields
				:form="form"
				:errors="errors"
				@status="setHeaderStatus"
				@overtime="setHeaderOvertime"
				@comments="setHeaderComments"
			/>

			<AttendanceEmployeeTable
				:rows="form.employee_list"
				:statuses="ATTENDANCE_STATUSES"
				:error="errors.employee_list"
				editable
				@remove="(i) => form.employee_list.splice(i, 1)"
			>
				<template #actions>
					<AttendanceTableActions
						:has-project="!!form.project"
						:roster-to-add="rosterToAdd.length"
						:roster-title="rosterTitle"
						@add-roster="addProjectRoster"
						@open-bulk="bulkOpen = true"
						@add-row="addRow"
					/>
				</template>
			</AttendanceEmployeeTable>
		</div>

		<AttendanceBulkSelectModal
			:open="bulkOpen"
			:project="form.project"
			:date="form.date"
			:project-label="projectLabel(form.project)"
			:existing="[...inTable]"
			@close="bulkOpen = false"
			@add="addWorkers"
		/>
	</DeskPage>

	<div v-else-if="loading" class="px-3 py-2 text-sm text-ink-500">Loading attendance…</div>

	<AccessDenied
		v-else-if="accessDenied"
		title="You don't have access to this attendance sheet"
		back-to="/field-attendance"
		back-label="Back to Field Attendance"
	/>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Field attendance not found.</div>
</template>
