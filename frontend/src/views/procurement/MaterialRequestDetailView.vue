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
import { usePermissions } from "@/composables/usePermissions";
import { useWorkflow } from "@/composables/useWorkflow";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const { canEdit, canSubmit, canCreate, canDelete } = usePermissions();

// Defer to an active Frappe Workflow on Material Request when one is configured — the
// transition that submits still runs the doc's on_submit, so MR submit side effects are
// preserved. With no workflow configured, the plain Submit / Cancel lifecycle shows.
const {
	active: wfActive,
	state: wfState,
	transitions: wfTransitions,
	refresh: refreshWorkflow,
	applyAction: applyWorkflowAction,
} = useWorkflow("Material Request");

const mr = ref(null);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		mr.value = await getMaterialRequest(props.id);
		await refreshWorkflow(props.id);
	} catch (err) {
		showToast(err.message || __("Failed to load request"), "error");
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
		title: __("Submit {0}?", [mr.value.name]),
		message: __(
			"Submit this request ({0})? It enters the procurement queue; a submitted request is cancelled, not edited.",
			[fmtINR(mr.value.total)]
		),
		confirmLabel: __("Submit"),
	});
	if (!ok) return;
	busy.value = true;
	try {
		mr.value = await submitMaterialRequest(mr.value.name);
		showToast(__("Request submitted."));
	} catch (err) {
		showToast(err.message || __("Submit failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: __("Cancel {0}?", [mr.value.name]),
		message: __(
			"Cancelling withdraws the request — it drops out of the procurement queue. Amend later to raise a corrected copy."
		),
		confirmLabel: __("Cancel request"),
		cancelLabel: __("Keep"),
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		mr.value = await cancelMaterialRequest(mr.value.name);
		showToast(__("Request cancelled."));
	} catch (err) {
		showToast(err.message || __("Cancel failed"), "error");
	} finally {
		busy.value = false;
	}
}
// Workflow-driven transition (only rendered when an active workflow governs Material Request).
// The transition that submits the doc runs on_submit, so any MR submit-time logic still fires.
async function onWorkflowAction(action) {
	busy.value = true;
	try {
		await applyWorkflowAction(mr.value.name, action);
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
		const res = await amendMaterialRequest(mr.value.name);
		showToast(__("Amended — a fresh draft was created."));
		router.push(`/procurement/material-requests/${res.name}`);
	} catch (err) {
		showToast(err.message || __("Amend failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete {0}?", [mr.value.name]),
		message: __("This request and its items will be removed permanently."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteMaterialRequest(mr.value.name);
		router.push("/procurement/material-requests");
	} catch (err) {
		showToast(err.message || __("Failed to delete request"), "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Material Requests"), to: "/procurement/material-requests" },
	{ label: mr.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="mr"
		:title="mr.name"
		:subtitle="
			__('{0} · requested {1}', [
				mr.project_name || mr.project,
				fmtDate(mr.transaction_date),
			])
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<ProcurementStatusPill :status="mr.status" class="self-center mr-1" />
			<span
				v-if="wfActive && wfState && wfState !== mr.status"
				class="self-center mr-1 text-[11px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200"
				>{{ __(wfState) }}</span
			>
			<button
				v-if="isDraft && canEdit('materialRequest')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="onEdit"
			>
				{{ __("Edit") }}
			</button>
			<!-- Plain docstatus lifecycle (no workflow configured) -->
			<button
				v-if="!wfActive && isDraft && canSubmit('materialRequest')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onSubmit"
			>
				{{ __("Submit") }}
			</button>
			<button
				v-if="canOrder && canCreate('purchaseOrder')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:title="__('Raise a Purchase Order from this request')"
				@click="onCreatePo"
			>
				{{ __("+ Create Purchase Order") }}
			</button>
			<button
				v-if="!wfActive && isSubmitted && canSubmit('materialRequest')"
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
				v-if="isCancelled && canCreate('materialRequest')"
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
				v-if="!isSubmitted && canDelete('materialRequest')"
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
			{{ __("Draft — not sent to the office yet. Submit it to enter the procurement queue.") }}
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
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Project") }}
				</div>
				<DeskLink :to="`/projects/${mr.project}`" class="text-sm">{{
					mr.project_name || mr.project
				}}</DeskLink>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Requested by") }}
				</div>
				<div class="flex items-center gap-1.5 mt-0.5">
					<UserAvatar :user-id="mr.requested_by" size="xs" show-name />
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Needed by") }}
				</div>
				<div class="text-sm text-ink-900 mt-0.5">
					{{ mr.schedule_date ? fmtDate(mr.schedule_date) : "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Estimated value") }}
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
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					{{ __("Items") }}
				</h3>
				<span class="text-[10px] text-ink-500"
					>{{ __("Ordered") }} {{ Math.round(mr.per_ordered || 0) }}%</span
				>
			</div>
			<table class="w-full text-xs" style="min-width: 640px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">{{ __("Item") }}</th>
						<th class="text-right px-3 py-2">{{ __("Qty") }}</th>
						<th class="text-left px-3 py-2">{{ __("UOM") }}</th>
						<th class="text-right px-3 py-2">{{ __("Est. rate") }}</th>
						<th class="text-right px-3 py-2">{{ __("Amount") }}</th>
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
		{{ loading ? __("Loading request…") : __("Material request not found.") }}
	</div>
</template>
