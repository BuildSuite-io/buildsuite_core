<script setup>
// The "Header" block, shared by both Field Attendance forms. The bulk-apply the
// hints promise lives in useAttendanceSheet().

import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { activeCompanyFilter } from "@/composables/useActiveCompany";
import { ATTENDANCE_STATUSES } from "@/utils/workforceForms";
import { __ } from "@/utils/translate";

defineProps({
	form: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});
// The three "applies to all rows" controls report upward instead of writing the
// header directly — useAttendanceSheet owns both the header value and the rows,
// so the two can never disagree.
const emit = defineEmits(["status", "overtime", "comments", "project"]);

// Project picker scoped to the switcher's working company (per-company projects).
const companyFilter = activeCompanyFilter();
</script>

<template>
	<DeskSection :title="__('Header')" :cols="3">
		<DeskField :label="__('Project')" required :error="errors.project">
			<DeskLinkPicker
				:model-value="form.project"
				doctype="Project"
				label-field="project_name"
				value-field="name"
				:filters="companyFilter"
				:placeholder="__('Pick a project…')"
				:search-placeholder="__('Search projects…')"
				@update:model-value="(v) => emit('project', v)"
			/>
		</DeskField>
		<DeskField :label="__('Date')" required :error="errors.date">
			<DeskInput v-model="form.date" type="date" />
		</DeskField>
		<DeskField :label="__('Status')" :hint="__('Applies to all rows.')">
			<DeskSelect :model-value="form.status" @update:model-value="(v) => emit('status', v)">
				<option v-for="s in ATTENDANCE_STATUSES" :key="s" :value="s">{{ __(s) }}</option>
			</DeskSelect>
		</DeskField>
		<DeskField :label="__('Task (optional)')" :hint="__('Books the whole sheet to one task.')">
			<DeskLinkPicker
				v-model="form.task"
				doctype="Task"
				label-field="subject"
				value-field="name"
				:filters="form.project ? [['project', '=', form.project]] : []"
				:placeholder="__('Deploy to task…')"
			/>
		</DeskField>
		<DeskField :label="__('Crew (optional)')" :hint="__('Records which gang worked this sheet.')">
			<DeskLinkPicker
				v-model="form.crew"
				doctype="Crew"
				label-field="crew_name"
				value-field="name"
				:placeholder="__('Pick a crew…')"
			/>
		</DeskField>
		<DeskField :label="__('Overtime hours')" :hint="__('Applies to all rows.')">
			<DeskInput
				:model-value="form.overtime_hours"
				type="number"
				min="0"
				:disabled="form.status === 'Absent'"
				@update:model-value="(v) => emit('overtime', Number(v) || 0)"
			/>
		</DeskField>
		<div class="md:col-span-3">
			<DeskField :label="__('Comments')" :hint="__('Applies to all rows.')">
				<DeskInput
					:model-value="form.comments"
					@update:model-value="(v) => emit('comments', v)"
				/>
			</DeskField>
		</div>
	</DeskSection>
</template>
