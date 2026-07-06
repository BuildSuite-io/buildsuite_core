<script setup>
// New Persona — create a Persona and its role mapping (backend-backed via
// buildsuite_core.api.persona). Admin / BSA only.

import { reactive, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { savePersona, listAssignableRoles } from "@/data/personaApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import PersonaRolesField from "@/components/PersonaRolesField.vue";

const router = useRouter();
const store = useDataStore();

const form = reactive({
	personaName: "",
	slug: "",
	sortOrder: "",
	enabled: true,
	description: "",
	roles: [],
});
const errors = ref({});
const saving = ref(false);
const assignableRoles = ref([]);

function validate() {
	const e = {};
	if (!form.personaName.trim()) e.personaName = "Name is required";
	if (!form.roles.length) e.roles = "Add at least one role";
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function save() {
	if (!validate() || saving.value) return;
	saving.value = true;
	try {
		const res = await savePersona({
			persona_name: form.personaName.trim(),
			slug: form.slug.trim(),
			description: form.description.trim(),
			enabled: form.enabled ? 1 : 0,
			sort_order: Number(form.sortOrder) || 0,
			roles: form.roles,
		});
		showToast("Persona created");
		router.push(`/settings/personas/${encodeURIComponent(res.name)}`);
	} catch (err) {
		showToast(err.message || "Failed to create persona", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.push("/settings/personas");
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Personas", to: "/settings/personas" },
	{ label: "New" },
];

onMounted(async () => {
	if (!store.isAdmin && !store.isBSA) {
		router.replace("/settings");
		return;
	}
	try {
		assignableRoles.value = await listAssignableRoles();
	} catch {
		assignableRoles.value = [];
	}
});
</script>

<template>
	<DeskPage title="New Persona" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create persona'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Basic">
					<DeskField
						label="Persona name"
						required
						:error="errors.personaName"
						hint="The label users pick. Can't be changed later."
					>
						<DeskInput v-model="form.personaName" placeholder="e.g. Planner" />
					</DeskField>
					<DeskField
						label="Slug"
						hint="Frontend id (auto-filled from the name if left blank)."
					>
						<DeskInput v-model="form.slug" placeholder="e.g. planner" />
					</DeskField>
					<DeskField label="Sort order" hint="Position in the persona dropdown.">
						<DeskInput v-model="form.sortOrder" type="number" placeholder="auto" />
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

				<DeskSection title="Roles" :cols="1">
					<DeskField
						label="Granted roles"
						required
						:error="errors.roles"
						hint="Assigning this persona to a user grants these Frappe roles."
					>
						<PersonaRolesField v-model="form.roles" :available="assignableRoles" />
					</DeskField>
				</DeskSection>

				<DeskSection title="Description" :cols="1">
					<DeskField label="Notes">
						<DeskInput
							v-model="form.description"
							placeholder="What this persona is for"
						/>
					</DeskField>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
