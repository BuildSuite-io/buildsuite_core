<script setup>
// New Work Package — Desk-styled. Accepts `?projectId=` on the route query to
// pre-fill the project (the entry point from Project Detail's Work Packages
// tab). When no projectId is supplied, the first project is selected as a
// default.

import { reactive, ref, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { createDataAdapter } from "@/data/adapters";

const router = useRouter();
const route = useRoute();
const store = useDataStore();
const { canCreate } = usePermissions();
const adapter = createDataAdapter(store);

const form = reactive({
	projectId: route.query.projectId || "",
	code: "",
	name: "",
	description: "",
	status: "Planned",
	budget: "",
	startDate: "",
	endDate: "",
});
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
	project: "projectId",
	work_package_name: "name",
	end_date: "endDate",
	start_date: "startDate",
});
const saving = ref(false);

const lockedProject = computed(() => !!route.query.projectId);
const parentProject = computed(() => store.projectById(form.projectId) || null);

function validate() {
	const e = {};
	if (!form.name.trim()) e.name = "Work package name is required";
	if (!form.projectId) e.projectId = "Project is required";
	if (form.endDate && form.startDate && form.endDate < form.startDate) {
		e.endDate = "End must be after start";
	}
	setErrors(e);
	return Object.keys(e).length === 0;
}

async function save() {
	if (!validate()) return;
	saving.value = true;
	try {
		const res = await adapter.create("Work Package", {
			project: form.projectId,
			code: form.code.trim(),
			work_package_name: form.name.trim(),
			description: form.description,
			status: form.status,
			budget: Number(form.budget) || 0,
			start_date: form.startDate,
			end_date: form.endDate,
		});
		router.push(`/work-packages/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create work package", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.back();
}

const breadcrumbs = computed(() => {
	const out = [
		{ label: "BuildSuite Core", to: "/" },
		{ label: "Work Package", to: "/work-packages" },
	];
	if (parentProject.value) {
		out.push({ label: parentProject.value.name, to: `/projects/${parentProject.value.id}` });
	}
	out.push({ label: "New" });
	return out;
});

const subtitle = computed(() =>
	parentProject.value
		? `Under ${parentProject.value.name}`
		: "Cost / control boundary inside a project"
);
</script>

<template>
	<DeskPage title="New Work Package" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('workPackage')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to create a work package.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create work package'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Basic information">
					<DeskField
						label="Project"
						required
						:error="errors.projectId"
						:hint="
							lockedProject ? 'Pre-selected from where you came in — locked.' : ''
						"
					>
						<DeskLinkPicker
							v-model="form.projectId"
							doctype="Project"
							placeholder="Select project"
							label-field="project_name"
							value-field="name"
							:search-fields="['project_name', 'name', 'custom_project_id']"
							order-by="modified desc"
							:page-length="20"
							:disabled="lockedProject"
							:error="errors.projectId"
							@change="clearError('projectId')"
						/>
					</DeskField>
					<DeskField label="Work Package name" required :error="errors.name">
						<DeskInput v-model="form.name" placeholder="e.g. Foundation Works" />
					</DeskField>
					<DeskField
						label="Code"
						hint="Short identifier — auto-generated if left blank."
					>
						<DeskInput v-model="form.code" placeholder="e.g. WP-FND" />
					</DeskField>
					<DeskField label="Description">
						<DeskTextarea
							v-model="form.description"
							:rows="3"
							placeholder="What this work package covers."
						/>
					</DeskField>
				</DeskSection>

				<DeskSection title="Schedule & cost">
					<DeskField label="Start date">
						<DeskInput v-model="form.startDate" type="date" />
					</DeskField>
					<DeskField label="Expected end date" :error="errors.endDate">
						<DeskInput v-model="form.endDate" type="date" />
					</DeskField>
					<DeskField label="Budget (₹)">
						<DeskInput v-model="form.budget" type="number" placeholder="0" />
					</DeskField>
					<DeskField label="Status">
						<DeskSelect v-model="form.status">
							<option>Planned</option>
							<option>In Progress</option>
							<option>On Hold</option>
							<option>Completed</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
