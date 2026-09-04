<script setup>
// Measurement Book detail — header strip + entries table + running
// measured total. Actions: Edit (Draft) / Certify / Revert to Draft /
// Delete. Certified books are the source of measured-to-date on the WO.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import {
	getMeasurementBook,
	certifyMeasurementBook,
	revertMeasurementBook,
} from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtDate } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
// The Site Engineer only raises MBs (create + read); edit/certify/delete are QS/PM actions.
// canEdit/canDelete resolve the persona's measurementBook caps (see roles.js).
const { canEdit, canDelete, canCreate, canSubmit } = usePermissions();

const mb = ref(null);
const woLines = ref([]);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		const data = await getMeasurementBook(props.id);
		woLines.value = data.wo_lines || [];
		delete data.wo_lines;
		mb.value = data;
	} catch (err) {
		showToast(err.message || "Failed to load measurement book", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => mb.value?.status === "Draft");
function scopeForLine(name) {
	return woLines.value.find((l) => l.name === name)?.scope || name || "—";
}
function entrySigned(e) {
	return (e.is_deduction ? -1 : 1) * (Number(e.quantity) || 0);
}

function onEdit() {
	router.push(`/measurement-books/${mb.value.name}/edit`);
}

async function onCertify() {
	const ok = await confirmDialog({
		title: `Certify ${mb.value.name}?`,
		message:
			"Certified measurement books become the source of measured-to-date on the work order. Revert to Draft to retract.",
		confirmLabel: "Certify",
	});
	if (!ok) return;
	busy.value = true;
	try {
		const res = await certifyMeasurementBook(mb.value.name);
		mb.value.status = res.status;
		mb.value.certified_by = res.certified_by;
		showToast("Measurement book certified.");
	} catch (err) {
		showToast(err.message || "Certify failed", "error");
	} finally {
		busy.value = false;
	}
}

async function onRevert() {
	busy.value = true;
	try {
		const res = await revertMeasurementBook(mb.value.name);
		mb.value.status = res.status;
		mb.value.certified_by = res.certified_by;
	} catch (err) {
		showToast(err.message || "Revert failed", "error");
	} finally {
		busy.value = false;
	}
}

// Once the MB is certified, its measured quantities can be billed — jump to the new
// Subcontractor Bill form seeded from this MB's Work Order (it derives the this-period
// lines from the WO's certified MBs).
function onCreateBill() {
	if (!mb.value?.work_order) return;
	router.push(`/subcontractor-bills/new?work_order=${mb.value.work_order}`);
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${mb.value.name}?`,
		message:
			"The entries are removed permanently. Measured-to-date on the work order will recompute against the remaining certified books.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Measurement Book", mb.value.name);
		router.push("/measurement-books");
	} catch (err) {
		showToast(err.message || "Failed to delete measurement book", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Measurement Books", to: "/measurement-books" },
	{ label: mb.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="mb"
		:title="mb.name"
		:subtitle="`${mb.project_name || mb.project} · ${mb.subcontractor_name || ''}`"
		:breadcrumbs="breadcrumbs"
		:status="mb.status"
	>
		<template #actions>
			<button
				v-if="isDraft && canEdit('measurementBook')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="onEdit"
			>
				Edit
			</button>
			<button
				v-if="isDraft && canSubmit('measurementBook')"
				type="button"
				class="text-xs px-2.5 py-1 border border-success-200 bg-success-50 hover:bg-success-100 text-success-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onCertify"
			>
				Certify
			</button>
			<button
				v-if="!isDraft && canSubmit('measurementBook')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onRevert"
			>
				Revert to Draft
			</button>
			<button
				v-if="!isDraft && mb.work_order && canCreate('subcontractorBill')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				title="Open the new Subcontractor Bill form pre-filled to this Work Order"
				@click="onCreateBill"
			>
				+ Create Subcontractor bill
			</button>
			<button
				v-if="canDelete('measurementBook')"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
		</template>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Project
				</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">
					{{ mb.project_name || mb.project }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Work order
				</div>
				<div class="text-sm mt-0.5">
					<DeskLink :to="`/subcontractor-work-orders/${encodeURIComponent(mb.work_order)}`">{{
						mb.work_order
					}}</DeskLink>
				</div>
				<div class="text-[10px] text-ink-500">
					{{ mb.subcontractor_name || "—"
					}}{{ mb.delivery_type ? ` · ${mb.delivery_type}` : "" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Date
				</div>
				<div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(mb.date) }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Measured by
				</div>
				<div class="text-sm text-ink-900 mt-0.5">
					<UserAvatar
						v-if="mb.measured_by"
						:user-id="mb.measured_by"
						size="xs"
						show-name
					/>
					<span v-else>—</span>
				</div>
				<div class="text-[10px] text-ink-500 mt-1 flex items-center gap-1">
					<span>Certified by</span>
					<UserAvatar
						v-if="mb.certified_by"
						:user-id="mb.certified_by"
						size="xs"
						show-name
					/>
					<span v-else>—</span>
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Measured total
				</div>
				<div class="text-base font-semibold text-info-700 tabular-nums mt-0.5">
					{{ Number(mb.measured_total || 0).toLocaleString("en-IN") }}
				</div>
				<div class="text-[10px] text-ink-500">
					across {{ (mb.entries || []).length }} entries
				</div>
			</div>
		</div>

		<!-- Entries table -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<div
				class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between"
			>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Entries
				</h3>
				<span class="text-[10px] text-ink-500 italic"
					>Quantity = Nos × L × B × D (or entered directly). Deduction rows
					subtract.</span
				>
			</div>
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">#</th>
						<th class="text-left px-3 py-2">Description</th>
						<th class="text-left px-3 py-2">Cost code</th>
						<th class="text-left px-3 py-2">WO line</th>
						<th class="text-right px-3 py-2">Nos</th>
						<th class="text-right px-3 py-2">L</th>
						<th class="text-right px-3 py-2">B</th>
						<th class="text-right px-3 py-2">D</th>
						<th class="text-right px-3 py-2">Qty</th>
						<th class="text-left px-3 py-2">UOM</th>
						<th class="text-center px-3 py-2">Deduction</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(e, idx) in mb.entries"
						:key="e.name"
						class="border-t border-ink-100 align-top"
						:class="e.is_deduction ? 'bg-danger-50/30' : ''"
					>
						<td class="px-3 py-2 text-ink-500">{{ idx + 1 }}</td>
						<td class="px-3 py-2 text-ink-900">{{ e.description }}</td>
						<td class="px-3 py-2">
							<span
								v-if="e.cost_code_label"
								class="text-[10px] font-mono px-1.5 py-0.5 rounded"
								:class="
									e.cost_code_type === 'Item'
										? 'bg-brand-50 text-brand-700'
										: 'bg-info-50 text-info-700'
								"
								:title="e.cost_code_label"
								>{{ e.cost_code_label }}</span
							>
							<span v-else class="text-ink-300">—</span>
						</td>
						<td class="px-3 py-2 text-ink-500 text-[11px]">
							{{ scopeForLine(e.work_order_line) }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ e.nos }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ e.length }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ e.breadth }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ e.depth }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
							{{ e.is_deduction ? "−" : ""
							}}{{ Number(e.quantity || 0).toLocaleString("en-IN") }}
						</td>
						<td class="px-3 py-2 text-ink-500">{{ e.uom }}</td>
						<td class="px-3 py-2 text-center">
							<span
								v-if="e.is_deduction"
								class="text-[10px] px-1.5 py-0.5 bg-danger-100 text-danger-700 rounded"
								>Deduct</span
							>
							<span
								v-else
								class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-500 rounded"
								>—</span
							>
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-ink-200 bg-ink-50">
						<td
							colspan="8"
							class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
						>
							Measured total
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-info-700"
						>
							{{ Number(mb.measured_total || 0).toLocaleString("en-IN") }}
						</td>
						<td colspan="2"></td>
					</tr>
				</tfoot>
			</table>
		</section>

		<!-- Remarks -->
		<section
			v-if="mb.remarks"
			class="mt-4 px-4 py-3 bg-ink-50 border border-ink-200 rounded-md"
		>
			<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">
				Remarks
			</div>
			<div class="text-sm text-ink-800 whitespace-pre-line">{{ mb.remarks }}</div>
		</section>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? "Loading measurement book…" : "Measurement book not found." }}
	</div>
</template>
