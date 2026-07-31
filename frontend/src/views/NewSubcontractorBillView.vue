<script setup>
// Subcontractor Bill — create + edit (core). Two modes:
//   • From Work Order — this period's lines are derived from certified
//     Measurement Books (read-only qty), retention inherited from the WO.
//   • Direct — free-text charge lines for one-off / lump-sum work.
// Taxes, TDS, discount and retention overrides are edited on the detail page
// (Draft-editable). Pre-fills the WO from ?work_order=… on the URL.

import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { getBill, getWoBillContext, saveBill } from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import { fmtINR } from "@/utils/format";

const route = useRoute();
const router = useRouter();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);

function todayIso() {
	return new Date().toISOString().slice(0, 10);
}

const mode = ref("wo"); // 'wo' | 'direct'
const saving = ref(false);
const errors = ref({});

const form = ref({
	work_order: route.query.work_order || "",
	subcontractor: "",
	project: "",
	date: todayIso(),
	retention_percent: 5,
	lines: [{ scope: "", cost_code: null, amount: 0 }],
});

const woContext = ref(null); // { subcontractor_name, project_name, retention_percent, next_ra_no, lines[] }

async function loadWoContext(wo) {
	if (!wo) {
		woContext.value = null;
		return;
	}
	try {
		const ctx = await getWoBillContext(wo);
		woContext.value = ctx;
		form.value.retention_percent = ctx.retention_percent ?? 5;
	} catch (err) {
		woContext.value = null;
		showToast(err.message || "Failed to load work order", "error");
	}
}

watch(
	editingId,
	async (id) => {
		if (id) {
			try {
				const bill = await getBill(id);
				if (bill.docstatus !== 0) {
					router.replace(`/subcontractor-bills/${id}`);
					return;
				}
				mode.value = bill.is_direct ? "direct" : "wo";
				form.value = {
					work_order: bill.work_order || "",
					subcontractor: bill.subcontractor || "",
					project: bill.project || "",
					date: bill.date || todayIso(),
					retention_percent: bill.retention_percent ?? 0,
					lines: bill.is_direct
						? (bill.lines || []).map((l) => ({
								scope: l.scope || "",
								cost_code: l.cost_code_label || null,
								amount: l.this_period_amount || 0,
						  }))
						: [{ scope: "", cost_code: null, amount: 0 }],
				};
				if (!bill.is_direct) loadWoContext(bill.work_order);
			} catch (err) {
				showToast(err.message || "Failed to load bill", "error");
			}
		} else if (form.value.work_order) {
			loadWoContext(form.value.work_order);
		}
	},
	{ immediate: true }
);

function onWorkOrderChange(wo) {
	form.value.work_order = wo;
	loadWoContext(wo);
}

const woLines = computed(() => woContext.value?.lines || []);
const woGross = computed(() =>
	woLines.value.reduce((a, l) => a + (Number(l.this_period_amount) || 0), 0)
);
const directGross = computed(() =>
	form.value.lines.reduce((a, l) => a + (Number(l.amount) || 0), 0)
);
const gross = computed(() => (mode.value === "wo" ? woGross.value : directGross.value));
const retention = computed(
	() => +((gross.value * (Number(form.value.retention_percent) || 0)) / 100).toFixed(2)
);
const netPayable = computed(() => +(gross.value - retention.value).toFixed(2));

function addLine() {
	form.value.lines.push({ scope: "", cost_code: null, amount: 0 });
}
function removeLine(i) {
	form.value.lines.splice(i, 1);
}

