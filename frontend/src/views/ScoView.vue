<script setup>
// Scope Change Order register — Desk-styled, backend-backed via the data adapter.
// Impact colouring: positive = added cost to the project = red; negative = saving = green.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import StatusBadge from "@/components/StatusBadge.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import { fmtINR, fmtCompactINR, fmtDate } from "@/utils/format";

const router = useRouter();

const scosRes = useDocTypeList("Scope Change Order", {
	fields: [
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
	],
	orderBy: "creation desc",
	pageLength: 0,
	cache: "buildsuite-sco-list",
	transform: (data) =>
		data.map((s) => ({
			id: s.name,
			project: s.project,
			projectName: s.project_name,
			title: s.title,
			type: s.type,
			impact: s.impact,
			recoverable: s.recoverable,
			status: s.status,
			raisedBy: s.raised_by,
			raisedDate: s.raised_date,
		})),
});

const all = computed(() => scosRes.data || []);
const search = ref("");
const statusFilter = ref("");

const items = computed(() => {
	let data = all.value;
	if (statusFilter.value) data = data.filter((s) => s.status === statusFilter.value);
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(s) =>
				(s.title || "").toLowerCase().includes(q) ||
				(s.id || "").toLowerCase().includes(q),
		);
	return data;
});

const pendingCount = computed(
	() => all.value.filter((s) => s.status === "Pending Approval").length,
);
const totalImpact = computed(() => all.value.reduce((a, s) => a + (Number(s.impact) || 0), 0));
const recoverableTotal = computed(() =>
	all.value.filter((s) => s.recoverable).reduce((a, s) => a + (Number(s.impact) || 0), 0),
);

const columns = [
	{ key: "id", label: "ID" },
	{ key: "title", label: "Title" },
	{ key: "project", label: "Project" },
	{ key: "type", label: "Type" },
	{ key: "impact", label: "Impact", align: "right" },
	{ key: "recoverable", label: "Recoverable" },
	{ key: "status", label: "Status" },
	{ key: "raisedDate", label: "Date" },
];

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Scope Change Orders" }];

function onRowClick(row) {
	router.push(`/sco/${row.id}`);
}
</script>

<template>
	<DeskPage title="Scope Change Orders" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/sco/new" class="desk-save-btn">+ Raise SCO</RouterLink>
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

		<DeskList
			v-model="search"
			:rows="items"
			:columns="columns"
			row-key="id"
			search-placeholder="Search SCO id or title…"
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

			<template #cell-id="{ row }">
				<DeskLink :to="`/sco/${row.id}`" class="font-mono text-xs" @click.stop>{{
					row.id
				}}</DeskLink>
			</template>
			<template #cell-title="{ row }">
				<span class="text-ink-900 font-medium text-sm">{{ row.title }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700 text-xs">{{ row.projectName || row.project }}</span>
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
			<template #cell-raisedDate="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.raisedDate) }}</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{
						scosRes.loading
							? "Loading scope change orders…"
							: "No scope change orders yet."
					}}
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
