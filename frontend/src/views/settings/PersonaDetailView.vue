<script setup>
// Persona detail — edit a persona's slug, roles, order and status, or delete it
// (backend-backed via buildsuite_core.api.persona). The persona name is the record
// key and is locked. Admin / BSA only.

import { reactive, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useConfirm } from "@/composables/useConfirm";
import {
	getPersona,
	savePersona,
	deletePersona,
	listAssignableRoles,
	PROJECT_VISIBILITY_OPTIONS,
	DEFAULT_PROJECT_VISIBILITY,
} from "@/data/personaApi";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
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
	projectVisibility: DEFAULT_PROJECT_VISIBILITY,
	// On for a persona scoped to its teams' projects (the seed default), off for "All projects".
	teamScopedNotifications: true,
});
const errors = ref({});
const visibilityHint = () =>
	__(PROJECT_VISIBILITY_OPTIONS.find((o) => o.value === form.projectVisibility)?.hint || "");
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
		form.projectVisibility = data.project_visibility || DEFAULT_PROJECT_VISIBILITY;
		form.teamScopedNotifications = !!data.team_scoped_notifications;
		isDefault.value = !!data.is_default;
	} catch (err) {
		loadError.value = err.message || __("Could not load persona.");
	} finally {
		loading.value = false;
	}
}

async function save() {
	if (saving.value) return;
	if (!form.roles.length) {
		errors.value = { roles: __("Add at least one role") };
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
			project_visibility: form.projectVisibility,
			team_scoped_notifications: form.teamScopedNotifications ? 1 : 0,
		});
		showToast(__("Persona saved"));
		router.push("/settings/personas");
	} catch (err) {
		showToast(err.message || __("Failed to save persona"), "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.push("/settings/personas");
}

async function remove() {
	const ok = await confirmDialog({
		title: __("Delete persona"),
		message: __('Delete "{0}"? Users must be reassigned first.', [props.id]),
		confirmLabel: __("Delete persona"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deletePersona(props.id);
		showToast(__("Persona deleted"));
		router.push("/settings/personas");
	} catch (err) {
		showToast(err.message || __("Could not delete persona"), "error");
	}
}

const breadcrumbs = () => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: __("Personas"), to: "/settings/personas" },
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
	<DeskPage :title="props.id" :subtitle="__('Persona')" :breadcrumbs="breadcrumbs()">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? __('Saving…') : __('Save changes')"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">
				{{ __("Loading persona…") }}
			</div>

			<div
				v-else-if="loadError"
				class="mb-3 px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700"
				style="border-radius: 6px"
			>
				{{ loadError }}
			</div>

			<div v-else class="max-w-3xl mx-auto">
				<DeskSection id="basic" :title="__('Basic')">
					<DeskField
						:label="__('Persona name')"
						:hint="__('The name is the key and can\'t be changed.')"
					>
						<DeskInput :model-value="props.id" disabled />
					</DeskField>
					<DeskField :label="__('Slug')">
						<DeskInput v-model="form.slug" :placeholder="__('e.g. planner')" />
					</DeskField>
					<DeskField :label="__('Sort order')">
						<DeskInput v-model="form.sortOrder" type="number" />
					</DeskField>
					<DeskField :label="__('Enabled')">
						<label class="flex items-center gap-2 py-1 text-sm cursor-pointer">
							<input
								type="checkbox"
								v-model="form.enabled"
								class="accent-brand-600"
							/>
							<span>{{ form.enabled ? __("Enabled") : __("Disabled") }}</span>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection id="roles" :title="__('Roles')" :cols="1">
					<DeskField
						:label="__('Granted roles')"
						required
						:error="errors.roles"
						:hint="__('Assigning this persona to a user grants these Frappe roles.')"
					>
						<PersonaRolesField v-model="form.roles" :available="assignableRoles" />
					</DeskField>
				</DeskSection>

				<DeskSection id="project-access" :title="__('Project access')" :cols="1">
					<DeskField
						:label="__('Project visibility')"
						:hint="
							visibilityHint() +
							' ' +
							__(
								'Applies to projects and their tasks, work packages, progress entries and stage plans. System Manager always sees all projects.'
							)
						"
					>
						<DeskSelect
							v-model="form.projectVisibility"
							data-test="project-visibility"
						>
							<option
								v-for="o in PROJECT_VISIBILITY_OPTIONS"
								:key="o.value"
								:value="o.value"
							>
								{{ __(o.label) }}
							</option>
						</DeskSelect>
					</DeskField>
					<label
						class="flex items-start gap-2 text-xs text-ink-700 mt-3 cursor-pointer"
						data-test="team-scoped-notifications"
					>
						<input
							v-model="form.teamScopedNotifications"
							type="checkbox"
							class="mt-0.5 accent-brand-600"
						/>
						<span>
							<span class="font-medium text-ink-900">{{
								__("Workflow notifications follow the project team")
							}}</span>
							<span class="block text-[11px] text-ink-500 mt-0.5">{{
								__(
									"For workflows marked \"Team-scoped notifications\": once a user of this persona is on a project team, they are told about a document's next workflow step only when they are on its project's team. Until then, and for other workflows, they are told as usual."
								)
							}}</span>
						</span>
					</label>
				</DeskSection>

				<DeskSection id="description" :title="__('Description')" :cols="1">
					<DeskField :label="__('Notes')">
						<DeskInput
							v-model="form.description"
							:placeholder="__('What this persona is for')"
						/>
					</DeskField>
				</DeskSection>

				<DeskSection id="danger-zone" :title="__('Danger zone')" :cols="1">
					<div class="flex items-center justify-between gap-3 flex-wrap">
						<p class="text-xs text-ink-500">
							<span v-if="isDefault"
								>{{ __("This is a BuildSuite default persona.") }} </span
							>{{
								__(
									"Deleting a persona is permanent and only allowed when no user is assigned it."
								)
							}}
						</p>
						<button
							class="text-sm px-3 py-1.5 border border-danger-200 text-danger-700 hover:bg-danger-50"
							style="border-radius: 6px"
							@click="remove"
						>
							{{ __("Delete persona") }}
						</button>
					</div>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
