<script setup>
// Scope Change Order register — Desk-styled, backend-backed via the data adapter.
// Impact colouring: positive = added cost to the project = red; negative = saving = green.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { usePermissions } from "@/composables/usePermissions";
import StatusBadge from "@/components/StatusBadge.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { fmtINR, fmtCompactINR, fmtDate } from "@/utils/format";

const router = useRouter();
const { canCreate } = usePermissions();

// KPI strip aggregates the whole register — a lightweight full fetch kept alongside
// the paginated list (which only holds the current page).
const kpiRes = useDocTypeList("Scope Change Order", {
	fields: ["name", "impact", "recoverable", "status"],
	orderBy: "creation desc",
	pageLength: 0,
	cache: "buildsuite-sco-kpis",
});
const all = computed(() => kpiRes.data || []);
const pendingCount = computed(
	() => all.value.filter((s) => s.status === "Pending Approval").length
);
const totalImpact = computed(() => all.value.reduce((a, s) => a + (Number(s.impact) || 0), 0));
const recoverableTotal = computed(() =>
	all.value.filter((s) => s.recoverable).reduce((a, s) => a + (Number(s.impact) || 0), 0)
);

const statusFilter = ref("");
const filterValues = computed(() => ({ status: statusFilter.value }));
const filterFieldMap = { status: "status" };

const FIELDS = [
	"name",
	"project",
	"project_name",
	"title",
	"type",
	"impact",
	"recoverable",
	"status",
	"raised_by",
	"raised_date",
];

const columns = [
	{ key: "name", label: "ID" },
	{ key: "title", label: "Title" },
	{ key: "project", label: "Project" },
	{ key: "type", label: "Type" },
	{ key: "impact", label: "Impact", align: "right" },
	{ key: "recoverable", label: "Recoverable" },
	{ key: "status", label: "Status" },
	{ key: "raised_date", label: "Date" },
];

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Scope Change Orders" }];

function onRowClick(row) {
	router.push(`/sco/${row.name}`);
}
</script>

<template>
	<DeskPage title="Scope Change Orders" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="canCreate('sco')" to="/sco/new" class="desk-save-btn"
				>+ Raise SCO</RouterLink
			>
		</template>

		<!-- KPI strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Total SCOs
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5">{{ all.length }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Pending approval
				</div>
				<div class="text-base font-semibold text-warning-700 mt-0.5">
					{{ pendingCount }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Net cost impact
				</div>
				<div
					class="text-base font-semibold mt-0.5 tabular-nums"
					:class="totalImpact >= 0 ? 'text-danger-700' : 'text-success-700'"
				>
					{{ totalImpact >= 0 ? "+" : "-" }}{{ fmtCompactINR(Math.abs(totalImpact)) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Client recoverable
				</div>
				<div class="text-base font-semibold text-success-700 mt-0.5 tabular-nums">
					{{ fmtCompactINR(recoverableTotal) }}
				</div>
			</div>
		</div>

		<DocTypeListView
			doctype="Scope Change Order"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['name', 'title']"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-sco-list"
			row-key="name"
			search-placeholder="Search SCO id or title…"
			empty-message="No scope change orders yet."
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-44">
					<option value="">Status: Any</option>
					<option>Pending Approval</option>
					<option>Approved</option>
					<option>Rejected</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Status"
					:value="statusFilter"
					@remove="statusFilter = ''"
				/>
			</template>

			<template #cell-name="{ row }">
				<DeskLink :to="`/sco/${row.name}`" class="font-mono text-xs" @click.stop>{{
					row.name
				}}</DeskLink>
			</template>
			<template #cell-title="{ row }">
				<span class="text-ink-900 font-medium text-sm">{{ row.title }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700 text-xs">{{ row.project_name || row.project }}</span>
			</template>
			<template #cell-type="{ row }">
				<span class="text-ink-700 text-xs">{{ row.type }}</span>
			</template>
			<template #cell-impact="{ row }">
				<span
					class="tabular-nums"
					:class="Number(row.impact) >= 0 ? 'text-danger-700' : 'text-success-700'"
				>
					{{ Number(row.impact) >= 0 ? "+" : "-"
					}}{{ fmtINR(Math.abs(Number(row.impact) || 0)) }}
				</span>
			</template>
			<template #cell-recoverable="{ row }">
				<span
					v-if="row.recoverable"
					class="text-[10px] px-1.5 py-0.5 bg-success-50 text-success-700 font-medium rounded"
					>Yes</span
				>
				<span
					v-else
					class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600 font-medium rounded"
					>Internal</span
				>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>
			<template #cell-raised_date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.raised_date) }}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
