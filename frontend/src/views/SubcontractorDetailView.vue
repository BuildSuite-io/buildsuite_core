<script setup>
// Subcontractor master detail — view / edit / delete + linked Work Orders.
// Mirrors the prototype's inline view↔edit toggle.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { fmtCompactINR, fmtDate } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import TradePicker from "@/components/TradePicker.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { projectName } = useProjectNames();
const { errors, applyServerErrors, setErrors } = useFormErrors({
	subcontractor_name: "subcontractor_name",
	trade: "trade",
});

// A subcontractor is a Supplier (supplier_type="Subcontractor").
const resource = adapter.read("Supplier", props.id, { fields: ["*"] });
const doc = computed(() => resource?.doc || null);

// Linked Work Orders for this subcontractor.
const wosRes = useDocTypeList("Subcontractor Work Order", {
	fields: ["name", "project", "date", "total_value", "docstatus"],
	filters: [["subcontractor", "=", props.id]],
	orderBy: "date desc",
	pageLength: 0,
	cache: `buildsuite-subcontractor-wos-${props.id}`,
});
const linkedWOs = computed(() => wosRes.data || []);

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		subcontractor_name: d.supplier_name || "",
		trade: d.custom_trade || "",
		status: d.disabled ? "Inactive" : "Active",
		tax_id: d.tax_id || "",
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
	const e = {};
	if (!form.value.subcontractor_name?.trim()) e.subcontractor_name = "Name is required.";
	if (!form.value.trade) e.trade = "Trade is required.";
	setErrors(e);
	return Object.keys(e).length === 0;
}
async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		await adapter.update("Supplier", props.id, {
			supplier_name: form.value.subcontractor_name.trim(),
			custom_trade: form.value.trade,
			tax_id: form.value.tax_id,
			disabled: form.value.status === "Inactive" ? 1 : 0,
		});
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update subcontractor", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const n = linkedWOs.value.length;
	const ok = await confirmDialog({
		title: `Delete ${doc.value?.supplier_name}?`,
		message: n
			? `${n} work order${
					n === 1 ? "" : "s"
			  } reference this subcontractor and would be left dangling.`
			: "This subcontractor master record will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Supplier", props.id);
		router.push("/subcontractors");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete subcontractor", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractors", to: "/subcontractors" },
	{ label: doc.value?.subcontractor_name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.supplier_name"
		:subtitle="`${doc.name} · ${doc.custom_trade || '—'}`"
		:breadcrumbs="breadcrumbs"
		:status="doc.disabled ? 'Inactive' : 'Active'"
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
				class="desk-save-btn"
				:disabled="saving"
				@click="saveEdit"
			>
				{{ saving ? "Saving…" : "Save" }}
			</button>
		</template>

		<!-- View mode -->
		<div v-if="!editing">
			<DeskSection title="Details" :cols="3">
				<DeskField label="Name"
					><div class="text-sm text-ink-900">
						{{ doc.supplier_name }}
					</div></DeskField
				>
				<DeskField label="Trade"
					><div class="text-sm text-ink-700">
						{{ doc.custom_trade || "—" }}
					</div></DeskField
				>
				<DeskField label="Status"
					><StatusBadge :status="doc.disabled ? 'Inactive' : 'Active'"
				/></DeskField>
				<DeskField label="Tax ID"
					><div class="text-sm font-mono text-ink-700">
						{{ doc.tax_id || "—" }}
					</div></DeskField
				>
			</DeskSection>
			<p class="text-xs text-ink-400 mt-2">
				Contact person, phone and email live on this subcontractor's Supplier record in the
				accounting desk.
			</p>

			<!-- Linked Work Orders -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Work orders ({{ linkedWOs.length }})
					</h3>
					<RouterLink
						:to="`/subcontractor-work-orders/new?subcontractor=${doc.name}`"
						class="text-xs text-brand-700 hover:underline"
						>+ Raise new work order</RouterLink
					>
				</div>
				<div
					v-if="linkedWOs.length"
					class="bg-white border border-ink-200 rounded-lg overflow-hidden"
				>
					<table class="w-full text-xs">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">WO</th>
								<th class="text-left px-3 py-2">Project</th>
								<th class="text-left px-3 py-2">Date</th>
								<th class="text-right px-3 py-2">Value</th>
								<th class="text-left px-3 py-2">Status</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="wo in linkedWOs"
								:key="wo.name"
								class="border-t border-ink-100 hover:bg-brand-50/30 cursor-pointer"
								@click="router.push(`/subcontractor-work-orders/${wo.name}`)"
							>
								<td class="px-3 py-2">
									<DeskLink
										:to="`/subcontractor-work-orders/${wo.name}`"
										@click.stop
										>{{ wo.name }}</DeskLink
									>
								</td>
								<td class="px-3 py-2 text-ink-700">
									{{ projectName(wo.project) }}
								</td>
								<td class="px-3 py-2 text-ink-500">{{ fmtDate(wo.date) }}</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium"
								>
									{{ fmtCompactINR(wo.total_value) }}
								</td>
								<td class="px-3 py-2">
									<StatusBadge
										:status="
											{ 0: 'Draft', 1: 'Submitted', 2: 'Cancelled' }[
												wo.docstatus
											] || 'Draft'
										"
										size="xs"
									/>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div v-else class="text-xs text-ink-400 italic">
					No work orders raised against this subcontractor yet.
				</div>
			</section>
		</div>

		<!-- Edit mode -->
		<div v-else>
			<DeskSection title="Details" :cols="3">
				<DeskField label="Name" required :error="errors.subcontractor_name"
					><DeskInput v-model="form.subcontractor_name"
				/></DeskField>
				<DeskField label="Trade" required :error="errors.trade">
					<TradePicker v-model="form.trade" :error="errors.trade" />
				</DeskField>
				<DeskField label="Status">
					<DeskSelect v-model="form.status"
						><option>Active</option>
						<option>Inactive</option></DeskSelect
					>
				</DeskField>
				<DeskField label="Tax ID" hint="e.g. GSTIN (India), VAT No, TIN"
					><DeskInput v-model="form.tax_id"
				/></DeskField>
			</DeskSection>
		</div>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Loading subcontractor…</div>
</template>
