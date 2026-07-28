<script setup>
// Machinery Usage detail — view / edit / delete. Total is computed for display.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { fmtINR, fmtDate } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { errors, applyServerErrors, setErrors } = useFormErrors({ machine: "machine" });

const resource = adapter.read("Machinery Usage", props.id, { fields: ["*"] });
const doc = computed(() => resource?.doc || null);

const machineryRes = useDocTypeList("Machinery", {
	fields: ["name", "machinery_name", "machinery_type", "ownership", "rate", "rate_unit"],
	orderBy: "machinery_name asc",
	pageLength: 0,
	cache: "buildsuite-machinery-options",
});
const machineryOptions = computed(() =>
	(machineryRes.data || []).map((m) => ({
		value: m.name,
		label: m.machinery_name,
		hint: [m.machinery_type, m.ownership].filter(Boolean).join(" · "),
	})),
);
const projectRes = useDocTypeList("Project", {
	fields: ["name", "project_name"],
	orderBy: "project_name asc",
	pageLength: 0,
	cache: "buildsuite-project-options",
});
const projectOptions = computed(() =>
	(projectRes.data || []).map((p) => ({ value: p.name, label: p.project_name, hint: p.name })),
);

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		machine: d.machine || "",
		project: d.project || "",
		task: d.task || "",
		date: d.date || "",
		quantity: d.quantity || 0,
		unit: d.unit || "Days",
		rate: d.rate || 0,
		fuel_cost: d.fuel_cost || 0,
	};
}
watch(
	doc,
	(v) => {
		if (v && !editing.value) form.value = snapshot();
	},
	{ immediate: true },
);

function totalOf(o) {
	return (Number(o.quantity) || 0) * (Number(o.rate) || 0) + (Number(o.fuel_cost) || 0);
}
const viewTotal = computed(() => (doc.value ? fmtINR(totalOf(doc.value)) : "—"));

function startEdit() {
	form.value = snapshot();
	setErrors({});
	editing.value = true;
}
function cancelEdit() {
	editing.value = false;
}
function validate() {
	const e = {};
	if (!form.value.machine) e.machine = "Machine is required.";
	setErrors(e);
	return Object.keys(e).length === 0;
}
async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		const f = form.value;
		await adapter.update("Machinery Usage", props.id, {
			machine: f.machine,
			project: f.project,
			task: f.task,
			date: f.date,
			quantity: f.quantity,
			unit: f.unit,
			rate: f.rate,
			fuel_cost: f.fuel_cost,
		});
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update usage", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: "Delete usage entry?",
		message: "This usage log entry will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Machinery Usage", props.id);
		router.push("/machinery-usage");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete usage", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery Usage", to: "/machinery-usage" },
	{ label: doc.value ? `${doc.value.machine} · ${fmtDate(doc.value.date)}` : props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="`${doc.machine} — ${fmtDate(doc.date)}`"
		:subtitle="`${doc.quantity} ${doc.unit} · ${viewTotal}`"
		:breadcrumbs="breadcrumbs"
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
			<button v-if="editing" type="button" class="desk-save-btn" :disabled="saving" @click="saveEdit">
				{{ saving ? "Saving…" : "Save" }}
			</button>
		</template>

		<!-- View mode -->
		<div v-if="!editing">
			<DeskSection title="Usage" :cols="3">
				<DeskField label="Machine">
					<DeskLink :to="`/machinery/${doc.machine}`">{{ doc.machine }}</DeskLink>
				</DeskField>
				<DeskField label="Project"
					><div class="text-sm text-ink-700">{{ doc.project || "—" }}</div></DeskField
				>
				<DeskField label="Task"
					><div class="text-sm text-ink-700">{{ doc.task || "—" }}</div></DeskField
				>
				<DeskField label="Date"
					><div class="text-sm text-ink-800">{{ fmtDate(doc.date) }}</div></DeskField
				>
				<DeskField label="Quantity"
					><div class="text-sm text-ink-800 tabular-nums">
						{{ doc.quantity }} {{ doc.unit }}
					</div></DeskField
				>
				<DeskField label="Rate"
					><div class="text-sm text-ink-800 tabular-nums">{{ fmtINR(doc.rate) }}</div></DeskField
				>
				<DeskField label="Fuel cost"
					><div class="text-sm text-ink-800 tabular-nums">
						{{ fmtINR(doc.fuel_cost) }}
					</div></DeskField
				>
				<DeskField label="Total"
					><div class="text-sm text-ink-900 font-medium tabular-nums">
						{{ viewTotal }}
					</div></DeskField
				>
			</DeskSection>
		</div>

		<!-- Edit mode -->
		<div v-else>
			<DeskSection title="Usage" :cols="3">
				<DeskField label="Machine" required :error="errors.machine">
					<DeskSearchableSelect
						v-model="form.machine"
						:options="machineryOptions"
						placeholder="Pick a machine…"
						search-placeholder="Search machine…"
					/>
				</DeskField>
				<DeskField label="Project">
					<DeskSearchableSelect
						v-model="form.project"
						:options="projectOptions"
						placeholder="Pick a project…"
						search-placeholder="Search project…"
						allow-clear
					/>
				</DeskField>
				<DeskField label="Task">
					<DeskLinkPicker
						v-model="form.task"
						doctype="Task"
						label-field="subject"
						value-field="name"
						:filters="form.project ? [['project', '=', form.project]] : []"
						placeholder="Task…"
					/>
				</DeskField>

				<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
				<DeskField label="Quantity"
					><DeskInput v-model.number="form.quantity" type="number" min="0" step="0.5"
				/></DeskField>
				<DeskField label="Unit">
					<DeskSelect v-model="form.unit"
						><option>Days</option>
						<option>Hours</option></DeskSelect
					>
				</DeskField>

				<DeskField label="Rate (₹)"
					><DeskInput v-model.number="form.rate" type="number" min="0"
				/></DeskField>
				<DeskField label="Fuel cost (₹)"
					><DeskInput v-model.number="form.fuel_cost" type="number" min="0"
				/></DeskField>
			</DeskSection>
		</div>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Loading usage…</div>
</template>