function validate() {
	const e = {};
	if (mode.value === "wo") {
		if (!form.value.work_order) e.work_order = "Pick a work order.";
		if (!isEdit.value && woGross.value <= 0)
			e.lines = "No fresh measured quantity to bill — certify a Measurement Book first.";
	} else {
		if (!form.value.subcontractor) e.subcontractor = "Pick a subcontractor.";
		if (!form.value.project) e.project = "Pick a project.";
		if (directGross.value <= 0) e.lines = "Add at least one line with an amount.";
	}
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const payload =
			mode.value === "wo"
				? {
						name: editingId.value || undefined,
						is_direct: 0,
						work_order: form.value.work_order,
						date: form.value.date,
						retention_percent: form.value.retention_percent,
				  }
				: {
						name: editingId.value || undefined,
						is_direct: 1,
						subcontractor: form.value.subcontractor,
						project: form.value.project,
						date: form.value.date,
						retention_percent: form.value.retention_percent,
						lines: form.value.lines
							.filter((l) => (l.scope || "").trim() || Number(l.amount) > 0)
							.map((l) => ({
								scope: l.scope,
								cost_code:
									l.cost_code && typeof l.cost_code === "object"
										? l.cost_code.label
										: l.cost_code || "",
								amount: Number(l.amount) || 0,
							})),
				  };
		const bill = await saveBill(payload);
		router.push(`/subcontractor-bills/${bill.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save bill", "error");
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const pageTitle = computed(() =>
	isEdit.value ? `Edit ${editingId.value}` : "New Subcontractor Bill"
);
const saveLabel = computed(() =>
	saving.value ? "Saving…" : isEdit.value ? "Save changes" : "Create Subcontractor bill"
);
const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractor Bills", to: "/subcontractor-bills" },
	...(isEdit.value
		? [
				{ label: editingId.value, to: `/subcontractor-bills/${editingId.value}` },
				{ label: "Edit" },
		  ]
		: [{ label: "New" }]),
]);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<!-- Mode toggle (create only) -->
			<div v-if="!isEdit" class="flex gap-2 mb-4">
				<button
					type="button"
					class="px-3 py-1.5 text-xs rounded-md border"
					:class="
						mode === 'wo'
							? 'bg-brand-600 text-white border-brand-600'
							: 'border-ink-200 text-ink-700'
					"
					@click="mode = 'wo'"
				>
					From Work Order
				</button>
				<button
					type="button"
					class="px-3 py-1.5 text-xs rounded-md border"
					:class="
						mode === 'direct'
							? 'bg-brand-600 text-white border-brand-600'
							: 'border-ink-200 text-ink-700'
					"
					@click="mode = 'direct'"
				>
					Direct (no work order)
				</button>
			</div>

			<!-- WORK ORDER MODE -->
			<template v-if="mode === 'wo'">
				<DeskSection title="Header" :cols="3">
					<DeskField label="Work order" required :error="errors.work_order">
						<DeskLinkPicker
							:model-value="form.work_order"
							doctype="Subcontractor Work Order"
							label-field="name"
							value-field="name"
							placeholder="Pick a work order…"
							:disabled="isEdit"
							@update:model-value="onWorkOrderChange"
						/>
					</DeskField>
					<DeskField label="Date" required
						><DeskInput v-model="form.date" type="date"
					/></DeskField>
					<DeskField label="Retention (%)">
						<DeskInput
							v-model.number="form.retention_percent"
							type="number"
							min="0"
							step="0.5"
						/>
					</DeskField>
				</DeskSection>

				<div
					v-if="woContext"
					class="mt-3 text-xs text-ink-600 bg-info-50 border border-info-100 rounded-md px-3 py-2"
				>
					{{ woContext.subcontractor_name }} · {{ woContext.project_name }} · This will
					be
					<span class="font-medium">Bill {{ woContext.next_ra_no }}</span>
				</div>

				<section class="mt-6">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">
						This period (derived from certified Measurement Books)
					</h3>
					<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
						<table class="w-full text-xs" style="min-width: 720px">
							<thead
								class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]"
							>
								<tr>
									<th class="text-left px-3 py-2">Scope</th>
									<th class="text-right px-3 py-2">Rate</th>
									<th class="text-right px-3 py-2">Measured</th>
									<th class="text-right px-3 py-2">Prev. billed</th>
									<th class="text-right px-3 py-2">This period</th>
									<th class="text-right px-3 py-2">Amount</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(l, i) in woLines"
									:key="i"
									class="border-t border-ink-100"
								>
									<td class="px-3 py-2 text-ink-900">{{ l.scope }}</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-700">
										{{ fmtINR(l.rate)
										}}<span class="text-ink-400">/{{ l.uom }}</span>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-info-700">
										{{
											Number(l.measured_qty_to_date).toLocaleString("en-IN")
										}}
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-500">
										{{ Number(l.previous_qty).toLocaleString("en-IN") }}
									</td>
									<td
										class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium"
									>
										{{ Number(l.this_period_qty).toLocaleString("en-IN") }}
									</td>
									<td class="px-3 py-2 text-right tabular-nums font-medium">
										{{ fmtINR(l.this_period_amount) }}
									</td>
								</tr>
								<tr v-if="!woLines.length">
									<td
										colspan="6"
										class="px-3 py-4 text-center text-ink-400 italic"
									>
										Pick a work order to derive this period's lines.
									</td>
								</tr>
							</tbody>
							<tfoot v-if="woLines.length">
								<tr class="bg-ink-50 border-t border-ink-200">
									<td colspan="5" class="px-3 py-1.5 text-right text-ink-600">
										Gross this period
									</td>
									<td class="px-3 py-1.5 text-right tabular-nums font-semibold">
										{{ fmtINR(woGross) }}
									</td>
								</tr>
								<tr class="bg-ink-50">
									<td colspan="5" class="px-3 py-1 text-right text-warning-700">
										Less retention ({{ form.retention_percent }}%)
									</td>
									<td class="px-3 py-1 text-right tabular-nums text-warning-700">
										−{{ fmtINR(retention) }}
									</td>
								</tr>
								<tr class="bg-ink-50 border-t border-ink-200">
									<td
										colspan="5"
										class="px-3 py-1.5 text-right font-semibold text-ink-900"
									>
										Net payable
									</td>
									<td
										class="px-3 py-1.5 text-right tabular-nums font-bold text-brand-700"
									>
										{{ fmtINR(netPayable) }}
									</td>
								</tr>
							</tfoot>
						</table>
					</div>
					<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">
						{{ errors.lines }}
					</p>
				</section>
			</template>

			<!-- DIRECT MODE -->
			<template v-else>
				<DeskSection title="Header" :cols="3">
					<DeskField label="Subcontractor" required :error="errors.subcontractor">
						<DeskLinkPicker
							v-model="form.subcontractor"
							doctype="Supplier"
							label-field="supplier_name"
							value-field="name"
							:filters="[['supplier_type', '=', 'Subcontractor']]"
							placeholder="Pick a subcontractor…"
						/>
					</DeskField>
					<DeskField
						label="Project"
						required
						hint="Sets the accounting company."
						:error="errors.project"
					>
						<DeskLinkPicker
							v-model="form.project"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							placeholder="Pick a project…"
						/>
					</DeskField>
					<DeskField label="Date" required
						><DeskInput v-model="form.date" type="date"
					/></DeskField>
					<DeskField label="Retention (%)">
						<DeskInput
							v-model.number="form.retention_percent"
							type="number"
							min="0"
							step="0.5"
						/>
					</DeskField>
				</DeskSection>

				<div
					class="mt-3 text-xs text-ink-600 bg-info-50 border border-info-100 rounded-md px-3 py-2"
				>
					Direct bill — for one-off / lump-sum charges. Taxes are applied on the detail
					page.
				</div>

				<section class="mt-6">
					<div class="flex items-center justify-between mb-2">
						<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
							Charge lines
						</h3>
						<button
							type="button"
							class="text-xs text-brand-700 hover:underline"
							@click="addLine"
						>
							+ Add line
						</button>
					</div>
					<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
						<table class="w-full text-xs" style="min-width: 560px">
							<thead
								class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]"
							>
								<tr>
									<th class="text-left px-3 py-2 min-w-[220px]">
										Scope / description
									</th>
									<th class="text-left px-3 py-2 min-w-[150px]">
										Cost code (optional)
									</th>
									<th class="text-right px-3 py-2 w-32">Amount</th>
									<th class="w-8"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(l, i) in form.lines"
									:key="i"
									class="border-t border-ink-100"
								>
									<td class="px-3 py-1">
										<input
											v-model="l.scope"
											class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
											placeholder="What is being billed"
										/>
									</td>
									<td class="px-3 py-1">
										<CostCodePicker
											v-model="l.cost_code"
											:project-id="form.project"
											placeholder="Pick code…"
										/>
									</td>
									<td class="px-3 py-1">
										<input
											v-model.number="l.amount"
											type="number"
											min="0"
											class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										/>
									</td>
									<td class="px-2 py-1 text-center">
										<button
											type="button"
											class="text-ink-400 hover:text-danger-600"
											@click="removeLine(i)"
										>
											✕
										</button>
									</td>
								</tr>
							</tbody>
							<tfoot>
								<tr class="bg-ink-50 border-t border-ink-200">
									<td colspan="2" class="px-3 py-1.5 text-right text-ink-600">
										Gross
									</td>
									<td class="px-3 py-1.5 text-right tabular-nums font-semibold">
										{{ fmtINR(directGross) }}
									</td>
									<td></td>
								</tr>
								<tr class="bg-ink-50">
									<td colspan="2" class="px-3 py-1 text-right text-warning-700">
										Less retention ({{ form.retention_percent }}%)
									</td>
									<td class="px-3 py-1 text-right tabular-nums text-warning-700">
										−{{ fmtINR(retention) }}
									</td>
									<td></td>
								</tr>
								<tr class="bg-ink-50 border-t border-ink-200">
									<td
										colspan="2"
										class="px-3 py-1.5 text-right font-semibold text-ink-900"
									>
										Net payable
									</td>
									<td
										class="px-3 py-1.5 text-right tabular-nums font-bold text-brand-700"
									>
										{{ fmtINR(netPayable) }}
									</td>
									<td></td>
								</tr>
							</tfoot>
						</table>
					</div>
					<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">
						{{ errors.lines }}
					</p>
				</section>
			</template>
		</DeskForm>
	</DeskPage>
</template>
