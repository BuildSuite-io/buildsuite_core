<script setup>
// Site Execution Settings — Single DocType. Module-operational defaults for
// the Site Execution workspace (Projects, WPs, Tasks, TPEs, Stage Planning).
// Session 34, M1 scope. Admin or BSA gated.

import { ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const store = useDataStore();

const editing = ref(false);
const form = ref({});
const saving = ref(false);

watch(
	() => store.siteExecutionSettings,
	(s) => {
		if (s) form.value = JSON.parse(JSON.stringify(s));
	},
	{ immediate: true, deep: true }
);

function startEdit() {
	form.value = JSON.parse(JSON.stringify(store.siteExecutionSettings));
	editing.value = true;
}
function cancelEdit() {
	form.value = JSON.parse(JSON.stringify(store.siteExecutionSettings));
	editing.value = false;
}
function saveEdit() {
	if (!store.isAdmin) return;
	saving.value = true;
	store.updateSiteExecutionSettings({ ...form.value });
	saving.value = false;
	editing.value = false;
}
function onPrimary() {
	editing.value ? saveEdit() : startEdit();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Site Execution Settings" },
];

const TASK_TYPES = ["Activity", "Milestone", "Inspection"];
</script>

<template>
	<DeskPage
		title="Site Execution Settings"
		subtitle="Module operational defaults"
		:breadcrumbs="breadcrumbs"
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
				/>
				<div
					v-else
					class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700"
				>
					Read-only. Editing requires Admin or BuildSuite Administrator role.
				</div>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Task defaults">
					<DeskField
						label="Default task type"
						hint="Pre-fills task type on new tasks. Choose Activity, Milestone or Inspection."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{ store.siteExecutionSettings.default_task_type }}
						</div>
						<DeskSelect v-else v-model="form.default_task_type">
							<option v-for="t in TASK_TYPES" :key="t">{{ t }}</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>

				<DeskSection title="Company propagation">
					<DeskField
						label="Auto-propagate company"
						hint="When ON, child records (Work Package, Task, Progress Entry, Stage Planning, Attachments) inherit company from their parent project on create. When OFF, company is left blank and must be set explicitly."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{ store.siteExecutionSettings.auto_propagate_company ? "On" : "Off" }}
						</div>
						<label v-else class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input
								type="checkbox"
								v-model="form.auto_propagate_company"
								class="accent-brand-600"
							/>
							<span>{{ form.auto_propagate_company ? "On" : "Off" }}</span>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection title="Task Progress Entry">
					<DeskField
						label="Require attachment"
						hint="When ON, filing a progress entry without at least one attachment is rejected. Enforces site photo discipline."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{
								store.siteExecutionSettings.tpe_attachment_required
									? "Required"
									: "Optional"
							}}
						</div>
						<label v-else class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input
								type="checkbox"
								v-model="form.tpe_attachment_required"
								class="accent-brand-600"
							/>
							<span>{{
								form.tpe_attachment_required ? "Required" : "Optional"
							}}</span>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection title="Safety">
					<DeskField
						label="Cascade-delete confirmation"
						hint="When ON, deleting a Project, Work Package or Task shows a confirm dialog listing the cascaded child records. Off skips the prompt."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{
								store.siteExecutionSettings.cascade_delete_confirmation
									? "On"
									: "Off"
							}}
						</div>
						<label v-else class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input
								type="checkbox"
								v-model="form.cascade_delete_confirmation"
								class="accent-brand-600"
							/>
							<span>{{ form.cascade_delete_confirmation ? "On" : "Off" }}</span>
						</label>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
