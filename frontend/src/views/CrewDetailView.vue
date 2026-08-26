<script setup>
// Crew detail — view / edit / delete. A crew is a standing gang, not tied to a
// project. Mirrors the inline view↔edit toggle used across the master pages.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { showToast } from "@/utils/appToast";
import { isPermissionDenied } from "@/utils/frappeError";
import { createDataAdapter } from "@/data/adapters";
import { usePermissions } from "@/composables/usePermissions";
import { saveCrew } from "@/data/crewApi";
import { validateCrew } from "@/utils/workforceForms";
import DeskPage from "@/components/desk/DeskPage.vue";
import AccessDenied from "@/components/AccessDenied.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import CrewFormFields from "@/components/CrewFormFields.vue";
import CrewMembersTable from "@/components/CrewMembersTable.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { canEdit, canDelete } = usePermissions();
const { workerName } = useFieldEmployeeOptions();
const { errors, applyServerErrors, setErrors } = useFormErrors({
	crew_name: "crew_name",
	company: "company",
	members: "members",
});

const resource = adapter.read("Crew", props.id);
const doc = computed(() => resource?.doc || null);
// Without this a bad id sits on "Loading…" forever, because `doc` is null in
// both the in-flight and the not-found case.
const loading = computed(() => !!(resource?.loading ?? resource?.get?.loading));
const accessDenied = computed(() => isPermissionDenied(resource?.error));
const members = computed(() => doc.value?.members || []);

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		crew_name: d.crew_name || "",
		crew_leader: d.crew_leader || "",
		trade: d.trade || "",
		company: d.company || "",
		members: (d.members || []).map((r) => ({
			field_employee: r.field_employee,
			role_in_crew: r.role_in_crew,
			daily_rate: r.daily_rate,
		})),
	};
}
watch(
	doc,
	(v) => {
		if (v && !editing.value) form.value = snapshot();
	},
	{ immediate: true }
);

function startEdit() {
	form.value = snapshot();
	setErrors({});
	editing.value = true;
}
function cancelEdit() {
	editing.value = false;
}

function validate() {
	const e = validateCrew(form.value);
	setErrors(e);
	return Object.keys(e).length === 0;
}

async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		await saveCrew({ name: props.id, ...form.value });
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update crew", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${doc.value?.crew_name}?`,
		message: "The crew is removed. Field attendance that referenced it keeps its stored rows.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Crew", props.id);
		router.push("/crews");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete crew", "error");
	}
}

const subtitle = computed(() => {
	const d = doc.value;
	if (!d) return "";
	const n = members.value.length;
	const count = `${n} member${n === 1 ? "" : "s"}`;
	return d.trade ? `${count} · ${d.trade}` : count;
});

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Crews", to: "/crews" },
	{ label: doc.value?.crew_name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.crew_name || doc.name"
		:subtitle="subtitle"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="!editing && canEdit('crew')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<button
				v-if="!editing && canDelete('crew')"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
			<button
				v-if="editing"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="cancelEdit"
			>
				Cancel
			</button>
			<button
				v-if="editing"
				type="button"
				class="desk-save-btn !text-xs"
				:disabled="saving"
				@click="saveEdit"
			>
				{{ saving ? "Saving…" : "Save" }}
			</button>
		</template>

		<!-- View mode -->
		<div v-if="!editing">
			<DeskSection title="Crew" :cols="2">
				<DeskField label="Crew leader">
					<div class="text-sm text-ink-900">
						{{ doc.crew_leader ? workerName(doc.crew_leader) : "—" }}
					</div>
				</DeskField>
				<DeskField label="Trade">
					<div class="text-sm text-ink-700">{{ doc.trade || "—" }}</div>
				</DeskField>
				<DeskField label="Company">
					<div class="text-sm text-ink-700">{{ doc.company || "—" }}</div>
				</DeskField>
			</DeskSection>

			<CrewMembersTable :rows="members" />
		</div>

		<!-- Edit mode -->
		<div v-else>
			<CrewFormFields :form="form" :errors="errors" />

			<CrewMembersTable
				:rows="form.members"
				:error="errors.members"
				editable
				@add="form.members.push({ field_employee: '', role_in_crew: '' })"
				@remove="(i) => form.members.splice(i, 1)"
			/>
		</div>
	</DeskPage>

	<div v-else-if="loading" class="px-3 py-2 text-sm text-ink-500">Loading crew…</div>

	<AccessDenied
		v-else-if="accessDenied"
		title="You don't have access to this crew"
		back-to="/crews"
		back-label="Back to Crews"
	/>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Crew not found.</div>
</template>
