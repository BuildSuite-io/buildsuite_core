<script setup>
// Subcontractor master detail — view / edit / delete + linked Work Orders.
// Mirrors the prototype's inline view↔edit toggle. Reads/writes through the
// subcontract API so contact person / phone / email (which live on the native
// Contact) travel with the trade / tax-id in one call.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { usePermissions } from "@/composables/usePermissions";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { getSubcontractor, updateSubcontractor } from "@/data/subcontractApi";
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
const { canEdit, canDelete, canCreate } = usePermissions();
const adapter = createDataAdapter(useDataStore()); // delete only
const { projectName } = useProjectNames();
const { errors, applyServerErrors, setErrors } = useFormErrors({
	subcontractor_name: "subcontractor_name",
	trade: "trade",
});

// A subcontractor is a Supplier (supplier_type="Subcontractor"); the API joins its
// primary Contact so { contact_person, phone, email } come back with it.
const sub = ref(null);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		sub.value = await getSubcontractor(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load subcontractor", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

// Linked Work Orders for this subcontractor.
const wosRes = useDocTypeList("Subcontractor Work Order", {
	fields: ["name", "project", "date", "total_value", "docstatus"],
	filters: [["subcontractor", "=", props.id]],
	orderBy: "date desc",
	pageLength: 0,
	cache: `buildsuite-subcontractor-wos-${props.id}`,
});
const linkedWOs = computed(() => wosRes.data || []);

// This subcontractor's bills → billed-to-date per work order for the "% Billed" column.
const billsRes = useDocTypeList("Subcontractor Bill", {
	fields: ["name", "work_order", "gross", "docstatus"],
	filters: [["subcontractor", "=", props.id]],
	orderBy: "modified desc",
	pageLength: 0,
	cache: `buildsuite-subcontractor-bills-${props.id}`,
});
const billedByWO = computed(() => {
	const map = {};
	for (const b of billsRes.data || []) {
		if (b.docstatus === 2 || !b.work_order) continue; // skip cancelled
		map[b.work_order] = (map[b.work_order] || 0) + (Number(b.gross) || 0);
	}
	return map;
});
function woPercentBilled(wo) {
	const total = Number(wo.total_value) || 0;
	if (total <= 0) return 0;
	return Math.min(100, Math.round(((billedByWO.value[wo.name] || 0) / total) * 1000) / 10);
}

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = sub.value;
	if (!d) return {};
	return {
		subcontractor_name: d.subcontractor_name || "",
		trade: d.trade || "",
		status: d.status || "Active",
		tax_id: d.tax_id || "",
		contact_person: d.contact_person || "",
		phone: d.phone || "",
		email: d.email || "",
	};
}
watch(
	sub,
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
		await updateSubcontractor(props.id, {
			subcontractor_name: form.value.subcontractor_name.trim(),
			trade: form.value.trade,
			tax_id: form.value.tax_id,
			status: form.value.status,
			contact_person: form.value.contact_person,
			phone: form.value.phone,
			email: form.value.email,
		});
		await load();
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
		title: `Delete ${sub.value?.subcontractor_name}?`,
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
	{ label: sub.value?.subcontractor_name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="sub"
		:title="sub.subcontractor_name"
		:subtitle="`${sub.name} · ${sub.trade || '—'}`"
		:breadcrumbs="breadcrumbs"
		:status="sub.status"
	>
		<template #actions>
			<button
				v-if="!editing && canEdit('subcontractor')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<button
				v-if="!editing && canDelete('subcontractor')"
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
				v-if="editing && canEdit('subcontractor')"
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
						{{ sub.subcontractor_name }}
					</div></DeskField
				>
				<DeskField label="Trade"
					><div class="text-sm text-ink-700">
						{{ sub.trade || "—" }}
					</div></DeskField
				>
				<DeskField label="Status"><StatusBadge :status="sub.status" /></DeskField>
				<DeskField label="Tax ID"
					><div class="text-sm font-mono text-ink-700">
						{{ sub.tax_id || "—" }}
					</div></DeskField
				>
			</DeskSection>

			<DeskSection title="Contact" :cols="3">
				<DeskField label="Contact person"
					><div class="text-sm text-ink-900">
						{{ sub.contact_person || "—" }}
					</div></DeskField
				>
				<DeskField label="Phone number"
					><div class="text-sm text-ink-700">
						{{ sub.phone || "—" }}
					</div></DeskField
				>
				<DeskField label="Email id"
					><div class="text-sm text-ink-700">
						{{ sub.email || "—" }}
					</div></DeskField
				>
			</DeskSection>

			<!-- Linked Work Orders -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Work orders ({{ linkedWOs.length }})
					</h3>
					<RouterLink
						v-if="canCreate('subcontractorWorkOrder')"
						:to="`/subcontractor-work-orders/new?subcontractor=${sub.name}`"
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
								<th class="text-right px-3 py-2">% Billed</th>
								<th class="text-left px-3 py-2">Status</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="wo in linkedWOs"
								:key="wo.name"
								class="border-t border-ink-100 hover:bg-brand-50/30 cursor-pointer"
								@click="router.push(`/subcontractor-work-orders/${encodeURIComponent(wo.name)}`)"
							>
								<td class="px-3 py-2">
									<DeskLink
										:to="`/subcontractor-work-orders/${encodeURIComponent(wo.name)}`"
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
								<td class="px-3 py-2 text-right tabular-nums text-ink-700">
									{{ woPercentBilled(wo) }}%
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

			<DeskSection title="Contact" :cols="3">
				<DeskField label="Contact person">
					<DeskInput v-model="form.contact_person" />
				</DeskField>
				<DeskField label="Phone number">
					<DeskInput v-model="form.phone" />
				</DeskField>
				<DeskField label="Email id">
					<DeskInput v-model="form.email" type="email" />
				</DeskField>
			</DeskSection>
		</div>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Loading subcontractor…</div>
</template>
