<script setup>
// Purchase Order detail — summary strip, read-only item lines (ordered vs received),
// and the native submittable lifecycle: Draft → Edit / Submit / Delete; Submitted →
// Create Receipt / Cancel; Cancelled → Amend / Delete.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getPurchaseOrder,
	submitPurchaseOrder,
	cancelPurchaseOrder,
	amendPurchaseOrder,
	deletePurchaseOrder,
} from "@/data/procurementApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();

const po = ref(null);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		po.value = await getPurchaseOrder(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load order", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => po.value?.state === "Draft");
const isSubmitted = computed(() => po.value?.state === "Submitted");
const isCancelled = computed(() => po.value?.state === "Cancelled");
const canReceive = computed(() => isSubmitted.value && (po.value?.per_received || 0) < 100);

function onEdit() {
	router.push(`/procurement/purchase-orders/${po.value.name}/edit`);
}
function onCreateReceipt() {
	router.push(`/procurement/receipts/new?po=${po.value.name}`);
}

async function onSubmit() {
	const ok = await confirmDialog({
		title: `Submit ${po.value.name}?`,
		message: `Submit this order to ${po.value.supplier_name || po.value.supplier} (${fmtINR(
			po.value.grand_total
		)})? It posts the order and locks the lines; a submitted order is amended, not edited.`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	busy.value = true;
	try {
		po.value = await submitPurchaseOrder(po.value.name);
		showToast("Order submitted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: `Cancel ${po.value.name}?`,
		message: "This cancels the order. It's blocked if receipts or bills exist against it.",
		confirmLabel: "Cancel order",
		cancelLabel: "Keep",
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		po.value = await cancelPurchaseOrder(po.value.name);
		showToast("Order cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onAmend() {
	busy.value = true;
	try {
		const res = await amendPurchaseOrder(po.value.name);
		showToast("Amended — a fresh draft was created.");
		router.push(`/procurement/purchase-orders/${res.name}`);
	} catch (err) {
		showToast(err.message || "Amend failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${po.value.name}?`,
		message: "This order and its items will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deletePurchaseOrder(po.value.name);
		router.push("/procurement/purchase-orders");
	} catch (err) {
		showToast(err.message || "Failed to delete order", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Purchase Orders", to: "/procurement/purchase-orders" },
	{ label: po.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="po"
		:title="po.name"
		:subtitle="`${po.supplier_name || po.supplier} · ${po.project_name || po.project}`"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<ProcurementStatusPill :status="po.status" class="self-center mr-1" />
			<button
				v-if="isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="onEdit"
			>
				Edit
			</button>
			<button
				v-if="isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onSubmit"
			>
				Submit
			</button>
			<button
				v-if="canReceive"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				title="Record a goods receipt against this order"
				@click="onCreateReceipt"
			>
				+ Create Receipt
			</button>
			<button
				v-if="isSubmitted"
				type="button"
				class="text-xs px-2.5 py-1 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onCancel"
			>
				Cancel
			</button>
			<button
				v-if="isCancelled"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				title="Create a fresh editable draft copy (the original stays cancelled)"
				@click="onAmend"
			>
				Amend
			</button>
			<button
				v-if="!isSubmitted"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
		</template>

		<div
			v-if="isDraft"
			class="mb-4 px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-md text-xs text-ink-600"
		>
			Draft — not sent to the supplier yet. Submit it to post the order.
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Supplier</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">
					{{ po.supplier_name || po.supplier }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Project</div>
				<DeskLink :to="`/projects/${po.project}`" class="text-sm">{{
					po.project_name || po.project
				}}</DeskLink>
				<div class="text-[10px] text-ink-500">
					{{
						po.schedule_date
							? "Required by " + fmtDate(po.schedule_date)
							: fmtDate(po.transaction_date)
					}}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Value</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(po.grand_total) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Received</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ Math.round(po.per_received || 0) }}%
				</div>
				<div class="text-[10px] text-ink-500">
					Billed {{ Math.round(po.per_billed || 0) }}%
				</div>
			</div>
		</div>

		<!-- Item lines -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Items</h3>
			</div>
			<table class="w-full text-xs" style="min-width: 700px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">Item</th>
						<th class="text-right px-3 py-2">Qty</th>
						<th class="text-left px-3 py-2">UOM</th>
						<th class="text-right px-3 py-2">Rate</th>
						<th class="text-right px-3 py-2">Amount</th>
						<th class="text-right px-3 py-2">Received</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(it, i) in po.items"
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
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ it.qty }}
						</td>
						<td class="px-3 py-2 text-ink-500">{{ it.uom || "—" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ fmtINR(it.rate) }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
							{{ fmtINR(it.amount) }}
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums font-medium"
							:class="
								(it.received_qty || 0) >= (it.qty || 0)
									? 'text-success-700'
									: 'text-ink-700'
							"
						>
							{{ it.received_qty || 0 }} / {{ it.qty }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-ink-200 bg-ink-50">
						<td
							colspan="4"
							class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
						>
							Total
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
						>
							{{ fmtINR(po.grand_total) }}
						</td>
						<td></td>
					</tr>
				</tfoot>
			</table>
		</section>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? "Loading order…" : "Purchase order not found." }}
	</div>
</template>
