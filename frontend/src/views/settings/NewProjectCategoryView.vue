<script setup>
// Project Categories — create form (backend-backed via the Project Category
// doctype). Admin / BSA only.

import { reactive, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";

const router = useRouter();
const store = useDataStore();
const adapter = createDataAdapter(store);

const form = reactive({
	name: "",
	workPackageLabel: "",
	workPackageLabelPlural: "",
	enabled: true,
	sortOrder: "",
});
const errors = ref({});
const saving = ref(false);

function validate() {
	const e = {};
	if (!form.name.trim()) e.name = "Name is required";
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function save() {
	if (!validate() || saving.value) return;
	saving.value = true;
	try {
		const res = await adapter.create("Project Category", {
			category_name: form.name.trim(),
			work_package_label: form.workPackageLabel.trim() || "Work Package",
			work_package_label_plural: form.workPackageLabelPlural.trim() || "Work Packages",
			enabled: form.enabled ? 1 : 0,
			sort_order: Number(form.sortOrder) || 0,
		});
		router.push(`/settings/project-categories/${res.name}`);
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to create category", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.back();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Project Categories", to: "/settings/project-categories" },
	{ label: "New" },
];

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) router.replace("/settings");
});
</script>

<template>
	<DeskPage title="New Project Category" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create category'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Basic">
					<DeskField
						label="Category name"
						required
						:error="errors.name"
						hint="e.g. Commercial, Residential, Infrastructure, EPC, Interiors."
					>
						<DeskInput v-model="form.name" placeholder="e.g. Industrial" />
					</DeskField>
					<DeskField label="Sort order" hint="Position in the new-project dropdown.">
						<DeskInput v-model="form.sortOrder" type="number" placeholder="auto" />
					</DeskField>
					<DeskField label="Enabled">
						<label class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input type="checkbox" v-model="form.enabled" class="accent-brand-600" />
							<span>{{
								form.enabled
									? "Enabled — appears in the new-project dropdown"
									: "Disabled — hidden from the new-project dropdown"
							}}</span>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection title="Work Package label">
					<DeskField
						label="Singular"
						hint='e.g. "Block", "Tower", "Package". Defaults to "Work Package".'
					>
						<DeskInput v-model="form.workPackageLabel" placeholder="Work Package" />
					</DeskField>
					<DeskField label="Plural">
						<DeskInput
							v-model="form.workPackageLabelPlural"
							placeholder="Work Packages"
						/>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
