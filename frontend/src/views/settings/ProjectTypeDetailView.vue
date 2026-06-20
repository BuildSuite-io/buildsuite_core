<script setup>
// Project Type Settings — detail / edit. Session 39 (exploratory).
//
// Admin/BSA gated. The `name` field is the join key onto project.type and is
// shown read-only in edit mode (renaming would break existing project records'
// type → settings lookup; a full rename would need a server-side migration
// step in production).

import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { PROJECT_TYPE_TEMPLATES } from "@/data/projectTypeTemplates";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const props = defineProps({ id: { type: String, required: true } });

const router = useRouter();
const store = useDataStore();
const confirmDialog = useConfirm();

const record = computed(() => store.projectTypeById(props.id));

const editing = ref(false);
const form = ref({});
const saving = ref(false);

function startEdit() {
	if (!record.value) return;
	form.value = JSON.parse(JSON.stringify(record.value));
	editing.value = true;
}
function cancelEdit() {
	form.value = JSON.parse(JSON.stringify(record.value));
	editing.value = false;
}
function saveEdit() {
	if (!store.isAdmin || !record.value) return;
	saving.value = true;
	store.updateProjectType(record.value.id, {
		workPackageLabel: form.value.workPackageLabel,
		workPackageLabelPlural: form.value.workPackageLabelPlural,
		defaultTemplate: form.value.defaultTemplate,
		enabled: form.value.enabled,
		sort_order: Number(form.value.sort_order) || 0,
	});
	saving.value = false;
	editing.value = false;
}
function onPrimary() {
	editing.value ? saveEdit() : startEdit();
}

async function onDelete() {
	if (!record.value) return;
	const count = store.projects.filter((p) => p.type === record.value.name).length;
	const message =
		count > 0
			? `${count} project${count === 1 ? "" : "s"} reference "${
					record.value.name
			  }". Deleting this record will leave them without configured settings (they still work — the name resolver falls back to site defaults). Continue?`
			: `Delete Project Type "${record.value.name}"? This is reversible — re-add via + New.`;
	const ok = await confirmDialog({
		title: "Delete Project Type",
		message,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	store.deleteProjectType(record.value.id);
	router.push("/settings/project-types");
}

const templateOptions = computed(() => Object.keys(PROJECT_TYPE_TEMPLATES));
const templatePreview = computed(() => {
	const key = (editing.value ? form.value.defaultTemplate : record.value?.defaultTemplate) || "";
	return PROJECT_TYPE_TEMPLATES[key] || null;
});

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Project Types", to: "/settings/project-types" },
	{ label: record.value?.name || "Project Type" },
]);

const projectsUsingThis = computed(() =>
	record.value ? store.projects.filter((p) => p.type === record.value.name) : []
);

onMounted(() => {
	if (!store.isAdmin) router.replace("/settings");
});
</script>

