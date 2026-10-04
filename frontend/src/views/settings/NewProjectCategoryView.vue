<script setup>
// Project Categories — create form (backend-backed via the Project Category
// doctype). Admin / BSA only.

import { reactive, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import { __ } from "@/utils/translate";
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
	if (!form.name.trim()) e.name = __("Name is required");
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
		showToast(parseFrappeError(err).summary ?? __("Failed to create category"), "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.back();
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: __("Project Categories"), to: "/settings/project-categories" },
	{ label: __("New") },
];

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) router.replace("/settings");
});
</script>

<template>
	<DeskPage :title="__('New Project Category')" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? __('Creating…') : __('Create category')"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection :title="__('Basic')">
					<DeskField
						:label="__('Category name')"
						required
						:error="errors.name"
						:hint="__('e.g. Commercial, Residential, Infrastructure, EPC, Interiors.')"
					>
						<DeskInput v-model="form.name" :placeholder="__('e.g. Industrial')" />
					</DeskField>
					<DeskField :label="__('Sort order')" :hint="__('Position in the new-project dropdown.')">
						<DeskInput v-model="form.sortOrder" type="number" :placeholder="__('auto')" />
					</DeskField>
					<DeskField :label="__('Enabled')">
						<label class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input type="checkbox" v-model="form.enabled" class="accent-brand-600" />
							<span>{{
								form.enabled
									? __("Enabled — appears in the new-project dropdown")
									: __("Disabled — hidden from the new-project dropdown")
							}}</span>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection :title="__('Work Package label')">
					<DeskField
						:label="__('Singular')"
						:hint="__('e.g. &quot;Block&quot;, &quot;Tower&quot;, &quot;Package&quot;. Defaults to &quot;Work Package&quot;.')"
					>
						<DeskInput v-model="form.workPackageLabel" :placeholder="__('Work Package')" />
					</DeskField>
					<DeskField :label="__('Plural')">
						<DeskInput
							v-model="form.workPackageLabelPlural"
							:placeholder="__('Work Packages')"
						/>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
