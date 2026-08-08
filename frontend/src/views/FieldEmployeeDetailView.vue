<script setup>
// Field Employee detail — view / edit / delete. A field employee is a native
// ERPNext Employee with the BuildSuite `is_labour` flag set. Mirrors the
// inline view↔edit toggle used across the app's master detail pages.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { showToast } from "@/utils/appToast";
import { isPermissionDenied } from "@/utils/frappeError";
import { createDataAdapter } from "@/data/adapters";
import { saveFieldEmployee } from "@/data/fieldEmployeeApi";
import { fmtINR, fmtDate } from "@/utils/format";
import { validateFieldEmployee } from "@/utils/workforceForms";
import { useContractorOptions } from "@/composables/useContractorOptions";
import DeskPage from "@/components/desk/DeskPage.vue";
import AccessDenied from "@/components/AccessDenied.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import FieldEmployeeFormFields from "@/components/FieldEmployeeFormFields.vue";
import AllocatedProjectsTable from "@/components/AllocatedProjectsTable.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { contractorName } = useContractorOptions();
const { errors, applyServerErrors, setErrors } = useFormErrors({
	first_name: "first_name",
	gender: "gender",
	date_of_birth: "date_of_birth",
	date_of_joining: "date_of_joining",
	company: "company",
	custom_wage: "custom_wage",
});

const resource = adapter.read("Employee", props.id);
const doc = computed(() => resource?.doc || null);
// Without this a bad id sits on "Loading…" forever, because `doc` is null in
// both the in-flight and the not-found case.
const loading = computed(() => !!(resource?.loading ?? resource?.get?.loading));
const accessDenied = computed(() => isPermissionDenied(resource?.error));

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		first_name: d.first_name || "",
		last_name: d.last_name || "",
		gender: d.gender || "",
		date_of_birth: d.date_of_birth || "",
		date_of_joining: d.date_of_joining || "",
		status: d.status || "Active",
		custom_trade: d.custom_trade || "",
		custom_contractor: d.custom_contractor || "",
		cell_number: d.cell_number || "",
		company: d.company || "",
		custom_wage: d.custom_wage ?? null,
		custom_wage_for_overtime: d.custom_wage_for_overtime ?? null,
		allocated_projects: (d.custom_project_assigned || []).map((r) => ({
			project: r.project,
		})),
	};
}

const allocations = computed(() => doc.value?.custom_project_assigned || []);

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
	const e = validateFieldEmployee(form.value);
	setErrors(e);
	return Object.keys(e).length === 0;
}

async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		await saveFieldEmployee({ name: props.id, ...form.value });
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update field employee", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${doc.value?.employee_name}?`,
		message: "This worker record will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Employee", props.id);
		router.push("/field-employees");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete field employee", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Field Employees", to: "/field-employees" },
	{ label: doc.value?.employee_name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.employee_name || doc.name"
		:subtitle="`${doc.name} · ${doc.custom_trade || '—'}`"
		:breadcrumbs="breadcrumbs"
		:status="doc.status"
	>
		<template #actions>
			<button
				v-if="!editing"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<button
				v-if="!editing"
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
			<DeskSection title="Worker" :cols="3">
				<DeskField label="First name">
					<div class="text-sm text-ink-900">{{ doc.first_name || "—" }}</div>
				</DeskField>
				<DeskField label="Last name">
					<div class="text-sm text-ink-900">{{ doc.last_name || "—" }}</div>
				</DeskField>
				<DeskField label="Gender">
					<div class="text-sm text-ink-700">{{ doc.gender || "—" }}</div>
				</DeskField>

				<DeskField label="Date of birth">
					<div class="text-sm text-ink-700">{{ fmtDate(doc.date_of_birth) || "—" }}</div>
				</DeskField>
				<DeskField label="Date of joining">
					<div class="text-sm text-ink-700">
						{{ fmtDate(doc.date_of_joining) || "—" }}
					</div>
				</DeskField>
				<DeskField label="Status">
					<StatusBadge :status="doc.status" />
				</DeskField>

				<DeskField label="Trade">
					<div class="text-sm text-ink-700">{{ doc.custom_trade || "—" }}</div>
				</DeskField>
				<DeskField label="Contractor">
					<div class="text-sm text-ink-700">
						{{ contractorName(doc.custom_contractor) || "—" }}
					</div>
				</DeskField>
				<DeskField label="Phone">
					<div class="text-sm text-ink-700">{{ doc.cell_number || "—" }}</div>
				</DeskField>
				<DeskField label="Company">
					<div class="text-sm text-ink-700">{{ doc.company || "—" }}</div>
				</DeskField>
			</DeskSection>

			<DeskSection title="Wages" :cols="2">
				<DeskField label="Daily wage">
					<div class="text-sm tabular-nums text-ink-900">
						{{ doc.custom_wage ? fmtINR(doc.custom_wage) : "—" }}
					</div>
				</DeskField>
				<DeskField label="Overtime wage">
					<div class="text-sm tabular-nums text-ink-900">
						{{
							doc.custom_wage_for_overtime
								? fmtINR(doc.custom_wage_for_overtime) + "/hr"
								: "—"
						}}
					</div>
				</DeskField>
			</DeskSection>

			<AllocatedProjectsTable :rows="allocations" />
		</div>

		<!-- Edit mode -->
		<div v-else>
			<FieldEmployeeFormFields :form="form" :errors="errors" />

			<AllocatedProjectsTable
				:rows="form.allocated_projects"
				editable
				@add="form.allocated_projects.push({ project: '' })"
				@remove="(i) => form.allocated_projects.splice(i, 1)"
			/>
		</div>
	</DeskPage>

	<div v-else-if="loading" class="px-3 py-2 text-sm text-ink-500">Loading field employee…</div>

	<AccessDenied
		v-else-if="accessDenied"
		title="You don't have access to this field employee"
		back-to="/field-employees"
		back-label="Back to Field Employees"
	/>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Field employee not found.</div>
</template>