<template>
	<DeskPage
		v-if="record"
		:title="record.name"
		:subtitle="`Project Type Settings · ${record.id}`"
		:breadcrumbs="breadcrumbs"
		:status="record.enabled ? 'Active' : 'On Hold'"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					v-if="store.isAdmin"
					:save-label="editing ? (saving ? 'Saving…' : 'Save') : 'Edit'"
					:show-cancel="editing"
					:saving="saving"
					cancel-label="Cancel"
					@save="onPrimary"
					@cancel="cancelEdit"
				>
					<template #left>
						<span class="text-[11px] text-ink-500">
							{{ projectsUsingThis.length }} project{{
								projectsUsingThis.length === 1 ? "" : "s"
							}}
							use this type.
						</span>
					</template>
					<template #menu>
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-danger-200 text-danger-700 hover:bg-danger-50"
							style="border-radius: 6px"
							@click="onDelete"
						>
							Delete
						</button>
					</template>
				</DeskActionBar>
				<div
					v-else
					class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700"
				>
					Read-only. Editing requires Admin or BuildSuite Administrator role.
				</div>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Basic">
					<DeskField label="Project Type name" hint="Read-only after create.">
						<div class="text-sm text-ink-900 py-1">{{ record.name }}</div>
					</DeskField>
					<DeskField
						label="Sort order"
						hint="Controls the order this type appears in the new-project type dropdown."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1 tabular-nums">
							{{ record.sort_order || "—" }}
						</div>
						<DeskInput v-else v-model="form.sort_order" type="number" />
					</DeskField>
					<DeskField
						label="Enabled"
						hint="Disabled types are hidden from the new-project type dropdown. Existing projects keep their type and settings."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{ record.enabled ? "Enabled" : "Disabled" }}
						</div>
						<label v-else class="flex items-center gap-2 py-1 text-sm cursor-pointer">
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
					<DeskField
						label="Singular"
						hint='Vocabulary override for projects of this type. e.g. "Block", "Tower", "Villa Type", "Chainage Segment", "Package". Leave empty to inherit the default.'
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{
								record.workPackageLabel || '— inherits default ("Work Package") —'
							}}
						</div>
						<DeskInput
							v-else
							v-model="form.workPackageLabel"
							placeholder="Work Package"
						/>
					</DeskField>
					<DeskField
						label="Plural"
						hint="Used in sidebar entries, page titles and list subtitles."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{
								record.workPackageLabelPlural ||
								'— inherits default ("Work Packages") —'
							}}
						</div>
						<DeskInput
							v-else
							v-model="form.workPackageLabelPlural"
							placeholder="Work Packages"
						/>
					</DeskField>
				</DeskSection>

				<DeskSection title="Default template">
					<DeskField
						label="Template"
						hint="Seeds default stages, work packages and tasks on new projects of this type."
					>
						<div v-if="!editing" class="py-1">
							<span
								v-if="record.defaultTemplate"
								class="text-sm px-2 py-0.5 bg-ink-100 text-ink-700"
								style="border-radius: 9999px"
								>{{ record.defaultTemplate }}</span
							>
							<span v-else class="text-sm text-ink-400 italic"
								>No template — projects of this type are created empty.</span
							>
						</div>
						<DeskSelect v-else v-model="form.defaultTemplate">
							<option value="">— No template —</option>
							<option v-for="t in templateOptions" :key="t">{{ t }}</option>
						</DeskSelect>
					</DeskField>

					<DeskField label="Template preview" v-if="templatePreview">
						<div
							class="px-3 py-2 bg-ink-50 border border-ink-200 text-[11px] text-ink-700 space-y-1"
							style="border-radius: 6px"
						>
							<div>
								<span class="font-medium text-ink-900">{{
									(templatePreview.defaultStages || []).length
								}}</span>
								default stages:
								<span class="text-ink-600">{{
									(templatePreview.defaultStages || [])
										.map((s) => s.stageName)
										.join(" → ")
								}}</span>
							</div>
							<div>
								<span class="font-medium text-ink-900">{{
									(templatePreview.defaultWorkPackages || []).length
								}}</span>
								default work packages:
								<span class="text-ink-600">{{
									(templatePreview.defaultWorkPackages || [])
										.map((w) => w.name)
										.join(" · ")
								}}</span>
							</div>
							<div>
								<span class="font-medium text-ink-900">{{
									(templatePreview.defaultTasks || []).length
								}}</span>
								default tasks across those work packages.
							</div>
						</div>
					</DeskField>
				</DeskSection>

				<DeskSection v-if="projectsUsingThis.length" title="Projects using this type">
					<DeskField
						:label="`${projectsUsingThis.length} project${
							projectsUsingThis.length === 1 ? '' : 's'
						}`"
					>
						<ul class="text-sm py-1 space-y-1">
							<li v-for="p in projectsUsingThis.slice(0, 10)" :key="p.id">
								<RouterLink :to="`/projects/${p.id}`" class="desk-link">{{
									p.name
								}}</RouterLink>
								<span class="text-ink-500 text-xs"> · {{ p.code }}</span>
							</li>
							<li
								v-if="projectsUsingThis.length > 10"
								class="text-xs text-ink-500 italic"
							>
								…and {{ projectsUsingThis.length - 10 }} more.
							</li>
						</ul>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>

	<DeskPage v-else title="Project Type not found" :breadcrumbs="breadcrumbs">
		<div class="border border-ink-200 px-4 py-8 text-center" style="border-radius: 6px">
			<div class="text-sm text-ink-700 mb-2">
				No record with id <span class="font-mono">{{ props.id }}</span
				>.
			</div>
			<RouterLink to="/settings/project-types" class="desk-link"
				>← Back to Project Types</RouterLink
			>
		</div>
	</DeskPage>
</template>
