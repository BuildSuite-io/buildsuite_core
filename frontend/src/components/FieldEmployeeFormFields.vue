<script setup>
// The "Worker" and "Wages" field blocks, shared by the New and Detail screens.

import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useContractorOptions } from "@/composables/useContractorOptions";

defineProps({
	form: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});

const { contractorOptions } = useContractorOptions();
</script>

<template>
	<DeskSection title="Worker" :cols="3">
		<DeskField label="First name" required :error="errors.first_name">
			<DeskInput v-model="form.first_name" />
		</DeskField>
		<DeskField label="Last name">
			<DeskInput v-model="form.last_name" />
		</DeskField>
		<DeskField label="Gender" required :error="errors.gender">
			<DeskLinkPicker
				v-model="form.gender"
				doctype="Gender"
				placeholder="Select gender"
				:error="errors.gender"
			/>
		</DeskField>

		<DeskField label="Date of birth" required :error="errors.date_of_birth">
			<DeskInput v-model="form.date_of_birth" type="date" />
		</DeskField>
		<DeskField label="Date of joining" required :error="errors.date_of_joining">
			<DeskInput v-model="form.date_of_joining" type="date" />
		</DeskField>
		<DeskField label="Status">
			<!-- ERPNext also has Suspended and Left, but Left demands a
			     relieving date this form doesn't collect, so it can never save. -->
			<DeskSelect v-model="form.status">
				<option>Active</option>
				<option>Inactive</option>
			</DeskSelect>
		</DeskField>

		<DeskField label="Trade">
			<DeskLinkPicker
				v-model="form.custom_trade"
				doctype="Labour Trade"
				label-field="trade"
				:search-fields="['trade', 'name']"
				placeholder="Select trade"
			/>
		</DeskField>
		<DeskField
			label="Contractor"
			hint="Labour contractor, if engaged through one. Leave blank if engaged directly."
		>
			<!-- Clearable on purpose: blank is a meaningful value here (engaged
			     directly), and DeskLinkPicker has no way to get back to blank. -->
			<DeskSearchableSelect
				v-model="form.custom_contractor"
				:options="contractorOptions"
				placeholder="— Engaged directly —"
				search-placeholder="Search suppliers…"
				allow-clear
			/>
		</DeskField>
		<DeskField label="Phone">
			<DeskInput v-model="form.cell_number" />
		</DeskField>
		<DeskField label="Company" required :error="errors.company">
			<DeskLinkPicker
				v-model="form.company"
				doctype="Company"
				placeholder="Select company"
				:error="errors.company"
			/>
		</DeskField>
	</DeskSection>

	<DeskSection title="Wages" :cols="2">
		<DeskField
			label="Daily wage"
			required
			hint="Daily wage — read at attendance posting."
			:error="errors.custom_wage"
		>
			<DeskInput v-model.number="form.custom_wage" type="number" min="0" />
		</DeskField>
		<DeskField label="Overtime wage" hint="Overtime wage per hour.">
			<DeskInput v-model.number="form.custom_wage_for_overtime" type="number" min="0" />
		</DeskField>
	</DeskSection>
</template>
