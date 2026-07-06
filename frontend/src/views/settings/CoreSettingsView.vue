<script setup>
// BuildSuite Core Settings — Single DocType. Org-wide BuildSuite-product
// toggles. Session 34, M1 scope. Admin or BSA gated.
//
// Production shape: Frappe Single DocType (one record per site). Prototype
// represents it as store.coreSettings (flat object). Edits flow through
// store.updateCoreSettings(patch).

import { ref, computed, watch, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { getCoreSettings, setProjectNaming } from "@/data/coreSettingsApi";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const router = useRouter();
const store = useDataStore();

const editing = ref(false);
const form = ref({});
const saving = ref(false);

// Project naming is server-persisted (BuildSuite Core Settings Single), unlike the
// other fields on this screen. Stored resolved value: "Project ID" or a naming
// series string. In the UI it's a mode select ("Project ID" | "Name Series") plus a
// series picker shown only in Name Series mode.
const PROJECT_ID_MODE = "Project ID";
const NAME_SERIES_MODE = "Name Series";
const projectNaming = ref(PROJECT_ID_MODE);
const projectNamingOptions = ref([PROJECT_ID_MODE]);

// The naming series available on the Project doctype (everything but "Project ID").
const seriesOptions = computed(() =>
	projectNamingOptions.value.filter((o) => o !== PROJECT_ID_MODE),
);
// Human-readable summary of the current setting for the read-only view.
const projectNamingLabel = computed(() =>
	projectNaming.value === PROJECT_ID_MODE
		? "Project ID"
		: `Name Series — ${projectNaming.value}`,
);

onMounted(async () => {
	try {
		const res = await getCoreSettings();
		projectNaming.value = res.project_naming || PROJECT_ID_MODE;
		projectNamingOptions.value = res.project_naming_options || [PROJECT_ID_MODE];
	} catch {
		/* leave defaults; non-admins can't read it */
	}
});

watch(
	() => store.coreSettings,
	(s) => {
		if (s) form.value = JSON.parse(JSON.stringify(s));
	},
	{ immediate: true, deep: true },
);

function startEdit() {
	const isSeries = projectNaming.value !== PROJECT_ID_MODE;
	form.value = {
		...JSON.parse(JSON.stringify(store.coreSettings)),
		naming_mode: isSeries ? NAME_SERIES_MODE : PROJECT_ID_MODE,
		naming_series: isSeries ? projectNaming.value : seriesOptions.value[0] || "",
	};
	editing.value = true;
}
function cancelEdit() {
	form.value = JSON.parse(JSON.stringify(store.coreSettings));
	editing.value = false;
}
async function saveEdit() {
	if (!store.isAdmin) return;
	saving.value = true;
	try {
		store.updateCoreSettings({ ...form.value });
		const resolved =
			form.value.naming_mode === NAME_SERIES_MODE
				? form.value.naming_series || seriesOptions.value[0]
				: PROJECT_ID_MODE;
		if (resolved && resolved !== projectNaming.value) {
			await setProjectNaming(resolved);
			projectNaming.value = resolved;
		}
		editing.value = false;
	} catch (err) {
		showToast(err.message || "Failed to save settings", "error");
	} finally {
		saving.value = false;
	}
}
function onPrimary() {
	editing.value ? saveEdit() : startEdit();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "BuildSuite Core Settings" },
];

const PROJECT_TYPES = ["Commercial", "Residential", "Infrastructure", "Industrial", "Renovation"];
</script>

<template>
	<DeskPage
		title="BuildSuite Core Settings"
		subtitle="Org-wide BuildSuite toggles"
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
				<DeskSection title="Multi-company">
					<DeskField
						label="Enable company segregation"
						hint="Master switch for multi-company segregation. Off → single-company UX (switcher and column auto-hide). On → multi-company users see segregation controls."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{
								store.coreSettings.enable_company_segregation
									? "Enabled"
									: "Disabled"
							}}
						</div>
						<label v-else class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input
								type="checkbox"
								v-model="form.enable_company_segregation"
								class="accent-brand-600"
							/>
							<span>{{
								form.enable_company_segregation ? "Enabled" : "Disabled"
							}}</span>
						</label>
					</DeskField>
					<DeskField
						label="Default company"
						hint="The company pre-selected on Project create when the user doesn't pick one explicitly. Must exist in the Companies fixture."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{
								store.companyById(store.coreSettings.default_company)?.name ||
								store.coreSettings.default_company
							}}
						</div>
						<DeskSelect v-else v-model="form.default_company">
							<option v-for="c in store.companies" :key="c.id" :value="c.id">
								{{ c.name }}
							</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>

				<DeskSection title="Project defaults">
					<DeskField
						label="Default project type"
						hint="Pre-fills the Project type field on new projects."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{ store.coreSettings.default_project_type }}
						</div>
						<DeskSelect v-else v-model="form.default_project_type">
							<option v-for="t in PROJECT_TYPES" :key="t">{{ t }}</option>
						</DeskSelect>
					</DeskField>
					<DeskField
						label="Project naming"
						hint="How a new project's record ID is generated. 'Project ID' uses the entered Project ID as the record name; 'Name Series' uses the selected ERPNext naming series."
					>
						<div v-if="!editing" class="text-sm text-ink-900 py-1">
							{{ projectNamingLabel }}
						</div>
						<DeskSelect v-else v-model="form.naming_mode">
							<option value="Project ID">Project ID</option>
							<option value="Name Series">Name Series</option>
						</DeskSelect>
					</DeskField>
					<DeskField
						v-if="editing && form.naming_mode === 'Name Series'"
						label="Name series"
						hint="The ERPNext naming series used to generate the project's record ID."
					>
						<DeskSelect v-model="form.naming_series">
							<option v-for="opt in seriesOptions" :key="opt" :value="opt">
								{{ opt }}
							</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
