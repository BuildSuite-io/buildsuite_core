<script setup>
// The "Header" block, shared by both Field Attendance forms. The bulk-apply the
// hints promise lives in useAttendanceSheet().

import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { ATTENDANCE_STATUSES } from "@/utils/workforceForms";

defineProps({
	form: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});
// The three "applies to all rows" controls report upward instead of writing the
// header directly — useAttendanceSheet owns both the header value and the rows,
// so the two can never disagree.
const emit = defineEmits(["status", "overtime", "comments"]);

const { projectOptions } = useProjectOptions();
</script>

<template>
	<DeskSection title="Header" :cols="3">
		<DeskField label="Project" required :error="errors.project">
			<DeskSearchableSelect
				v-model="form.project"
				:options="projectOptions"
				placeholder="Pick a project…"
				search-placeholder="Search projects…"
			/>
		</DeskField>
		<DeskField label="Date" required :error="errors.date">
			<DeskInput v-model="form.date" type="date" />
		</DeskField>
		<DeskField label="Status" hint="Applies to all rows.">
			<DeskSelect :model-value="form.status" @update:model-value="(v) => emit('status', v)">
				<option v-for="s in ATTENDANCE_STATUSES" :key="s">{{ s }}</option>
			</DeskSelect>
		</DeskField>
		<DeskField label="Overtime hours" hint="Applies to all rows.">
			<DeskInput
				:model-value="form.overtime_hours"
				type="number"
				min="0"
				:disabled="form.status === 'Absent'"
				@update:model-value="(v) => emit('overtime', Number(v) || 0)"
			/>
		</DeskField>
		<div class="md:col-span-3">
			<DeskField label="Comments" hint="Applies to all rows.">
				<DeskInput
					:model-value="form.comments"
					@update:model-value="(v) => emit('comments', v)"
				/>
			</DeskField>
		</div>
	</DeskSection>
</template>
