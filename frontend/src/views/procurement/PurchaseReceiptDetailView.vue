<script setup>
// Purchase Receipt detail — summary strip, read-only received lines, and the native
// submittable lifecycle: Draft → Edit / Submit / Delete; Submitted → Cancel;
// Cancelled → Amend / Delete. Submitting posts stock; cancelling reverses it.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getPurchaseReceipt,
	submitPurchaseReceipt,
	cancelPurchaseReceipt,
	amendPurchaseReceipt,
	deletePurchaseReceipt,
} from "@/data/procurementApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();

const pr = ref(null);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		pr.value = await getPurchaseReceipt(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load receipt", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => pr.value?.state === "Draft");
const isSubmitted = computed(() => pr.value?.state === "Submitted");
const isCancelled = computed(() => pr.value?.state === "Cancelled");
const total = computed(() =>
	(pr.value?.items || []).reduce((a, it) => a + (it.received_qty || 0) * (it.rate || 0), 0)
);

function onEdit() {
	router.push(`/procurement/receipts/${pr.value.name}/edit`);
}

async function onSubmit() {
	const ok = await confirmDialog({
		title: `Submit ${pr.value.name}?`,
		message:
			"Submitting posts the goods into stock and updates the purchase order's received quantity.",
		confirmLabel: "Submit",
	});
	if (!ok) return;
	busy.value = true;
	try {
		pr.value = await submitPurchaseReceipt(pr.value.name);
		showToast("Receipt submitted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: `Cancel ${pr.value.name}?`,
		message:
			"Cancelling reverses the receipt — the material leaves stock and the order's received quantity drops back.",
		confirmLabel: "Cancel receipt",
		cancelLabel: "Keep",
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		pr.value = await cancelPurchaseReceipt(pr.value.name);
		showToast("Receipt cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onAmend() {
	busy.value = true;
	try {
		const res = await amendPurchaseReceipt(pr.value.name);
		showToast("Amended — a fresh draft was created.");
		router.push(`/procurement/receipts/${res.name}`);
	} catch (err) {
		showToast(err.message || "Amend failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${pr.value.name}?`,
		message: "This receipt will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deletePurchaseReceipt(pr.value.name);
		router.push("/procurement/receipts");
	} catch (err) {
		showToast(err.message || "Failed to delete receipt", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Purchase Receipts", to: "/procurement/receipts" },
	{ label: pr.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="pr"
		:title="pr.name"
		:subtitle="`${pr.supplier_name || pr.supplier} · ${pr.project_name || pr.project}`"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<ProcurementStatusPill :status="pr.status" class="self-center mr-1" />
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
			Draft — not posted to stock yet. Submit it to record the goods into the warehouse.
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Supplier</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">
					{{ pr.supplier_name || pr.supplier }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Project</div>
				<DeskLink :to="`/projects/${pr.project}`" class="text-sm">{{
					pr.project_name || pr.project
				}}</DeskLink>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Received on</div>
				<div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(pr.posting_date) }}</div>
				<div v-if="pr.purchase_order" class="text-[10px] text-ink-500">
					against
					<DeskLink
						:to="`/procurement/purchase-orders/${pr.purchase_order}`"
						class="font-mono"
						>{{ pr.purchase_order }}</DeskLink
					>
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Value received</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(total) }}
				</div>
			</div>
		</div>

		<!-- Received lines -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<div
				class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between"
			>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Items received
				</h3>
				<span class="text-[10px] text-ink-500">Into {{ pr.warehouse || "—" }}</span>
			</div>
			<table class="w-full text-xs" style="min-width: 620px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">Item</th>
						<th class="text-left px-3 py-2">UOM</th>
						<th class="text-right px-3 py-2">Rate</th>
						<th class="text-right px-3 py-2">Received</th>
						<th class="text-right px-3 py-2">Amount</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(it, i) in pr.items" :key="i" class="border-t border-ink-100">
						<td class="px-3 py-2 text-ink-900">{{ it.item_name || it.item_code }}</td>
						<td class="px-3 py-2 text-ink-500">{{ it.uom || "—" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ fmtINR(it.rate) }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-success-700 font-medium">
							{{ it.received_qty }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
							{{ fmtINR((it.received_qty || 0) * (it.rate || 0)) }}
						</td>
					</tr>
				</tbody>
			</table>
		</section>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? "Loading receipt…" : "Purchase receipt not found." }}
	</div>
</template>
