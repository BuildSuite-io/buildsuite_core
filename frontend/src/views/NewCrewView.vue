<script setup>
// New Crew form. A crew is a standing gang — no project link, so the same gang
// can work any site. Member role and daily rate fill from the worker on save.

import { reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
// Custom Fields, controls and save hooks an installed app adds to this form (sdk/useExtensionFields).
import ExtensionSlot from "@/components/ExtensionSlot.vue";
import { useExtensionFields } from "@/sdk/useExtensionFields";
import { __ } from "@/utils/translate";
import { useFormErrors } from "@/composables/useFormErrors";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { saveCrew } from "@/data/crewApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import CrewFormFields from "@/components/CrewFormFields.vue";
import CrewMembersTable from "@/components/CrewMembersTable.vue";
import { validateCrew } from "@/utils/workforceForms";

const router = useRouter();
const { canCreate } = usePermissions();
const activeCompany = useActiveCompany();

const form = reactive({
	crew_name: "",
	crew_leader: "",
	trade: "",
	company: activeCompany.value || "",
	members: [],
});
const ext = useExtensionFields("Crew", form);
ext.defaults();

// The default company arrives from an async fetch. Apply it only while the field
// is still untouched, so it never overwrites a company the user already picked.
watch(activeCompany, (c) => {
	if (c && !form.company) form.company = c;
});

const { errors, applyServerErrors, setErrors } = useFormErrors({
	crew_name: "crew_name",
	company: "company",
	members: "members",
});
const saving = ref(false);

function validate() {
	const e = validateCrew(form);
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
		const res = await saveCrew(payload);
		await ext.afterSave(res, { isNew: true });
		showToast(__("Crew created"));
		router.push(`/crews/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? __("Failed to create crew"), "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Workforce"), to: "/workforce" },
	{ label: __("Crews"), to: "/crews" },
	{ label: __("New") },
];
</script>

<template>
	<DeskPage :title="__('New Crew')" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('crew')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ __("You don't have permission to create a crew.") }}
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? __('Creating…') : __('Create crew')"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>
			<ExtensionSlot :name="ext.slot('top')" :context="ext.context" />

			<CrewFormFields :form="form" :errors="errors" />

			<CrewMembersTable
				:rows="form.members"
				:error="errors.members"
				editable
				@add="form.members.push({ field_employee: '', role_in_crew: '' })"
				@remove="(i) => form.members.splice(i, 1)"
			/>
			<ExtensionSlot :name="ext.slot('bottom')" :context="ext.context" />
		</DeskForm>
	</DeskPage>
</template>
