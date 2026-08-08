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
			<DeskSelect v-model="form.status">
				<option v-for="s in ATTENDANCE_STATUSES" :key="s">{{ s }}</option>
			</DeskSelect>
		</DeskField>
		<DeskField label="Overtime hours" hint="Applies to all rows.">
			<DeskInput
				v-model.number="form.overtime_hours"
				type="number"
				min="0"
				:disabled="form.status === 'Absent'"
			/>
		</DeskField>
		<div class="md:col-span-3">
			<DeskField label="Comments" hint="Applies to all rows.">
				<DeskInput v-model="form.comments" />
			</DeskField>
		</div>
	</DeskSection>
</template>
