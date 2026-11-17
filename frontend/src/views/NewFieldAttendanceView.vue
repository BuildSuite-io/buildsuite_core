<script setup>
// New Field Attendance — one sheet per project per day. Draft only; submitted
// from Desk. The header block and roster helpers are shared with the detail view
// via AttendanceFormFields / useAttendanceSheet.

import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
// Custom Fields, controls and save hooks an installed app adds to this form (sdk/useExtensionFields).
import ExtensionSlot from "@/components/ExtensionSlot.vue";
import { useExtensionFields } from "@/sdk/useExtensionFields";
import { useFormErrors } from "@/composables/useFormErrors";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { useAttendanceSheet } from "@/composables/useAttendanceSheet";
import { usePermissions } from "@/composables/usePermissions";
import { saveFieldAttendance } from "@/data/fieldAttendanceApi";
import { ATTENDANCE_STATUSES, validateFieldAttendance } from "@/utils/workforceForms";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import AttendanceFormFields from "@/components/AttendanceFormFields.vue";
import AttendanceTableActions from "@/components/AttendanceTableActions.vue";
import AttendanceEmployeeTable from "@/components/AttendanceEmployeeTable.vue";
import AttendanceBulkSelectModal from "@/components/AttendanceBulkSelectModal.vue";

const router = useRouter();
const { canCreate } = usePermissions();
const { projectLabel } = useProjectOptions();

const form = reactive({
	project: "",
	date: new Date().toISOString().slice(0, 10),
	status: "Present",
	overtime_hours: 0,
	comments: "",
	cost_code: null,
	employee_list: [],
});
const ext = useExtensionFields("Field Attendance", form);
ext.defaults();

const {
	inTable,
	addRow,
	addWorkers,
	setHeaderStatus,
	setHeaderOvertime,
	setHeaderComments,
	setHeaderCostCode,
	setHeaderProject,
	rosterToAdd,
	rosterTitle,
	addProjectRoster,
} = useAttendanceSheet(() => form);

const { errors, applyServerErrors, setErrors } = useFormErrors({
	project: "project",
	date: "date",
	employee_list: "employee_list",
});
const saving = ref(false);
const bulkOpen = ref(false);

function validate() {
	const e = validateFieldAttendance(form);
	setErrors(e);
	return Object.keys(e).length === 0;
}

function onCancel() {
	router.back();
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const payload = {
			...form,
			custom_fields: ext.payload(), // an installed app's Custom Fields
		};
		await ext.beforeSave(payload, form);
		const res = await saveFieldAttendance(payload);
		await ext.afterSave(res, { isNew: true });
		showToast(__("Attendance created"));
		router.push(`/field-attendance/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? __("Failed to create attendance"), "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Field Attendance"), to: "/field-attendance" },
	{ label: __("New") },
];
</script>

<template>
	<DeskPage :title="__('New Field Attendance')" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('fieldAttendance')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ __("You don't have permission to create a field attendance sheet.") }}
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? __('Creating…') : __('Create')"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>
			<ExtensionSlot :name="ext.slot('top')" :context="ext.context" />

			<AttendanceFormFields
				:form="form"
				:errors="errors"
				@status="setHeaderStatus"
				@overtime="setHeaderOvertime"
				@comments="setHeaderComments"
				@project="setHeaderProject"
				@cost-code="setHeaderCostCode"
			/>

			<AttendanceEmployeeTable
				:rows="form.employee_list"
				:statuses="ATTENDANCE_STATUSES"
				:error="errors.employee_list"
				:project-id="form.project"
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
			<ExtensionSlot :name="ext.slot('bottom')" :context="ext.context" />
		</DeskForm>

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
</template>
