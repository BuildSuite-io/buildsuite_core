<script setup>
// The "Crew" field block, shared by the New and Detail screens.

import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";

defineProps({
	form: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});

const { workerOptions } = useFieldEmployeeOptions();
</script>

<template>
	<DeskSection title="Crew" :cols="2">
		<DeskField label="Crew name" required :error="errors.crew_name">
			<DeskInput v-model="form.crew_name" placeholder="e.g. Block A Structural Gang" />
		</DeskField>
		<DeskField label="Crew leader">
			<DeskSearchableSelect
				v-model="form.crew_leader"
				:options="workerOptions"
				placeholder="Pick a worker…"
				search-placeholder="Search workers…"
				allow-clear
			/>
		</DeskField>

		<DeskField label="Trade">
			<DeskLinkPicker
				v-model="form.trade"
				doctype="Labour Trade"
				label-field="trade"
				:search-fields="['trade', 'name']"
				placeholder="Select trade"
			/>
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
</template>
