<script setup>
// Material Consumption detail — view / edit / delete, draft only.
// A posted entry is read-only. Submit comes from a Frappe Workflow, if a site
// configures one: useWorkflow renders its transitions as buttons.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { useWorkflow } from "@/composables/useWorkflow";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { getMaterialConsumption } from "@/data/materialConsumptionApi";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { showToast } from "@/utils/appToast";
import { fmtDate } from "@/utils/format";
import { isPermissionDenied } from "@/utils/frappeError";
import DeskPage from "@/components/desk/DeskPage.vue";
import AccessDenied from "@/components/AccessDenied.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import FrappeUserBadge from "@/components/FrappeUserBadge.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { projectLabel } = useProjectOptions();
const {
	active: wfActive,
	state: wfState,
	transitions: wfTransitions,
	refresh: refreshWorkflow,
	applyAction: applyWorkflowAction,
} = useWorkflow("Stock Entry");

const DOCSTATUS_LABELS = { 0: "Draft", 1: "Submitted", 2: "Cancelled" };

const doc = ref(null);
const loading = ref(true);
const loadError = ref(null);

const accessDenied = computed(() => isPermissionDenied(loadError.value));
const isDraft = computed(() => doc.value?.docstatus === 0);
// A workflow owns the status label once active.
const stateLabel = computed(() =>
	wfActive.value
		? wfState.value || DOCSTATUS_LABELS[doc.value?.docstatus]
		: DOCSTATUS_LABELS[doc.value?.docstatus] || "Draft"
);
const busy = ref(false);

// The API returns the child rows; a list read would not.
async function load() {
	loading.value = true;
	loadError.value = null;
	try {
		doc.value = await getMaterialConsumption(props.id);
		await refreshWorkflow(props.id);
	} catch (err) {
		doc.value = null;
		loadError.value = err;
	} finally {
		loading.value = false;
	}
}
// Not onMounted — the router reuses this component when only :id changes.
watch(() => props.id, load, { immediate: true });

async function onWorkflowAction(action) {
	busy.value = true;
	try {
		await applyWorkflowAction(props.id, action);
		await load();
		showToast(`${action} done.`);
	} catch (err) {
		showToast(err.message || "Action failed", "error");
	} finally {
		busy.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: "Delete consumption?",
		message: `${props.id} will be removed permanently.`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Stock Entry", props.id);
		showToast("Consumption deleted");
		router.push("/material-consumption");
	} catch (err) {
		showToast(err.message || "Failed to delete", "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Material Consumption", to: "/material-consumption" },
	{ label: props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.name"
		:subtitle="`Recorded ${fmtDate(doc.posting_date)} · ${doc.purpose || 'Material Issue'}`"
		:status="stateLabel"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="!wfActive && isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="router.push(`/material-consumption/${doc.name}/edit`)"
			>
				Edit
			</button>
			<button
				v-if="!wfActive && isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>

			<!-- One button per allowed transition. -->
			<button
				v-for="t in wfActive ? wfTransitions : []"
				:key="t.action"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onWorkflowAction(t.action)"
			>
				{{ t.action }}
			</button>
		</template>

		<div
			class="mb-4 px-3 py-2 bg-ink-50 border border-ink-200 text-xs text-ink-600"
			style="border-radius: 6px"
		>
			{{
				isDraft
					? "Draft — nothing has been deducted from site stock yet."
					: `This entry is ${stateLabel.toLowerCase()} and can no longer be edited here.`
			}}
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-3 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Project
				</div>
				<DeskLink v-if="doc.project" :to="`/projects/${doc.project}`" class="text-sm">
					{{ doc.project_name || projectLabel(doc.project) || doc.project }}
				</DeskLink>
				<div v-else class="text-sm text-ink-400 mt-0.5">—</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Cost code
				</div>
				<span
					v-if="doc.cost_code_label"
					class="inline-block mt-1 text-[11px] px-2 py-0.5 bg-info-50 text-info-700"
					style="border-radius: 4px"
					>{{ doc.cost_code_label }}</span
				>
				<div v-else class="text-sm text-ink-400 mt-0.5">Not cost-coded</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Recorded by
				</div>
				<div class="mt-0.5">
					<FrappeUserBadge v-if="doc.owner" :user-id="doc.owner" size="xs" />
					<span v-else class="text-sm text-ink-400">—</span>
				</div>
			</div>
		</div>

		<div class="border border-ink-200 overflow-hidden" style="border-radius: 6px">
			<div
				class="grid grid-cols-[1fr_140px_120px] gap-2 bg-ink-50 border-b border-ink-200 px-3 py-2 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
			>
				<span>Item</span>
				<span class="text-right">Qty consumed</span>
				<span>UOM</span>
			</div>
			<div
				v-for="row in doc.items"
				:key="row.item_code"
				class="grid grid-cols-[1fr_140px_120px] gap-2 px-3 py-2 border-b border-ink-100 last:border-0 text-sm"
			>
				<span class="text-ink-900">{{ row.item_name || row.item_code }}</span>
				<span class="text-right tabular-nums font-medium text-ink-900">{{ row.qty }}</span>
				<span class="text-ink-500 text-xs pt-0.5">{{ row.uom || "—" }}</span>
			</div>
			<div
				v-if="!doc.items.length"
				class="px-3 py-6 text-center text-xs text-ink-400 italic"
			>
				No items on this entry.
			</div>
		</div>
	</DeskPage>

	<AccessDenied v-else-if="accessDenied" />

	<div v-else-if="!loading" class="desk-page">
		<p class="text-sm text-ink-500">
			Consumption record not found.
			<DeskLink to="/material-consumption">Back to log →</DeskLink>
		</p>
	</div>
</template>
