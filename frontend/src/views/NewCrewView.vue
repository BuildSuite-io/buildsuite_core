<script setup>
// New Crew form. A crew is a standing gang — no project link, so the same gang
// can work any site. Member role and daily rate fill from the worker on save.

import { reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { saveCrew } from "@/data/crewApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import CrewFormFields from "@/components/CrewFormFields.vue";
import CrewMembersTable from "@/components/CrewMembersTable.vue";
import { validateCrew } from "@/utils/workforceForms";

const router = useRouter();
const activeCompany = useActiveCompany();

const form = reactive({
	crew_name: "",
	crew_leader: "",
	trade: "",
	company: activeCompany.value || "",
	members: [],
});

// The default company arrives from an async fetch. Apply it only while the field
// is still untouched, so it never overwrites a company the user already picked.
watch(activeCompany, (c) => {
	if (c && !form.company) form.company = c;
});

const { errors, applyServerErrors, setErrors } = useFormErrors({
	crew_name: "crew_name",
	company: "company",
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
		const res = await saveCrew({ ...form });
		showToast("Crew created");
		router.push(`/crews/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create crew", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Crews", to: "/crews" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="New Crew" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create crew'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<CrewFormFields :form="form" :errors="errors" />

			<CrewMembersTable
				:rows="form.members"
				editable
				@add="form.members.push({ field_employee: '', role_in_crew: '' })"
				@remove="(i) => form.members.splice(i, 1)"
			/>
		</DeskForm>
	</DeskPage>
</template>
