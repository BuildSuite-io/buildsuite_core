<script setup>
// Purchase Receipt form — record goods received against a submitted Purchase Order.
// Pick an open PO and its remaining-to-receive lines pre-fill (item, uom, PO rate,
// ordered qty, received qty default = remaining). Supplier + project are derived
// from the PO; one receiving warehouse applies to the whole receipt. Saved via
// save_purchase_receipt (seeded from ERPNext's PO → Receipt mapper).
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import {
	getOpenPurchaseOrders,
	getReceiptDraft,
	getPurchaseReceipt,
	savePurchaseReceipt,
} from "@/data/procurementApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtDate, fmtINR } from "@/utils/format";

const route = useRoute();
const router = useRouter();
const { canEdit, canCreate } = usePermissions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);
const canSaveForm = computed(() =>
	isEdit.value ? canEdit("purchaseReceipt") : canCreate("purchaseReceipt")
);

function today() {
	return new Date().toISOString().slice(0, 10);
}

const openPos = ref([]);
const selectedPo = ref(route.query.po || "");
const receipt = ref({
	supplier_name: "",
	project_name: "",
	warehouse: "",
	posting_date: today(),
	lines: [],
});
const error = ref("");
const saving = ref(false);

const poOptions = computed(() =>
	openPos.value.map((po) => ({
		value: po.name,
		label: `${po.name} — ${po.supplier_name || po.supplier}`,
		hint: [
			po.project_name || po.project,
			po.schedule_date ? "due " + fmtDate(po.schedule_date) : "",
		]
			.filter(Boolean)
			.join(" · "),
	}))
);

// New receipt: load open POs for the picker.
watch(
	isEdit,
	async (edit) => {
		if (edit) return;
		try {
			openPos.value = await getOpenPurchaseOrders();
		} catch (err) {
			showToast(err.message || "Failed to load purchase orders", "error");
		}
	},
	{ immediate: true }
);

// New receipt: when a PO is chosen, pull the remaining-to-receive draft lines.
watch(
	selectedPo,
	async (poName) => {
		if (!poName || isEdit.value) return;
		try {
			const draft = await getReceiptDraft(poName);
			receipt.value = {
				supplier_name: draft.supplier_name || draft.supplier,
				project_name: draft.project_name || draft.project,
				warehouse: draft.warehouse || "",
				posting_date: today(),
				lines: (draft.items || []).map((it) => ({
					item_code: it.item_code,
					item_name: it.item_name,
					uom: it.uom,
					rate: it.rate,
					ordered_qty: it.ordered_qty,
					received_qty: it.received_qty,
					purchase_order_item: it.purchase_order_item,
				})),
			};
		} catch (err) {
			error.value = err.message || "Can't receive against this order.";
		}
	},
	{ immediate: true }
);

// Edit mode: load the existing draft receipt.
watch(
	editingId,
	async (id) => {
		if (!id) return;
		try {
			const pr = await getPurchaseReceipt(id);
			if (pr.state !== "Draft") {
				showToast("Only a draft receipt can be edited.", "error");
				router.replace(`/procurement/receipts/${id}`);
				return;
			}
			selectedPo.value = pr.purchase_order;
			receipt.value = {
				supplier_name: pr.supplier_name || pr.supplier,
				project_name: pr.project_name || pr.project,
				warehouse: pr.warehouse || "",
				posting_date: pr.posting_date || today(),
				lines: (pr.items || []).map((it) => ({
					item_code: it.item_code,
					item_name: it.item_name,
					uom: it.uom,
					rate: it.rate,
					ordered_qty: it.ordered_qty,
					received_qty: it.received_qty,
					purchase_order_item: it.purchase_order_item,
				})),
			};
		} catch (err) {
			showToast(err.message || "Failed to load receipt", "error");
		}
	},
	{ immediate: true }
);

const receivedLines = computed(() =>
	receipt.value.lines.filter((l) => Number(l.received_qty) > 0)
);
const total = computed(() =>
	receivedLines.value.reduce((a, l) => a + Number(l.received_qty) * (Number(l.rate) || 0), 0)
);
const canSave = computed(
	() => !!selectedPo.value && !!receipt.value.warehouse && receivedLines.value.length > 0
);

