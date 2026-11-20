<script setup>
// Requests for Quotation — ERPNext's Request for Quotation, in-app list via DocTypeListView
// (pagination / sort / search for free). The suppliers asked and how many have quoted live on
// child rows, so they come from a summary call (rfq_list_summaries) for the rows on screen.
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useProjectNames } from "@/composables/useProjectNames";
import { useActiveCompany, activeCompanyFilter } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { getRfqListSummaries } from "@/data/rfqApi";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const { canCreate } = usePermissions();
const { projectName } = useProjectNames();
const activeCompany = useActiveCompany();
// Toggle-gated: [] when company awareness is off, so the list shows every company.
const baseFilters = activeCompanyFilter();

const FIELDS = ["name", "subject", "project", "transaction_date", "status"];
const columns = [
	{ key: "name", label: __("ID") },
	{ key: "subject", label: __("Subject") },
	{ key: "project", label: __("Project") },
	{ key: "transaction_date", label: __("Date") },
	// Not fields: filled from the summaries (so neither is fetched nor offered as a sort).
	{ key: "suppliers", label: __("Suppliers") },
	{ key: "quotes", label: __("Quotations") },
	{ key: "status", label: __("Status") },
];

// Summaries for the rows on screen, fetched whenever the page changes (paging, filters, search,
// company) and kept for rows already seen. A request whose suppliers change is re-read on the
// next visit to the list.
const summaries = ref({});
async function onRowsChange(rows) {
	const names = (rows || []).map((r) => r.name).filter((n) => n && !(n in summaries.value));
	if (!names.length) return;
	try {
		summaries.value = { ...summaries.value, ...((await getRfqListSummaries(names)) || {}) };
	} catch {
		// the list still shows; only the supplier column stays blank for these rows
	}
}
const summary = (row) => summaries.value[row.name] || null;

const statusFilter = ref("");
const projectFilter = ref("");
const filterValues = computed(() => ({
	status: statusFilter.value,
	project: projectFilter.value,
}));
const filterFieldMap = { status: "status", project: "project" };

function openDetail(row) {
	router.push(`/procurement/rfqs/${row.name}`);
}
function openNew() {
	router.push("/procurement/rfqs/new");
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Request for Quotation") },
];
</script>

<template>
	<DeskPage
		:title="__('Request for Quotation')"
		:subtitle="
			__(
				'Ask suppliers to quote for the same list of material, then compare what comes back.'
			)
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="canCreate('rfq')"
				type="button"
				class="desk-save-btn !text-xs"
				data-test="rfq-new"
				@click="openNew"
			>
				+ {{ __("New") }}
			</button>
		</template>

		<DocTypeListView
			v-if="activeCompany"
			doctype="Request for Quotation"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'subject']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-rfqs"
			row-key="name"
			initial-order-by="transaction_date desc"
			:search-placeholder="__('Search request, subject…')"
			:empty-message="
				__(
					'No requests for quotation yet. Raise one, or start from a submitted material request.'
				)
			"
			@row-click="openDetail"
			@rows-change="onRowsChange"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-40">
					<option value="">{{ __("All statuses") }}</option>
					<option value="Draft">{{ __("Draft") }}</option>
					<option value="Submitted">{{ __("Submitted") }}</option>
					<option value="Cancelled">{{ __("Cancelled") }}</option>
				</DeskSelect>
				<div class="w-48">
					<DeskLinkPicker
						v-model="projectFilter"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:placeholder="__('All projects')"
					/>
				</div>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-[11px] text-ink-600 whitespace-nowrap">{{
					row.name
				}}</span>
			</template>
			<template #cell-subject="{ row }">
				<span class="block min-w-[200px] text-ink-900 font-medium">{{
					row.subject || "—"
				}}</span>
				<span v-if="summary(row)" class="block text-[11px] text-ink-500">
					{{
						summary(row).items === 1
							? __("1 item")
							: __("{0} items", [summary(row).items])
					}}
					<template v-if="summary(row).material_request">
						· {{ __("from {0}", [summary(row).material_request]) }}</template
					>
				</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700">{{ projectName(row.project) || "—" }}</span>
			</template>
			<template #cell-transaction_date="{ row }">
				<span class="text-ink-500 whitespace-nowrap">{{
					fmtDate(row.transaction_date)
				}}</span>
			</template>
			<template #cell-suppliers="{ row }">
				<span class="text-xs text-ink-600">{{
					summary(row)?.suppliers.join(", ") || "—"
				}}</span>
			</template>
			<template #cell-quotes="{ row }">
				<span
					v-if="summary(row)"
					class="text-xs tabular-nums whitespace-nowrap"
					:class="summary(row).received ? 'text-ink-900' : 'text-ink-500'"
				>
					{{
						__("{0} of {1} received", [
							summary(row).received,
							summary(row).suppliers.length,
						])
					}}
				</span>
				<span v-else class="text-ink-400">—</span>
			</template>
			<template #cell-status="{ row }">
				<ProcurementStatusPill :status="row.status" />
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
