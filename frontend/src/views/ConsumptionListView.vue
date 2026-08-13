<script setup>
// Material Consumption — Stock Entries of type "Material Issue".
// Its own API, not DocTypeListView: the consumed items are child rows.

import { onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import FrappeUserBadge from "@/components/FrappeUserBadge.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { listMaterialConsumption } from "@/data/materialConsumptionApi";
import { showToast } from "@/utils/appToast";
import { fmtDate } from "@/utils/format";

const router = useRouter();
const { projectOptions, projectLabel } = useProjectOptions();

const DOCSTATUS_LABELS = { 0: "Draft", 1: "Submitted", 2: "Cancelled" };

const rows = ref([]);
const totalCount = ref(0);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(10);
const search = ref("");
const projectFilter = ref("");

// reqId: only the latest request wins.
let reqId = 0;
async function reload() {
	const my = ++reqId;
	loading.value = true;
	try {
		const res = await listMaterialConsumption({
			start: (page.value - 1) * pageSize.value,
			page_length: pageSize.value,
			search: search.value.trim() || undefined,
			project: projectFilter.value || undefined,
		});
		if (my !== reqId) return;
		rows.value = res.rows || [];
		totalCount.value = res.total_count || 0;
	} catch (err) {
		if (my === reqId) showToast(err.message || "Could not load consumption.", "error");
	} finally {
		if (my === reqId) loading.value = false;
	}
}

let searchTimer;
watch(search, () => {
	clearTimeout(searchTimer);
	searchTimer = setTimeout(() => {
		page.value = 1;
		reload();
	}, 300);
});
watch(projectFilter, () => {
	page.value = 1;
	reload();
});
onMounted(reload);

// Formatting is the view's job — the API returns data.
function itemsSummary(row) {
	return (row.items || []).map((i) => `${i.label} ×${i.qty} ${i.uom}`.trim()).join(" · ");
}

const columns = [
	{ key: "name", label: "ID" },
	{ key: "posting_date", label: "Date" },
	{ key: "project", label: "Project" },
	{ key: "items", label: "Items consumed" },
	{ key: "cost_code_label", label: "Cost code" },
	{ key: "owner", label: "By" },
	{ key: "docstatus", label: "State" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Material Consumption" },
];
</script>

<template>
	<DeskPage title="Material Consumption" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/material-consumption/new" class="desk-save-btn !text-xs">
				+ Record consumption
			</RouterLink>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="name"
			search-placeholder="Search consumption…"
			@row-click="(row) => router.push(`/material-consumption/${row.name}`)"
			:server-paginated="true"
			:total-rows="totalCount"
			:current-page="page"
			:page-size="pageSize"
			@page-change="
				(p) => {
					if (p !== page) {
						page = p;
						reload();
					}
				}
			"
			@page-size-change="
				(s) => {
					pageSize = s;
					page = 1;
					reload();
				}
			"
		>
			<template #filter-chips>
				<div class="w-56">
					<DeskSearchableSelect
						v-model="projectFilter"
						:options="projectOptions"
						placeholder="All projects"
						search-placeholder="Search projects…"
						allow-clear
					/>
				</div>
			</template>

			<template #cell-name="{ row }">
				<DeskLink
					:to="`/material-consumption/${row.name}`"
					class="font-mono text-xs"
					@click.stop
				>
					{{ row.name }}
				</DeskLink>
			</template>

			<template #cell-posting_date="{ row }">
				<span class="text-ink-700">{{ fmtDate(row.posting_date) || "—" }}</span>
			</template>

			<template #cell-project="{ row }">
				<span class="text-ink-900 font-medium">{{
					projectLabel(row.project) || "—"
				}}</span>
			</template>

			<template #cell-items="{ row }">
				<span class="text-ink-700">{{ itemsSummary(row) || "—" }}</span>
			</template>

			<template #cell-cost_code_label="{ row }">
				<span
					v-if="row.cost_code_label"
					class="text-[11px] px-1.5 py-0.5 bg-info-50 text-info-700 whitespace-nowrap"
					style="border-radius: 4px"
					>{{ row.cost_code_label }}</span
				>
				<span v-else class="text-ink-400">—</span>
			</template>

			<template #cell-owner="{ row }">
				<FrappeUserBadge :user-id="row.owner" size="xs" />
			</template>

			<template #cell-docstatus="{ row }">
				<StatusBadge :status="DOCSTATUS_LABELS[row.docstatus] || 'Draft'" />
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ loading ? "Loading…" : "No material consumption recorded yet." }}
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
