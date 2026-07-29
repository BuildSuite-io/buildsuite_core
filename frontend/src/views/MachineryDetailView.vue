<script setup>
// Machinery master detail — view / edit / delete. Mirrors the demo.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
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
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { errors, applyServerErrors, setErrors } = useFormErrors({
	machinery_code: "machinery_code",
	machinery_name: "machinery_name",
	machinery_type: "machinery_type",
	company: "company",
});

const resource = adapter.read("Machinery", props.id, { fields: ["*"] });
const doc = computed(() => resource?.doc || null);

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		machinery_code: d.machinery_code || "",
		machinery_name: d.machinery_name || "",
		machinery_type: d.machinery_type || "",
		ownership: d.ownership || "Owned",
		rate: d.rate || 0,
		rate_unit: d.rate_unit || "Day",
		owner_vendor: d.owner_vendor || "",
		asset: d.asset || "",
		status: d.status || "Active",
		company: d.company || "",
	};
}
watch(
	doc,
	(v) => {
		if (v && !editing.value) form.value = snapshot();
	},
	{ immediate: true },
);

const rateDisplay = computed(() => {
	const d = doc.value;
	if (!d || !d.rate) return "—";
	return `${fmtINR(d.rate)}/${d.rate_unit || "—"}`;
});

const usageRes = useDocTypeList("Machinery Usage", {
	fields: ["name", "date", "project", "task", "quantity", "unit", "rate", "fuel_cost"],
	filters: { machine: props.id },
	orderBy: "date desc",
	pageLength: 0,
});
const usageRows = computed(() => usageRes.data || []);
function usageTotal(u) {
	return (Number(u.quantity) || 0) * (Number(u.rate) || 0) + (Number(u.fuel_cost) || 0);
}

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
	if (!form.value.machinery_name?.trim()) e.machinery_name = "Name is required.";
	if (!form.value.machinery_type) e.machinery_type = "Type is required.";
	if (!form.value.company) e.company = "Company is required.";
	setErrors(e);
	return Object.keys(e).length === 0;
}
async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		const f = form.value;
		await adapter.update("Machinery", props.id, {
			machinery_name: f.machinery_name.trim(),
			machinery_type: f.machinery_type,
			ownership: f.ownership,
			rate: f.rate,
			rate_unit: f.rate_unit,
			owner_vendor: f.owner_vendor,
			asset: f.ownership === "Owned" ? f.asset : "",
			status: f.status,
			company: f.company,
		});
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update machinery", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${doc.value?.machinery_name}?`,
		message: "This machinery record will be removed permanently. Its usage logs will remain.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Machinery", props.id);
		router.push("/machinery");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete machinery", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery", to: "/machinery" },
	{ label: doc.value?.machinery_name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.machinery_name"
		:subtitle="`${doc.machinery_type || '—'} · ${doc.ownership}`"
		:breadcrumbs="breadcrumbs"
		:status="[doc.status]"
	>
		<template #actions>
			<RouterLink
				v-if="!editing"
				:to="`/machinery-usage/new?machine=${doc.name}`"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
			>
				+ Log usage
			</RouterLink>
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
			<DeskSection title="Machinery" :cols="3">
				<DeskField label="Code"
					><div class="text-sm font-mono text-ink-900">{{ doc.machinery_code }}</div></DeskField
				>
				<DeskField label="Type"
					><div class="text-sm text-ink-700">{{ doc.machinery_type || "—" }}</div></DeskField
				>
				<DeskField label="Ownership"
					><div class="text-sm text-ink-800">{{ doc.ownership }}</div></DeskField
				>
				<DeskField label="Rate"
					><div class="text-sm text-ink-800 tabular-nums">{{ rateDisplay }}</div></DeskField
				>
				<DeskField label="Owner / Vendor"
					><div class="text-sm text-ink-800">{{ doc.owner_vendor || "—" }}</div></DeskField
				>
				<DeskField label="Status"><StatusBadge :status="doc.status" /></DeskField>
				<DeskField v-if="doc.ownership === 'Owned'" label="Linked asset (ERPNext)">
					<DeskLink v-if="doc.asset" :href="`/app/asset/${doc.asset}`" target="_blank"
						>{{ doc.asset }}</DeskLink
					>
					<div v-else class="text-sm text-ink-400">— not linked —</div>
				</DeskField>
				<DeskField label="Company"
					><div class="text-sm text-ink-700">{{ doc.company || "—" }}</div></DeskField
				>
			</DeskSection>

			<!-- Usage logs for this machine -->
			<DeskSection :title="`Usage logs (${usageRows.length})`" :cols="1">
				<table v-if="usageRows.length" class="w-full text-sm">
					<thead>
						<tr class="text-left text-ink-500 border-b border-ink-100">
							<th class="py-1.5 pr-3 font-medium">Date</th>
							<th class="py-1.5 pr-3 font-medium">Project</th>
							<th class="py-1.5 pr-3 font-medium">Task</th>
							<th class="py-1.5 pr-3 font-medium text-right">Qty</th>
							<th class="py-1.5 font-medium text-right">Total</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="u in usageRows"
							:key="u.name"
							class="border-b border-ink-50 hover:bg-ink-50 cursor-pointer"
							@click="router.push(`/machinery-usage/${u.name}`)"
						>
							<td class="py-1.5 pr-3 text-ink-500">{{ fmtDate(u.date) }}</td>
							<td class="py-1.5 pr-3 text-ink-700">{{ u.project || "—" }}</td>
							<td class="py-1.5 pr-3 text-ink-500">{{ u.task || "—" }}</td>
							<td class="py-1.5 pr-3 text-right tabular-nums">{{ u.quantity }} {{ u.unit }}</td>
							<td class="py-1.5 text-right tabular-nums text-ink-900 font-medium">
								{{ fmtINR(usageTotal(u)) }}
							</td>
						</tr>
					</tbody>
				</table>
				<div v-else class="text-sm text-ink-400 italic">No usage logged yet.</div>
			</DeskSection>
		</div>

		<!-- Edit mode -->
		<div v-else>
			<DeskSection title="Machinery" :cols="3">
				<DeskField label="Code" hint="Record ID — cannot be changed">
					<div class="text-sm font-mono text-ink-500">{{ doc.machinery_code }}</div>
				</DeskField>
				<DeskField label="Name" required :error="errors.machinery_name"
					><DeskInput v-model="form.machinery_name"
				/></DeskField>
				<DeskField label="Type" required :error="errors.machinery_type">
					<DeskLinkPicker
						v-model="form.machinery_type"
						doctype="Machinery Type"
						label-field="name"
						value-field="name"
						placeholder="Pick a type…"
					/>
				</DeskField>

				<DeskField label="Ownership">
					<DeskSelect v-model="form.ownership"
						><option>Owned</option>
						<option>Hired</option></DeskSelect
					>
				</DeskField>
				<DeskField label="Rate (₹)"
					><DeskInput v-model.number="form.rate" type="number" min="0"
				/></DeskField>
				<DeskField label="Rate Unit">
					<DeskSelect v-model="form.rate_unit"
						><option>Hour</option>
						<option>Day</option>
						<option>Month</option></DeskSelect
					>
				</DeskField>

				<DeskField label="Owner / Vendor"
					><DeskInput v-model="form.owner_vendor"
				/></DeskField>
				<DeskField label="Status">
					<DeskSelect v-model="form.status"
						><option>Active</option>
						<option>Inactive</option></DeskSelect
					>
				</DeskField>
				<DeskField
					v-if="form.ownership === 'Owned'"
					label="Asset"
					hint="Optional — owned fixed asset."
				>
					<DeskLinkPicker
						v-model="form.asset"
						doctype="Asset"
						label-field="asset_name"
						value-field="name"
						placeholder="Link an asset…"
					/>
				</DeskField>

				<DeskField label="Company" required :error="errors.company">
					<DeskLinkPicker
						v-model="form.company"
						doctype="Company"
						label-field="name"
						value-field="name"
						placeholder="Company…"
					/>
				</DeskField>
			</DeskSection>
		</div>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Loading machinery…</div>
</template>
