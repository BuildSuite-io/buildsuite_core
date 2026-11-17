<script setup>
// Supplier Quotation detail — summary strip, read-only lines (rate, lead time; a line with no
// rate reads Not quoted), the taxes, and the native submittable lifecycle: Draft → Edit /
// Submit / Delete; Submitted → Compare / Create Purchase Order / Cancel; Cancelled → Amend /
// Delete. A submitted quotation joins the comparison on its request.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getSupplierQuotation,
	submitSupplierQuotation,
	cancelSupplierQuotation,
	amendSupplierQuotation,
	deleteSupplierQuotation,
} from "@/data/rfqApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import { usePermissions } from "@/composables/usePermissions";
import { useWorkflow } from "@/composables/useWorkflow";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const { canEdit, canSubmit, canCreate, canDelete } = usePermissions();

const {
	active: wfActive,
	state: wfState,
	transitions: wfTransitions,
	refresh: refreshWorkflow,
	applyAction: applyWorkflowAction,
} = useWorkflow("Supplier Quotation");

const sq = ref(null);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		sq.value = await getSupplierQuotation(props.id);
		await refreshWorkflow(props.id);
	} catch (err) {
		showToast(err.message || __("Failed to load quotation"), "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => sq.value?.state === "Draft");
const isSubmitted = computed(() => sq.value?.state === "Submitted");
const isCancelled = computed(() => sq.value?.state === "Cancelled");
const isExpired = computed(() => sq.value?.status === "Expired");
// Something the supplier priced is still to be ordered (ERPNext's own Ordered status says not).
const canOrder = computed(() => isSubmitted.value && sq.value?.status !== "Ordered");

function onEdit() {
	router.push(`/procurement/supplier-quotations/${sq.value.name}/edit`);
}
function onCompare() {
	router.push(
		`/procurement/supplier-quotation-comparison?rfq=${encodeURIComponent(
			sq.value.request_for_quotation
		)}`
	);
}
function onCreatePo() {
	router.push(`/procurement/purchase-orders/new?sq=${encodeURIComponent(sq.value.name)}`);
}

async function onSubmit() {
	const ok = await confirmDialog({
		title: __("Submit {0}?", [sq.value.name]),
		message: sq.value.request_for_quotation
			? __(
					"Submit this quotation from {0} ({1} net)? It then counts in the comparison and marks the request as answered by this supplier.",
					[sq.value.supplier_name, fmtINR(sq.value.total)]
			  )
			: __("Submit this quotation from {0} ({1} net)?", [
					sq.value.supplier_name,
					fmtINR(sq.value.total),
			  ]),
		confirmLabel: __("Submit"),
	});
	if (!ok) return;
	busy.value = true;
	try {
		sq.value = await submitSupplierQuotation(sq.value.name);
		showToast(__("Quotation submitted."));
	} catch (err) {
		showToast(err.message || __("Submit failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: __("Cancel {0}?", [sq.value.name]),
		message: __(
			"A cancelled quotation leaves the comparison. It's blocked while a purchase order raised from it is live."
		),
		confirmLabel: __("Cancel quotation"),
		cancelLabel: __("Keep"),
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		sq.value = await cancelSupplierQuotation(sq.value.name);
		showToast(__("Quotation cancelled."));
	} catch (err) {
		showToast(err.message || __("Cancel failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onWorkflowAction(action) {
	busy.value = true;
	try {
		await applyWorkflowAction(sq.value.name, action);
		await load();
		showToast(__("{0} done.", [action]));
	} catch (err) {
		showToast(err.message || __("Action failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onAmend() {
	busy.value = true;
	try {
		const res = await amendSupplierQuotation(sq.value.name);
		showToast(__("Amended — a fresh draft was created."));
		router.push(`/procurement/supplier-quotations/${res.name}`);
	} catch (err) {
		showToast(err.message || __("Amend failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete {0}?", [sq.value.name]),
		message: __("This quotation and its items will be removed permanently."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteSupplierQuotation(sq.value.name);
		router.push("/procurement/supplier-quotations");
	} catch (err) {
		showToast(err.message || __("Failed to delete quotation"), "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Supplier Quotations"), to: "/procurement/supplier-quotations" },
	{ label: sq.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="sq"
		:title="sq.name"
		:subtitle="`${sq.supplier_name || sq.supplier} · ${fmtDate(sq.transaction_date)}`"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<ProcurementStatusPill
				:status="sq.status"
				class="self-center mr-1"
				data-test="sq-status"
			/>
			<span
				v-if="wfActive && wfState && wfState !== sq.status"
				class="self-center mr-1 text-[11px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200"
				>{{ __(wfState) }}</span
			>
			<button
				v-if="isDraft && canEdit('supplierQuotation')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="onEdit"
			>
				{{ __("Edit") }}
			</button>
			<button
				v-if="isSubmitted && sq.request_for_quotation"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="onCompare"
			>
				{{ __("Compare") }}
			</button>
			<!-- Plain docstatus lifecycle (no workflow configured) -->
			<button
				v-if="!wfActive && isDraft && canSubmit('supplierQuotation')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				data-test="sq-submit"
				@click="onSubmit"
			>
				{{ __("Submit") }}
			</button>
			<button
				v-if="canOrder && canCreate('purchaseOrder')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:title="__('Raise a Purchase Order at the quoted rates')"
				data-test="sq-create-po"
				@click="onCreatePo"
			>
				+ {{ __("Create Purchase Order") }}
			</button>
			<button
				v-if="!wfActive && isSubmitted && canSubmit('supplierQuotation')"
				type="button"
				class="text-xs px-2.5 py-1 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onCancel"
			>
				{{ __("Cancel") }}
			</button>
			<!-- Workflow transitions (active workflow) — role- and state-filtered by the backend -->
			<button
				v-for="t in wfActive ? wfTransitions : []"
				:key="t.action"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onWorkflowAction(t.action)"
			>
				{{ __(t.action) }}
			</button>
			<button
				v-if="isCancelled && canCreate('supplierQuotation')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				:title="__('Create a fresh editable draft copy (the original stays cancelled)')"
				@click="onAmend"
			>
				{{ __("Amend") }}
			</button>
			<button
				v-if="!isSubmitted && canDelete('supplierQuotation')"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				{{ __("Delete") }}
			</button>
		</template>

		<div
			v-if="isDraft"
			class="mb-4 px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-md text-xs text-ink-600"
		>
			{{ __("Draft. It joins the comparison once submitted.") }}
		</div>
		<div
			v-if="isExpired"
			class="mb-4 px-4 py-2.5 bg-warning-50 border border-warning-200 rounded-md text-xs text-warning-700"
		>
			{{
				__(
					"This quotation's validity ended on {0}. Confirm the rates with the supplier before ordering.",
					[fmtDate(sq.valid_till)]
				)
			}}
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Supplier") }}
				</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">
					{{ sq.supplier_name || sq.supplier }}
				</div>
				<div v-if="sq.quotation_number" class="text-[10px] text-ink-500">
					{{ __("Ref {0}", [sq.quotation_number]) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Project") }}
				</div>
				<DeskLink :to="`/projects/${sq.project}`" class="text-sm">{{
					sq.project_name || sq.project
				}}</DeskLink>
				<div v-if="sq.request_for_quotation" class="mt-0.5">
					<DeskLink
						:to="`/procurement/rfqs/${sq.request_for_quotation}`"
						class="text-[11px]"
						>{{ sq.request_for_quotation }}</DeskLink
					>
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Valid till") }}
				</div>
				<div class="text-sm text-ink-900 mt-0.5">
					{{ sq.valid_till ? fmtDate(sq.valid_till) : "—" }}
				</div>
				<div v-if="sq.payment_terms" class="text-[10px] text-ink-500">
					{{ sq.payment_terms }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Net value") }}
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(sq.total) }}
				</div>
				<div
					v-if="sq.total_taxes_and_charges"
					class="text-[10px] text-ink-500 tabular-nums"
				>
					{{ __("{0} with tax", [fmtINR(sq.grand_total)]) }}
				</div>
			</div>
		</div>

		<!-- Item lines -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					{{ __("Items") }}
				</h3>
			</div>
			<table class="w-full text-xs" style="min-width: 700px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">{{ __("Item") }}</th>
						<th class="text-right px-3 py-2">{{ __("Qty") }}</th>
						<th class="text-left px-3 py-2">{{ __("UOM") }}</th>
						<th class="text-right px-3 py-2">{{ __("Rate") }}</th>
						<th class="text-right px-3 py-2">{{ __("Lead time") }}</th>
						<th class="text-right px-3 py-2">{{ __("Amount") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(it, i) in sq.items"
						:key="i"
						class="border-t border-ink-100 align-top"
					>
						<td class="px-3 py-2">
							<span class="text-ink-900">{{ it.item_name || it.item_code }}</span>
							<span
								v-if="it.item_name && it.item_code !== it.item_name"
								class="text-[10px] font-mono text-ink-400 ml-1.5"
								>{{ it.item_code }}</span
							>
							<span
								v-if="it.description"
								class="block text-[11px] text-ink-500 mt-0.5"
								>{{ it.description }}</span
							>
							<span
								v-if="it.cost_code && it.cost_code.label"
								class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded mt-1"
								:class="
									it.cost_code.type === 'item'
										? 'bg-brand-50 text-brand-700'
										: 'bg-info-50 text-info-700'
								"
								>{{ it.cost_code.label }}</span
							>
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ it.qty }}
						</td>
						<td class="px-3 py-2 text-ink-500">{{ it.uom || "—" }}</td>
						<td
							class="px-3 py-2 text-right tabular-nums"
							:class="it.rate ? 'text-ink-700' : 'text-ink-400'"
						>
							{{ it.rate ? fmtINR(it.rate) : __("Not quoted") }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-600">
							{{
								it.lead_time_days != null
									? __("{0} days", [it.lead_time_days])
									: "—"
							}}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
							{{ it.rate ? fmtINR(it.amount) : "—" }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-ink-200 bg-ink-50">
						<td
							colspan="5"
							class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
						>
							{{ __("Net total") }}
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
						>
							{{ fmtINR(sq.total) }}
						</td>
					</tr>
					<tr v-for="(t, i) in sq.taxes" :key="i" class="bg-ink-50">
						<td colspan="5" class="px-3 py-1.5 text-right text-xs text-ink-600">
							{{ t.description }}<template v-if="t.rate"> @ {{ t.rate }}%</template>
						</td>
						<td class="px-3 py-1.5 text-right tabular-nums text-ink-700">
							{{ fmtINR(t.tax_amount) }}
						</td>
					</tr>
					<tr v-if="sq.taxes.length" class="border-t border-ink-200 bg-ink-50">
						<td
							colspan="5"
							class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
						>
							{{ __("Grand total") }}
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
						>
							{{ fmtINR(sq.grand_total) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</section>

		<section
			v-if="sq.notes"
			class="bg-white border border-ink-200 rounded-lg overflow-hidden mt-4"
		>
			<header class="px-4 py-2 bg-ink-50 border-b border-ink-200">
				<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
					{{ __("Supplier's notes") }}
				</div>
			</header>
			<p class="px-4 py-3 text-xs text-ink-700 whitespace-pre-line">{{ sq.notes }}</p>
		</section>

		<section
			v-if="sq.purchase_orders && sq.purchase_orders.length"
			class="bg-white border border-ink-200 rounded-lg overflow-x-auto mt-4"
			data-test="sq-orders"
		>
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					{{ __("Purchase orders from this quotation") }}
				</h3>
			</div>
			<table class="w-full text-xs">
				<tbody>
					<tr
						v-for="p in sq.purchase_orders"
						:key="p.name"
						class="border-t border-ink-100 first:border-t-0 cursor-pointer hover:bg-ink-50"
						@click="router.push(`/procurement/purchase-orders/${p.name}`)"
					>
						<td class="px-3 py-2.5 font-mono text-[11px] text-ink-600">
							{{ p.name }}
						</td>
						<td class="px-3 py-2.5"><ProcurementStatusPill :status="p.status" /></td>
						<td class="px-3 py-2.5 text-right tabular-nums text-ink-900 font-medium">
							{{ fmtINR(p.grand_total) }}
						</td>
					</tr>
				</tbody>
			</table>
		</section>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? __("Loading quotation…") : __("Supplier quotation not found.") }}
	</div>
</template>
