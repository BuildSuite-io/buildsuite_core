<script setup>
// The "Crew" field block, shared by the New and Detail screens.

import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { __ } from "@/utils/translate";

defineProps({
	form: { type: Object, required: true },
	errors: { type: Object, default: () => ({}) },
});

const { workerOptions } = useFieldEmployeeOptions();
</script>

<template>
	<DeskSection :title="__('Crew')" :cols="2">
		<DeskField :label="__('Crew name')" required :error="errors.crew_name">
			<DeskInput v-model="form.crew_name" :placeholder="__('e.g. Block A Structural Gang')" />
		</DeskField>
		<DeskField :label="__('Crew leader')">
			<DeskSearchableSelect
				v-model="form.crew_leader"
				:options="workerOptions"
				:placeholder="__('Pick a worker…')"
				:search-placeholder="__('Search workers…')"
				allow-clear
			/>
		</DeskField>

		<DeskField :label="__('Trade')">
			<DeskLinkPicker
				v-model="form.trade"
				doctype="Labour Trade"
				label-field="trade"
				:search-fields="['trade', 'name']"
				:placeholder="__('Select trade')"
			/>
		</DeskField>
		<DeskField :label="__('Company')" required :error="errors.company">
			<DeskLinkPicker
				v-model="form.company"
				doctype="Company"
				:placeholder="__('Select company')"
				:error="errors.company"
			/>
		</DeskField>
	</DeskSection>
</template>
