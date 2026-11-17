<script setup>
// Sales › Leads — enquiries that are not customers yet, on ERPNext's own Lead.
//
// Board (the default) or List, remembered per browser. The board's columns are the lead's stages;
// a card moves by hand between Lead / Open / Interested, while Quotation and Lost Quotation follow
// the lead's quotations and Converted its customer (buildsuite_core.utils.lead), so those columns
// refuse a drop and say why. Do Not Contact has no column: stopping is a decision, not a stage —
// the board counts those leads under it and the List shows them.
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSegmented from "@/components/desk/DeskSegmented.vue";
import DeskBoard from "@/components/desk/DeskBoard.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import FrappeUserBadge from "@/components/FrappeUserBadge.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import LeadFormModal from "@/components/LeadFormModal.vue";
import { usePermissions } from "@/composables/usePermissions";
import { listLeads, updateLead } from "@/data/leadsApi";
import {
	DO_NOT_CONTACT,
	LEAD_BOARD_STATUSES,
	LEAD_MANUAL_STATUSES,
	LEAD_STATUSES,
	leadAge,
	leadMatchesSearch,
} from "@/data/leads";
import { showToast } from "@/utils/appToast";
import { fmtCompactCurrency, fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { canCreate, canEdit } = usePermissions();
const canAdd = computed(() => canCreate("lead"));
const canMoveLeads = computed(() => canEdit("lead"));

// ---- view, remembered per browser ----
const VIEW_KEY = "buildsuite:leads:view";
function readView() {
	try {
		return localStorage.getItem(VIEW_KEY) === "list" ? "list" : "board";
	} catch {
		return "board";
	}
}
const view = ref(readView());
watch(view, (v) => {
	try {
		localStorage.setItem(VIEW_KEY, v);
	} catch {
		/* private window — the choice just isn't remembered */
	}
});
const VIEWS = [
	{ value: "board", label: __("Board"), icon: "layout-grid" },
	{ value: "list", label: __("List"), icon: "clipboard-list" },
];

// ---- data ----
const leads = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		leads.value = (await listLeads()) || [];
	} catch (err) {
		showToast(err.message || __("Could not load the leads."), "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

// ---- filters ----
const search = ref("");
const sourceFilter = ref("");
const ownerFilter = ref("");
const statusFilter = ref(""); // List only — the board's columns ARE the status
const anyFilter = computed(
	() => !!(search.value || sourceFilter.value || ownerFilter.value || statusFilter.value),
);
function clearFilters() {
	search.value = "";
	sourceFilter.value = "";
	ownerFilter.value = "";
	statusFilter.value = "";
}

const filtered = computed(() =>
	leads.value.filter(
		(l) =>
			leadMatchesSearch(l, search.value) &&
			(!sourceFilter.value || l.utm_source === sourceFilter.value) &&
			(!ownerFilter.value || l.lead_owner === ownerFilter.value) &&
			(view.value !== "list" || !statusFilter.value || l.status === statusFilter.value),
	),
);
const openCount = computed(
	() =>
		filtered.value.filter(
			(l) => !["Converted", DO_NOT_CONTACT, "Lost Quotation"].includes(l.status),
		).length,
);
const subtitle = computed(() => {
	const n = filtered.value.length;
	return __("Sales · enquiries that are not customers yet · {0} · {1} open", [
		n === 1 ? __("1 lead") : __("{0} leads", [n]),
		openCount.value,
	]);
});

// ---- board ----
// ERPNext's own Replied / Opportunity have no BuildSuite column; they read as Open.
const columnOf = (status) => (["Replied", "Opportunity"].includes(status) ? "Open" : status);
const columns = computed(() =>
	LEAD_BOARD_STATUSES.map((status) => ({
		key: status,
		label: __(status),
		items: filtered.value.filter((l) => columnOf(l.status) === status),
		droppable: canMoveLeads.value && LEAD_MANUAL_STATUSES.includes(status),
	})),
);
const hiddenOnBoard = computed(
	() => filtered.value.filter((l) => l.status === DO_NOT_CONTACT).length,
);

// Whoever may edit leads can pick up any card; a card whose column is not theirs to set (a
// converted lead, or one with quotations) is refused on the drop with the reason, rather than
// silently not lifting.
const canPickUp = () => canMoveLeads.value;
const isConverted = (lead) => lead.status === "Converted" || !!lead.customer;

async function onDrop({ item, to, column }) {
	if (columnOf(item.status) === to) return;
	if (isConverted(item)) {
		showToast(
			__("{0} is a customer now, so it stays in Converted.", [item.lead_name]),
			"info",
		);
		return;
	}
	if (item.quotation_count) {
		showToast(__("{0} has quotations, so its column follows them.", [item.lead_name]), "info");
		return;
	}
	if (!column.droppable) {
		const why =
			to === "Converted"
				? __(
						"{0} is set by the system: it follows the lead's quotations and its conversion to a customer.",
						[__(to)],
					)
				: __("{0} is set by the system: it follows the lead's quotations.", [__(to)]);
		showToast(why, "info");
		return;
	}
	const before = item.status;
	item.status = to; // optimistic; put back if the save is refused
	try {
		await updateLead(item.name, { status: to });
	} catch (err) {
		item.status = before;
		showToast(err.message || __("Could not move the lead."), "error");
	}
}

function quotationLine(lead) {
	const n = lead.quotation_count;
	const count = n === 1 ? __("1 quotation") : __("{0} quotations", [n]);
	return `${count} · ${fmtCompactCurrency(lead.latest_quotation_total, lead.latest_quotation_currency || undefined)}`;
}

function openLead(lead) {
	router.push(`/leads/${encodeURIComponent(lead.name)}`);
}

// ---- list ----
const listColumns = [
	{ key: "lead_name", label: __("Lead") },
	{ key: "mobile_no", label: __("Mobile") },
	{ key: "city", label: __("Place") },
	{ key: "utm_source", label: __("Source") },
	{ key: "quotations", label: __("Quotations"), align: "right" },
	{ key: "status", label: __("Status") },
	{ key: "creation", label: __("Created") },
];

// ---- new lead ----
const newOpen = ref(false);
function onSaved(lead) {
	newOpen.value = false;
	router.push(`/leads/${encodeURIComponent(lead.name)}`);
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Sales"), to: "/sales" },
	{ label: __("Leads") },
];
</script>

<template>
	<DeskPage :title="__('Leads')" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskSegmented v-model="view" :options="VIEWS" :aria-label="__('View')" />
			<button
				v-if="canAdd"
				type="button"
				class="desk-save-btn !text-xs"
				@click="newOpen = true"
			>
				{{ __("+ New lead") }}
			</button>
		</template>

		<!-- Filters, shared by both views. The List keeps its search inside the table. -->
		<div class="flex flex-wrap items-center gap-2 mb-3">
			<div v-if="view === 'board'" class="w-full sm:w-64">
				<DeskInput v-model="search" :placeholder="__('Search name, mobile, place…')" />
			</div>
			<div class="w-full sm:w-48">
				<DeskLinkPicker
					v-model="sourceFilter"
					doctype="UTM Source"
					:placeholder="__('Any source')"
				/>
			</div>
			<div class="w-full sm:w-52">
				<DeskLinkPicker
					v-model="ownerFilter"
					doctype="User"
					label-field="full_name"
					:search-fields="['full_name', 'name']"
					:filters="[
						['enabled', '=', 1],
						['user_type', '=', 'System User'],
					]"
					:placeholder="__('Any owner')"
				/>
			</div>
			<div v-if="view === 'list'" class="w-full sm:w-44">
				<DeskSelect v-model="statusFilter">
					<option value="">{{ __("Any status") }}</option>
					<option v-for="s in LEAD_STATUSES" :key="s" :value="s">{{ __(s) }}</option>
				</DeskSelect>
			</div>
			<button v-if="anyFilter" type="button" class="desk-link text-xs" @click="clearFilters">
				{{ __("Clear filters") }}
			</button>
		</div>

		<!-- Board -->
		<template v-if="view === 'board'">
			<p v-if="loading && !leads.length" class="text-sm text-ink-500 py-6">
				{{ __("Loading leads…") }}
			</p>
			<template v-else>
				<DeskBoard
					:columns="columns"
					item-key="name"
					:draggable="canPickUp"
					:locked-text="__('Set by the system')"
					@drop="onDrop"
				>
					<!-- A div, not a <button>: a drag cannot start from a form control. -->
					<template #card="{ item }">
						<div
							role="button"
							tabindex="0"
							class="w-full text-left bg-white border border-ink-200 hover:border-ink-300 px-3 py-2.5 shadow-fp-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
							style="border-radius: 8px"
							@click="openLead(item)"
							@keydown.enter.prevent="openLead(item)"
							@keydown.space.prevent="openLead(item)"
						>
							<div class="text-sm font-medium text-ink-900 leading-snug">
								{{ item.lead_name || item.company_name }}
							</div>
							<div
								v-if="item.company_name && item.company_name !== item.lead_name"
								class="text-[11px] text-ink-500"
							>
								{{ item.company_name }}
							</div>
							<div class="text-xs text-ink-700 mt-1 tabular-nums">
								{{ item.mobile_no || __("No mobile") }}
							</div>
							<div class="text-[11px] text-ink-500">
								{{
									[item.city, item.utm_source && __(item.utm_source)]
										.filter(Boolean)
										.join(" · ") || "—"
								}}
							</div>
							<div
								v-if="item.quotation_count"
								class="text-[11px] text-ink-600 mt-1.5 flex items-center gap-1"
							>
								<WorkspaceIcon slug="file-text" :size="12" />
								<span class="tabular-nums">{{ quotationLine(item) }}</span>
							</div>
							<div
								v-if="item.latest_lost_reasons?.length"
								class="text-[11px] text-danger-700 truncate"
							>
								{{ __("Lost: {0}", [item.latest_lost_reasons.join(", ")]) }}
							</div>
							<div
								v-if="item.customer_name"
								class="text-[11px] text-brand-700 truncate"
							>
								{{ __("Customer: {0}", [item.customer_name]) }}
							</div>
							<div class="flex items-center justify-between mt-2">
								<FrappeUserBadge
									v-if="item.lead_owner"
									:user-id="item.lead_owner"
									:show-name="false"
									size="xs"
								/>
								<span v-else />
								<span class="text-[11px] text-ink-500">{{
									__(leadAge(item.creation))
								}}</span>
							</div>
						</div>
					</template>
				</DeskBoard>
				<p v-if="hiddenOnBoard" class="text-xs text-ink-500 mt-3">
					{{
						hiddenOnBoard === 1
							? __(
									"1 marked Do Not Contact is not shown: stopping is a decision, not a stage. The list shows it.",
								)
							: __(
									"{0} marked Do Not Contact are not shown: stopping is a decision, not a stage. The list shows them.",
									[hiddenOnBoard],
								)
					}}
				</p>
				<p v-if="!loading && !leads.length" class="text-sm text-ink-500 mt-3">
					{{ __("No leads yet. Add one when someone asks for a price.") }}
				</p>
			</template>
		</template>

		<!-- List -->
		<DeskList
			v-else
			v-model="search"
			:rows="filtered"
			:columns="listColumns"
			row-key="name"
			:loading="loading && !leads.length"
			:show-sort="false"
			:search-placeholder="__('Search name, mobile, place…')"
			@row-click="openLead"
		>
			<template #cell-lead_name="{ row }">
				<div class="text-ink-900 font-medium">{{ row.lead_name || row.company_name }}</div>
				<div class="text-[11px] text-ink-500">
					{{
						[row.company_name !== row.lead_name ? row.company_name : "", row.name]
							.filter(Boolean)
							.join(" · ")
					}}
				</div>
			</template>
			<template #cell-mobile_no="{ row }">
				<span class="text-xs tabular-nums text-ink-700">{{ row.mobile_no || "—" }}</span>
			</template>
			<template #cell-city="{ row }">
				<span class="text-xs text-ink-700">{{ row.city || "—" }}</span>
			</template>
			<template #cell-utm_source="{ row }">
				<span class="text-xs text-ink-700">{{
					row.utm_source ? __(row.utm_source) : "—"
				}}</span>
			</template>
			<template #cell-quotations="{ row }">
				<span v-if="row.quotation_count" class="text-xs tabular-nums text-ink-900">
					{{ row.quotation_count }} ·
					{{
						fmtCompactCurrency(
							row.latest_quotation_total,
							row.latest_quotation_currency || undefined,
						)
					}}
				</span>
				<span v-else class="text-ink-400">—</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" size="xs" />
			</template>
			<template #cell-creation="{ row }">
				<span class="text-xs text-ink-700">{{ fmtDate(row.creation) }}</span>
			</template>
			<template #empty>
				<div class="text-sm text-ink-500">
					{{
						anyFilter
							? __("No leads match those filters.")
							: __("No leads yet. Add one when someone asks for a price.")
					}}
				</div>
			</template>
		</DeskList>

		<LeadFormModal :open="newOpen" @close="newOpen = false" @saved="onSaved" />
	</DeskPage>
</template>
