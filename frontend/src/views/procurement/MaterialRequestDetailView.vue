<script setup>
// Material Request detail — summary strip, read-only item lines, and the native
// submittable lifecycle: Draft → Edit / Submit / Delete; Submitted → Create
// Purchase Order / Cancel; Cancelled → Amend / Delete. State IS the docstatus.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getMaterialRequest,
	submitMaterialRequest,
	cancelMaterialRequest,
	amendMaterialRequest,
	deleteMaterialRequest,
} from "@/data/procurementApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();

const mr = ref(null);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		mr.value = await getMaterialRequest(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load request", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => mr.value?.state === "Draft");
const isSubmitted = computed(() => mr.value?.state === "Submitted");
const isCancelled = computed(() => mr.value?.state === "Cancelled");
const canOrder = computed(() => isSubmitted.value && (mr.value?.per_ordered || 0) < 100);

function onEdit() {
	router.push(`/procurement/material-requests/${mr.value.name}/edit`);
}
function onCreatePo() {
	router.push(`/procurement/purchase-orders/new?mr=${mr.value.name}`);
}

async function onSubmit() {
	const ok = await confirmDialog({
		title: `Submit ${mr.value.name}?`,
		message: `Submit this request (${fmtINR(
			mr.value.total
		)})? It enters the procurement queue; a submitted request is cancelled, not edited.`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	busy.value = true;
	try {
		mr.value = await submitMaterialRequest(mr.value.name);
		showToast("Request submitted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: `Cancel ${mr.value.name}?`,
		message:
			"Cancelling withdraws the request — it drops out of the procurement queue. Amend later to raise a corrected copy.",
		confirmLabel: "Cancel request",
		cancelLabel: "Keep",
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		mr.value = await cancelMaterialRequest(mr.value.name);
		showToast("Request cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onAmend() {
	busy.value = true;
	try {
		const res = await amendMaterialRequest(mr.value.name);
		showToast("Amended — a fresh draft was created.");
		router.push(`/procurement/material-requests/${res.name}`);
	} catch (err) {
		showToast(err.message || "Amend failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${mr.value.name}?`,
		message: "This request and its items will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteMaterialRequest(mr.value.name);
		router.push("/procurement/material-requests");
	} catch (err) {
		showToast(err.message || "Failed to delete request", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Material Requests", to: "/procurement/material-requests" },
	{ label: mr.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="mr"
		:title="mr.name"
		:subtitle="`${mr.project_name || mr.project} · requested ${fmtDate(mr.transaction_date)}`"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<ProcurementStatusPill :status="mr.status" class="self-center mr-1" />
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
				v-if="canOrder"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				title="Raise a Purchase Order from this request"
				@click="onCreatePo"
			>
				+ Create Purchase Order
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
			Draft — not sent to the office yet. Submit it to enter the procurement queue.
		</div>
		<div
			v-if="isCancelled"
			class="mb-4 px-4 py-2.5 bg-ink-100 border border-ink-200 rounded-md text-xs text-ink-600"
		>
			This request is <span class="font-semibold">cancelled</span> — it's out of the
			procurement queue. Click <span class="font-medium">Amend</span> to raise a corrected
			draft.
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Project</div>
				<DeskLink :to="`/projects/${mr.project}`" class="text-sm">{{
					mr.project_name || mr.project
				}}</DeskLink>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Requested by</div>
				<div class="flex items-center gap-1.5 mt-0.5">
					<UserAvatar :user-id="mr.requested_by" size="xs" show-name />
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Needed by</div>
				<div class="text-sm text-ink-900 mt-0.5">
					{{ mr.schedule_date ? fmtDate(mr.schedule_date) : "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					Estimated value
				</div>
				<div class="text-sm font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(mr.total) }}
				</div>
			</div>
		</div>

		<!-- Item lines -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<div
				class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between"
			>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Items</h3>
				<span class="text-[10px] text-ink-500"
					>Ordered {{ Math.round(mr.per_ordered || 0) }}%</span
				>
			</div>
			<table class="w-full text-xs" style="min-width: 640px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">Item</th>
						<th class="text-right px-3 py-2">Qty</th>
						<th class="text-left px-3 py-2">UOM</th>
						<th class="text-right px-3 py-2">Est. rate</th>
						<th class="text-right px-3 py-2">Amount</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(it, i) in mr.items"
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
							{{ it.rate ? fmtINR(it.rate) : "—" }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
							{{ it.amount ? fmtINR(it.amount) : "—" }}
						</td>
					</tr>
				</tbody>
			</table>
		</section>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? "Loading request…" : "Material request not found." }}
	</div>
</template>
