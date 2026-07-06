<script setup>
// Persona detail — edit a persona's slug, roles, order and status, or delete it
// (backend-backed via buildsuite_core.api.persona). The persona name is the record
// key and is locked. Admin / BSA only.

import { reactive, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useConfirm } from "@/composables/useConfirm";
import { getPersona, savePersona, deletePersona, listAssignableRoles } from "@/data/personaApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import PersonaRolesField from "@/components/PersonaRolesField.vue";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const store = useDataStore();
const confirmDialog = useConfirm();

const form = reactive({
	slug: "",
	sortOrder: 0,
	enabled: true,
	description: "",
	roles: [],
});
const errors = ref({});
const isDefault = ref(false);
const saving = ref(false);
const loading = ref(true);
const loadError = ref("");
const assignableRoles = ref([]);

async function load() {
	loading.value = true;
	loadError.value = "";
	try {
		const [data, roles] = await Promise.all([getPersona(props.id), listAssignableRoles()]);
		assignableRoles.value = roles || [];
		form.slug = data.slug || "";
		form.sortOrder = data.sort_order || 0;
		form.enabled = !!data.enabled;
		form.description = data.description || "";
		form.roles = data.roles || [];
		isDefault.value = !!data.is_default;
	} catch (err) {
		loadError.value = err.message || "Could not load persona.";
	} finally {
		loading.value = false;
	}
}

async function save() {
	if (saving.value) return;
	if (!form.roles.length) {
		errors.value = { roles: "Add at least one role" };
		return;
	}
	errors.value = {};
	saving.value = true;
	try {
		await savePersona({
			name: props.id,
			slug: form.slug.trim(),
			description: form.description.trim(),
			enabled: form.enabled ? 1 : 0,
			sort_order: Number(form.sortOrder) || 0,
			roles: form.roles,
		});
		showToast("Persona saved");
		router.push("/settings/personas");
	} catch (err) {
		showToast(err.message || "Failed to save persona", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.push("/settings/personas");
}

async function remove() {
	const ok = await confirmDialog({
		title: "Delete persona",
		message: `Delete "${props.id}"? Users must be reassigned first.`,
		confirmLabel: "Delete persona",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deletePersona(props.id);
		showToast("Persona deleted");
		router.push("/settings/personas");
	} catch (err) {
		showToast(err.message || "Could not delete persona", "error");
	}
}

const breadcrumbs = () => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Personas", to: "/settings/personas" },
	{ label: props.id },
];

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) {
		router.replace("/settings");
		return;
	}
	load();
});
</script>

<template>
	<DeskPage :title="props.id" subtitle="Persona" :breadcrumbs="breadcrumbs()">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Saving…' : 'Save changes'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">
				Loading persona…
			</div>

			<div
				v-else-if="loadError"
				class="mb-3 px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700"
				style="border-radius: 6px"
			>
				{{ loadError }}
			</div>

			<div v-else class="max-w-3xl mx-auto">
				<DeskSection title="Basic">
					<DeskField
						label="Persona name"
						hint="The name is the key and can't be changed."
					>
						<DeskInput :model-value="props.id" disabled />
					</DeskField>
					<DeskField label="Slug">
						<DeskInput v-model="form.slug" placeholder="e.g. planner" />
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

				<DeskSection title="Danger zone" :cols="1">
					<div class="flex items-center justify-between gap-3 flex-wrap">
						<p class="text-xs text-ink-500">
							<span v-if="isDefault">This is a BuildSuite default persona. </span
							>Deleting a persona is permanent and only allowed when no user is
							assigned it.
						</p>
						<button
							class="text-sm px-3 py-1.5 border border-danger-200 text-danger-700 hover:bg-danger-50"
							style="border-radius: 6px"
							@click="remove"
						>
							Delete persona
						</button>
					</div>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