async function onSave() {
	error.value = "";
	if (!selectedPo.value) {
		error.value = "Pick a purchase order.";
		return;
	}
	if (!receipt.value.warehouse) {
		error.value = "Pick a receiving warehouse.";
		return;
	}
	if (!receivedLines.value.length) {
		error.value = "Enter at least one received quantity.";
		return;
	}
	saving.value = true;
	try {
		const pr = await savePurchaseReceipt({
			name: editingId.value || undefined,
			purchase_order: selectedPo.value,
			posting_date: receipt.value.posting_date,
			warehouse: receipt.value.warehouse,
			items: receivedLines.value.map((l) => ({
				item_code: l.item_code,
				received_qty: Number(l.received_qty),
				purchase_order_item: l.purchase_order_item,
			})),
		});
		showToast(isEdit.value ? "Receipt saved." : "Receipt recorded.");
		router.push(`/procurement/receipts/${pr.name}`);
	} catch (err) {
		error.value = err.message || "Failed to save receipt";
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Purchase Receipts", to: "/procurement/receipts" },
	isEdit.value
		? { label: editingId.value, to: `/procurement/receipts/${editingId.value}` }
		: { label: "New" },
	...(isEdit.value ? [{ label: "Edit" }] : []),
]);
const pageTitle = computed(() =>
	isEdit.value ? `Edit ${editingId.value}` : "New Purchase Receipt"
);
const saveLabel = computed(() =>
	saving.value ? "Saving…" : isEdit.value ? "Save changes" : "Confirm receipt"
);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canSaveForm"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to {{ isEdit ? "edit this" : "create a" }} purchase receipt.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					:can-save="canSave"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<div
				v-if="error"
				class="mb-4 bg-danger-50 border border-danger-200 rounded-lg px-4 py-2.5 text-xs text-danger-700"
			>
				{{ error }}
			</div>

			<DeskSection title="Receipt" :cols="3">
				<DeskField label="Purchase order" required>
					<DeskSearchableSelect
						v-if="!isEdit"
						v-model="selectedPo"
						:options="poOptions"
						placeholder="— Select open PO —"
						search-placeholder="Search PO, supplier…"
					/>
					<div v-else class="text-sm text-ink-900 pt-1.5 font-mono">
						{{ selectedPo }}
					</div>
				</DeskField>
				<DeskField
					label="Receiving warehouse"
					required
					hint="Where the goods land on site."
				>
					<DeskLinkPicker
						v-model="receipt.warehouse"
						doctype="Warehouse"
						label-field="warehouse_name"
						value-field="name"
						:filters="[['is_group', '=', 0]]"
						placeholder="— Select warehouse —"
					/>
				</DeskField>
				<DeskField label="Received on">
					<DeskInput v-model="receipt.posting_date" type="date" />
				</DeskField>
				<DeskField
					v-if="receipt.supplier_name"
					label="Supplier"
					hint="From the purchase order."
				>
					<div class="text-sm text-ink-900 pt-1.5">{{ receipt.supplier_name }}</div>
				</DeskField>
				<DeskField
					v-if="receipt.project_name"
					label="Project"
					hint="From the purchase order."
				>
					<div class="text-sm text-ink-900 pt-1.5">{{ receipt.project_name }}</div>
				</DeskField>
			</DeskSection>

			<!-- Received lines -->
			<section v-if="receipt.lines.length" class="mt-6">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">
					Items received
				</h3>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 680px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">Item</th>
								<th class="text-left px-3 py-2">UOM</th>
								<th class="text-right px-3 py-2">Ordered</th>
								<th class="text-right px-3 py-2">PO rate</th>
								<th class="text-right px-3 py-2 w-28">Received now</th>
								<th class="text-right px-3 py-2">Amount</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(l, idx) in receipt.lines"
								:key="idx"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2 text-ink-900">
									{{ l.item_name || l.item_code }}
								</td>
								<td class="px-3 py-2 text-ink-500">{{ l.uom || "—" }}</td>
								<td class="px-3 py-2 text-right tabular-nums text-ink-500">
									{{ l.ordered_qty }}
								</td>
								<td class="px-3 py-2 text-right tabular-nums text-ink-700">
									{{ fmtINR(l.rate) }}
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="l.received_qty"
										type="number"
										min="0"
										:max="l.ordered_qty"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none border border-ink-200 rounded px-1.5"
									/>
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium"
								>
									{{
										fmtINR(
											(Number(l.received_qty) || 0) * (Number(l.rate) || 0)
										)
									}}
								</td>
							</tr>
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-ink-200 bg-ink-50">
								<td
									colspan="5"
									class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
								>
									Total received
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
								>
									{{ fmtINR(total) }}
								</td>
							</tr>
						</tfoot>
					</table>
				</div>
			</section>
			<div v-else-if="selectedPo" class="mt-6 text-xs text-ink-400 italic">
				Nothing left to receive on this order.
			</div>
		</DeskForm>
	</DeskPage>
</template>
