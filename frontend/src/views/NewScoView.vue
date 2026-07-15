<script setup>
// Raise a Scope Change Order — Desk-styled form. Raising creates the SCO in
// "Pending Approval"; a PM / Director then approves it, after which a BOQ revision
// can be raised from the approved change order. Pre-fills the project from
// ?project=… (the Project detail's "+ Raise SCO" passes it).

import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { createDataAdapter } from "@/data/adapters";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const route = useRoute();
const router = useRouter();
const adapter = createDataAdapter(useDataStore());

const TYPES = [
	"Design Change",
	"Client Request",
	"Statutory",
	"Site Condition",
	"Rework",
	"Other",
];

const form = reactive({
	project: route.query.project || "",
	type: "Design Change",
	title: "",
	impact: 0,
	recoverable: "1",
	reason: "",
});
const { errors, applyServerErrors, setErrors } = useFormErrors({
	project: "project",
	title: "title",
});
const saving = ref(false);

function validate() {
	const e = {};
	if (!form.project) e.project = "Pick a project.";
	if (!form.title.trim()) e.title = "Title is required.";
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
		const res = await adapter.create("Scope Change Order", {
			project: form.project,
			type: form.type,
			title: form.title.trim(),
			impact: Number(form.impact) || 0,
			recoverable: form.recoverable === "1" ? 1 : 0,
			reason: form.reason,
		});
		router.push(`/sco/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to raise scope change order", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Scope Change Orders", to: "/sco" },
	{ label: "Raise" },
];
</script>

<template>
	<DeskPage
		title="Raise Scope Change Order"
		subtitle="Raising submits it for PM / Director approval"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Raising…' : 'Raise SCO'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Change order" :cols="2">
				<DeskField label="Project" required :error="errors.project">
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						placeholder="Pick a project…"
					/>
				</DeskField>
				<DeskField label="Type">
					<DeskSelect v-model="form.type">
						<option v-for="t in TYPES" :key="t">{{ t }}</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Title" required :error="errors.title" class="md:col-span-2">
					<DeskInput
						v-model="form.title"
						placeholder="e.g. Foundation depth revision — soil report"
					/>
				</DeskField>
				<DeskField
					label="Cost impact (₹)"
					hint="Positive = added cost to the project; negative = a saving."
				>
					<DeskInput v-model.number="form.impact" type="number" step="1000" />
				</DeskField>
				<DeskField label="Cost recovery">
					<DeskSelect v-model="form.recoverable">
						<option value="1">Recoverable from client</option>
						<option value="0">Internal — absorbed by us</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Reason / justification" class="md:col-span-2">
					<DeskTextarea
						v-model="form.reason"
						:rows="4"
						placeholder="Why is this change needed?"
					/>
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
