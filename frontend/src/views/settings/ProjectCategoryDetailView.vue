<script setup>
// Project Categories — edit / delete (backend-backed via the Project Category
// doctype). Admin / BSA only.

import { reactive, ref, computed, watch, onMounted } from "vue";
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

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const store = useDataStore();
const adapter = createDataAdapter(store);

const form = reactive({
	workPackageLabel: "",
	workPackageLabelPlural: "",
	enabled: true,
	sortOrder: 0,
});
const saving = ref(false);
const loaded = ref(false);

const resource = adapter.read("Project Category", props.id, {
	fields: [
		"name",
		"category_name",
		"work_package_label",
		"work_package_label_plural",
		"enabled",
		"sort_order",
	],
	transform: (rows) => rows,
});

function firstRow(res) {
	if (res?.doc) return res.doc;
	const raw = res?.data;
	if (Array.isArray(raw)) return raw[0] || null;
	if (Array.isArray(raw?.value)) return raw.value[0] || null;
	return raw || null;
}
const record = computed(() => firstRow(resource));

watch(
	record,
	(r) => {
		if (!r || loaded.value) return;
		form.workPackageLabel = r.work_package_label || "";
		form.workPackageLabelPlural = r.work_package_label_plural || "";
		form.enabled = !!r.enabled;
		form.sortOrder = r.sort_order || 0;
		loaded.value = true;
	},
	{ immediate: true },
);

async function save() {
	if (saving.value) return;
	saving.value = true;
	try {
		await adapter.update("Project Category", props.id, {
			work_package_label: form.workPackageLabel.trim() || "Work Package",
			work_package_label_plural: form.workPackageLabelPlural.trim() || "Work Packages",
			enabled: form.enabled ? 1 : 0,
			sort_order: Number(form.sortOrder) || 0,
		});
		showToast("Category saved");
		router.push("/settings/project-categories");
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to save category", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.push("/settings/project-categories");
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Project Categories", to: "/settings/project-categories" },
	{ label: props.id },
]);

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) router.replace("/settings");
});
</script>

<template>
	<DeskPage :title="props.id" subtitle="Project category" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Saving…' : 'Save changes'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Basic">
					<DeskField
						label="Category name"
						hint="The name is the key and can't be changed."
					>
						<DeskInput :model-value="props.id" disabled />
					</DeskField>
					<DeskField label="Sort order">
						<DeskInput v-model="form.sortOrder" type="number" />
					</DeskField>
					<DeskField label="Enabled">
						<label class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input
								type="checkbox"
								v-model="form.enabled"
								class="accent-brand-600"
							/>
							<span>{{ form.enabled ? "Enabled" : "Disabled" }}</span>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection title="Work Package label">
					<DeskField label="Singular">
						<DeskInput v-model="form.workPackageLabel" placeholder="Work Package" />
					</DeskField>
					<DeskField label="Plural">
						<DeskInput
							v-model="form.workPackageLabelPlural"
							placeholder="Work Packages"
						/>
					</DeskField>
				</DeskSection>

				<DeskSection title="Default template" :cols="1">
					<p class="text-sm text-ink-500 -mt-1">
						The Work Packages, Stages and Tasks a project inherits when it's created
						under this category. Tasks are assigned to their Stage, so imported stage
						plans arrive with their tasks.
					</p>
					<div>
						<button
							class="text-sm text-brand-600 hover:underline"
							@click="
								router.push(`/settings/project-categories/${props.id}/template`)
							"
						>
							Edit default template →
						</button>
					</div>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
