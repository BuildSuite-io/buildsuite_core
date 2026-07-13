<script setup>
// Subcontractor Work Order detail — summary strip, read-only SOV table,
// terms, and workflow action buttons (Submit for Approval / Approve /
// Reject / Start / Close, whatever the approval workflow offers the
// current user). Measurement Books + RA bills land in a later pass.

import { computed, ref, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { getWorkOrder, applyWoAction } from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());

const wo = ref(null);
const actions = ref([]);
const loading = ref(true);
const busy = ref(false);

async function load() {
	loading.value = true;
	try {
		const data = await getWorkOrder(props.id);
		actions.value = data.actions || [];
		delete data.actions;
		wo.value = data;
	} catch (err) {
		showToast(err.message || "Failed to load work order", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => wo.value?.status === "Draft");

async function onAction(action) {
	const ok = await confirmDialog({
		title: `${action}?`,
		message: `Apply "${action}" to ${wo.value.name}? This moves the work order to its next approval state.`,
		confirmLabel: action,
	});
	if (!ok) return;
	busy.value = true;
	try {
		const res = await applyWoAction(wo.value.name, action);
		wo.value.status = res.status;
		actions.value = res.actions || [];
		showToast(`Work order is now ${res.status}.`);
	} catch (err) {
		showToast(err.message || "Action failed", "error");
	} finally {
		busy.value = false;
	}
}

function onEdit() {
	router.push(`/subcontractor-work-orders/${wo.value.name}/edit`);
}

async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete ${wo.value.name}?`,
		message: "This work order and its schedule of values will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Subcontractor Work Order", wo.value.name);
		router.push("/subcontractor-work-orders");
	} catch (err) {
		showToast(err.message || "Failed to delete work order", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Work Orders", to: "/subcontractor-work-orders" },
	{ label: wo.value?.name || props.id },
]);

const tab = ref("sov");
const tabs = [
	{ id: "sov", label: "Schedule of values" },
	{ id: "terms", label: "Terms" },
];
</script>

<template>
	<DeskPage
		v-if="wo"
		:title="wo.subcontractor_name || wo.name"
		:subtitle="`${wo.name} · ${wo.project}`"
		:breadcrumbs="breadcrumbs"
		:status="wo.delivery_type ? [wo.status, wo.delivery_type] : wo.status"
	>
		<template #actions>
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
				v-for="action in actions"
				:key="action"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onAction(action)"
			>
				{{ action }}
			</button>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
		</template>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Subcontractor
				</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">
					{{ wo.subcontractor_name || "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Project
				</div>
				<div class="text-sm text-ink-900 mt-0.5 truncate">{{ wo.project }}</div>
				<div class="text-[10px] text-ink-500">{{ fmtDate(wo.date) }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Total value
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(wo.total_value) }}
				</div>
				<div class="text-[10px] text-ink-500">Retention {{ wo.retention_percent }}%</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Status
				</div>
				<div class="mt-1"><StatusBadge :status="wo.status" /></div>
			</div>
		</div>

		<!-- Tab strip -->
		<div
			class="border-b border-ink-200 mb-4 flex gap-4 text-xs overflow-x-auto overflow-y-hidden"
		>
			<button
				v-for="t in tabs"
				:key="t.id"
				type="button"
				class="pb-2 -mb-px border-b-2 transition-colors whitespace-nowrap"
				:class="
					tab === t.id
						? 'border-brand-600 text-brand-700 font-medium'
						: 'border-transparent text-ink-500 hover:text-ink-800'
				"
				@click="tab = t.id"
			>
				{{ t.label }}
			</button>
		</div>

		<!-- Schedule of values (read-only) -->
		<section
			v-if="tab === 'sov'"
			class="bg-white border border-ink-200 rounded-lg overflow-x-auto"
		>
			<div
				class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between"
			>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Schedule of values
				</h3>
				<span v-if="wo.delivery_type" class="text-[10px] text-ink-500 italic">{{
					wo.delivery_type
				}}</span>
			</div>
			<table class="w-full text-xs" style="min-width: 640px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">Scope</th>
						<th class="text-left px-3 py-2">Cost code</th>
						<th class="text-right px-3 py-2">Qty</th>
						<th class="text-left px-3 py-2">UOM</th>
						<th class="text-right px-3 py-2">Rate</th>
						<th class="text-right px-3 py-2">Line value</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="line in wo.lines"
						:key="line.name"
						class="border-t border-ink-100 align-top"
					>
						<td class="px-3 py-2 text-ink-900">{{ line.scope }}</td>
						<td class="px-3 py-2">
							<span
								v-if="line.cost_code_label"
								class="text-[10px] font-mono px-1.5 py-0.5 rounded"
								:class="
									line.cost_code_type === 'Item'
										? 'bg-brand-50 text-brand-700'
										: 'bg-info-50 text-info-700'
								"
								:title="line.cost_code_label"
								>{{ line.cost_code_label }}</span
							>
							<span v-else class="text-ink-300">—</span>
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ line.qty }}
						</td>
						<td class="px-3 py-2 text-ink-500">{{ line.uom || "—" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ fmtINR(line.rate) }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
							{{ fmtINR(line.amount) }}
						</td>
					</tr>
				</tbody>
				<tfoot>
					<tr class="border-t-2 border-ink-200 bg-ink-50">
						<td
							colspan="5"
							class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
						>
							WO total
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
						>
							{{ fmtINR(wo.total_value) }}
						</td>
					</tr>
				</tfoot>
			</table>
		</section>

		<!-- Terms (read-only; edit via the WO form) -->
		<section v-if="tab === 'terms'">
			<div class="flex items-center justify-between mb-2 gap-3">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Terms &amp; conditions
				</h3>
				<button
					v-if="isDraft"
					type="button"
					class="text-xs text-brand-700 hover:underline"
					@click="onEdit"
				>
					Edit in work order
				</button>
			</div>
			<div
				v-if="wo.terms"
				class="bg-white border border-ink-200 rounded-lg p-4 text-xs text-ink-800 whitespace-pre-line leading-relaxed"
			>
				{{ wo.terms }}
			</div>
			<div v-else class="text-xs text-ink-400 italic">
				No terms set. Edit the work order to import a template or type custom terms.
			</div>
		</section>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? "Loading work order…" : "Work order not found." }}
	</div>
</template>
