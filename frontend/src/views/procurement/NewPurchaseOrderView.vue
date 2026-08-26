<script setup>
// Purchase Order form — create + edit (draft only). Supplier + project header and
// an editable item grid (item, qty, uom, rate → amount). Honors ?mr=<id> to convert
// an approved Material Request: project + still-to-order lines pre-fill and the PO's
// lines are linked back to the request. Saved via save_purchase_order.
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { getPurchaseOrder, getMrForPo, savePurchaseOrder } from "@/data/procurementApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtINR } from "@/utils/format";

const route = useRoute();
const router = useRouter();
const { canEdit, canCreate } = usePermissions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);
const canSaveForm = computed(() =>
	isEdit.value ? canEdit("purchaseOrder") : canCreate("purchaseOrder")
);

function emptyLine() {
	return { item_code: "", description: "", qty: null, uom: "", rate: null };
}
function inDays(n) {
	return new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);
}

const form = ref({
	supplier: "",
	project: route.query.project || "",
	schedule_date: inDays(10),
	material_request: null,
	lines: [emptyLine()],
});
const errors = ref({});
const saving = ref(false);

// Edit mode: load the draft PO.
watch(
	editingId,
	async (id) => {
		if (!id) return;
		try {
			const po = await getPurchaseOrder(id);
			if (po.state !== "Draft") {
				showToast("Only a draft order can be edited.", "error");
				router.replace(`/procurement/purchase-orders/${id}`);
				return;
			}
			form.value = {
				supplier: po.supplier || "",
				project: po.project || "",
				schedule_date: po.schedule_date || inDays(10),
				material_request: null,
				lines: (po.items || []).map((it) => ({
					item_code: it.item_code || "",
					description: it.description || "",
					qty: it.qty,
					uom: it.uom || "",
					rate: it.rate ?? null,
				})),
			};
			if (!form.value.lines.length) form.value.lines = [emptyLine()];
		} catch (err) {
			showToast(err.message || "Failed to load order", "error");
		}
	},
	{ immediate: true }
);

// Convert-from-MR: prefill project + lines when opened as /new?mr=<id>.
watch(
	() => route.query.mr,
	async (mrId) => {
		if (!mrId || isEdit.value) return;
		try {
			const pre = await getMrForPo(mrId);
			form.value.project = pre.project || form.value.project;
			form.value.material_request = pre.material_request;
			if (pre.lines?.length) {
				form.value.lines = pre.lines.map((l) => ({
					item_code: l.item_code || "",
					description: l.description || "",
					qty: l.qty,
					uom: l.uom || "",
					rate: l.rate ?? null,
				}));
			}
		} catch (err) {
			showToast(err.message || "Failed to load material request", "error");
		}
	},
	{ immediate: true }
);

const validLines = computed(() =>
	form.value.lines.filter((l) => l.item_code && Number(l.qty) > 0)
);
const total = computed(() =>
	validLines.value.reduce((a, l) => a + Number(l.qty) * (Number(l.rate) || 0), 0)
);

function addLine() {
	form.value.lines.push(emptyLine());
}
function removeLine(idx) {
	form.value.lines.splice(idx, 1);
	if (!form.value.lines.length) addLine();
}
function lineAmount(l) {
	return (Number(l.qty) || 0) * (Number(l.rate) || 0);
}

function validate() {
	const e = {};
	if (!form.value.supplier) e.supplier = "Pick a supplier.";
	if (!form.value.project) e.project = "Pick a project.";
	if (!validLines.value.length) e.lines = "Add at least one item with a quantity.";
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const po = await savePurchaseOrder({
			name: editingId.value || undefined,
			supplier: form.value.supplier,
			project: form.value.project,
			schedule_date: form.value.schedule_date,
			material_request: form.value.material_request || undefined,
			items: validLines.value.map((l) => ({
				item_code: l.item_code,
				description: l.description,
				qty: Number(l.qty),
				uom: l.uom || null,
				rate: Number(l.rate) || 0,
			})),
		});
		showToast(isEdit.value ? "Order saved." : "Order created.");
		router.push(`/procurement/purchase-orders/${po.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save order", "error");
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
	{ label: "Purchase Orders", to: "/procurement/purchase-orders" },
	isEdit.value
		? { label: editingId.value, to: `/procurement/purchase-orders/${editingId.value}` }
		: { label: "New" },
	...(isEdit.value ? [{ label: "Edit" }] : []),
]);
const pageTitle = computed(() =>
	isEdit.value ? `Edit ${editingId.value}` : "New Purchase Order"
);
const saveLabel = computed(() =>
	saving.value ? "Saving…" : isEdit.value ? "Save changes" : "Create order"
);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canSaveForm"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to {{ isEdit ? "edit this" : "create a" }} purchase order.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<div
				v-if="form.material_request"
				class="mb-4 px-4 py-2 bg-info-50 border border-info-200 rounded-md text-xs text-info-700"
			>
				Converting from Material Request
				<span class="font-mono">{{ form.material_request }}</span> — lines pre-filled; set
				the supplier and rates.
			</div>

			<DeskSection title="Order" :cols="3">
				<DeskField label="Supplier" required :error="errors.supplier">
					<DeskLinkPicker
						v-model="form.supplier"
						doctype="Supplier"
						label-field="supplier_name"
						value-field="name"
						:search-fields="['supplier_name', 'name']"
						placeholder="— Select supplier —"
					/>
				</DeskField>
				<DeskField
					label="Project"
					required
					:error="errors.project"
					:hint="isEdit ? 'Locked while editing.' : ''"
				>
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						:disabled="isEdit"
						placeholder="— Select project —"
					/>
				</DeskField>
				<DeskField label="Required by">
					<DeskInput v-model="form.schedule_date" type="date" />
				</DeskField>
			</DeskSection>

			<!-- Item lines -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Items
					</h3>
					<button
						type="button"
						class="text-xs text-brand-700 hover:underline"
						@click="addLine"
					>
						+ Add item
					</button>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 760px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2" style="min-width: 200px">Item</th>
								<th class="text-left px-3 py-2">Notes</th>
								<th class="text-right px-3 py-2 w-20">Qty</th>
								<th class="text-left px-3 py-2 w-28">UOM</th>
								<th class="text-right px-3 py-2 w-28">Rate</th>
								<th class="text-right px-3 py-2 w-28">Amount</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(line, idx) in form.lines"
								:key="idx"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2" style="min-width: 200px">
									<DeskLinkPicker
										v-model="line.item_code"
										doctype="Item"
										label-field="item_name"
										value-field="name"
										:search-fields="['item_name', 'item_code', 'name']"
										placeholder="— Item —"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model="line.description"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										placeholder="Notes…"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.qty"
										type="number"
										min="0"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
									/>
								</td>
								<td class="px-3 py-2" style="min-width: 110px">
									<DeskLinkPicker
										v-model="line.uom"
										doctype="UOM"
										label-field="name"
										value-field="name"
										placeholder="—"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.rate"
										type="number"
										min="0"
										step="0.01"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
									/>
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium"
								>
									{{ fmtINR(lineAmount(line)) }}
								</td>
								<td class="px-2 py-2 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										title="Remove"
										@click="removeLine(idx)"
									>
										✕
									</button>
								</td>
							</tr>
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-ink-200 bg-ink-50">
								<td
									colspan="5"
									class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
								>
									Total
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
								>
									{{ fmtINR(total) }}
								</td>
								<td></td>
							</tr>
						</tfoot>
					</table>
				</div>
				<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">{{ errors.lines }}</p>
			</section>
		</DeskForm>
	</DeskPage>
</template>
