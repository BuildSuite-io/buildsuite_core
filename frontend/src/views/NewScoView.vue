<script setup>
// Raise a Scope Change Order (M7). Saved straight into Pending Approval (raise =
// submit for approval); approval happens on the detail page. raised_by / raised_date
// / status / company are stamped server-side (controller before_insert + fetch_from).

import { computed, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
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

// Select options from the DocType meta (single source of truth).
const { selectOptions } = useDoctypeMeta("Scope Change Order");
const typeOptions = computed(() => selectOptions("sco_type"));
const recoveryOptions = computed(() => selectOptions("cost_recovery"));

const form = reactive({
	project: route.query.projectId || "",
	title: "",
	sco_type: "Design Change",
	cost_impact: 0,
	cost_recovery: "Internal",
	reason__justification: "",
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

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const res = await adapter.create("Scope Change Order", {
			project: form.project,
			title: form.title.trim(),
			sco_type: form.sco_type,
			cost_impact: Number(form.cost_impact) || 0,
			cost_recovery: form.cost_recovery,
			reason__justification: form.reason__justification,
		});
		router.push(`/sco/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to raise scope change", "error");
	} finally {
		saving.value = false;
	}
}

function onCancel() {
	router.back();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Scope Change", to: "/sco" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="Raise Scope Change Order" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Raising…' : 'Raise SCO'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Scope change" :cols="2">
				<DeskField label="Project" required :error="errors.project">
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						placeholder="— Select project —"
					/>
				</DeskField>
				<DeskField label="Type">
					<DeskSelect v-model="form.sco_type">
						<option v-for="t in typeOptions" :key="t">{{ t }}</option>
					</DeskSelect>
				</DeskField>
				<div class="md:col-span-2">
					<DeskField label="Title" required :error="errors.title">
						<DeskInput
							v-model="form.title"
							placeholder="e.g. Foundation depth revision — soil report"
						/>
					</DeskField>
				</div>
				<DeskField
					label="Cost impact (₹)"
					hint="Positive = added cost to the project; negative = saving."
				>
					<DeskInput v-model.number="form.cost_impact" type="number" />
				</DeskField>
				<DeskField label="Cost recovery" hint="Who bears the cost of this scope change.">
					<DeskSelect v-model="form.cost_recovery">
						<option v-for="r in recoveryOptions" :key="r">{{ r }}</option>
					</DeskSelect>
				</DeskField>
				<div class="md:col-span-2">
					<DeskField label="Reason / justification">
						<DeskTextarea
							v-model="form.reason__justification"
							:rows="4"
							placeholder="Why is this scope change needed?"
						/>
					</DeskField>
				</div>
			</DeskSection>
			<div class="text-xs text-ink-500 italic">
				Raising submits the SCO for approval. A PM / Director then approves or rejects it.
			</div>
		</DeskForm>
	</DeskPage>
</template>
