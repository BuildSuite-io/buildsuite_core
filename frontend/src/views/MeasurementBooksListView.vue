<script setup>
// Measurement Book list — Desk-styled, mirrors the prototype. Sits at
// project level; each MB carries a work_order link so you can see which
// WO it feeds.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate } from "@/utils/format";

const router = useRouter();
const { projectName } = useProjectNames();

const mbRes = useDocTypeList("Measurement Book", {
	fields: ["name", "project", "work_order", "date", "measured_total", "status"],
	orderBy: "date desc",
	pageLength: 0,
	cache: "buildsuite-measurement-book-list",
	transform: (data) =>
		data.map((m) => ({
			id: m.name,
			project: m.project,
			work_order: m.work_order,
			date: m.date,
			measured: m.measured_total,
			status: m.status,
		})),
});

const search = ref("");
const rows = computed(() => {
	let data = mbRes.data || [];
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(m) =>
				(m.id || "").toLowerCase().includes(q) ||
				(m.work_order || "").toLowerCase().includes(q) ||
				(m.project || "").toLowerCase().includes(q) ||
				projectName(m.project).toLowerCase().includes(q)
		);
	return data;
});

const columns = [
	{ key: "id", label: "MB ID" },
	{ key: "project", label: "Project" },
	{ key: "work_order", label: "Work Order" },
	{ key: "date", label: "Date" },
	{ key: "measured", label: "Measured", align: "right" },
	{ key: "status", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Measurement Books" },
];

function onRowClick(row) {
	router.push(`/measurement-books/${row.id}`);
}
</script>

<template>
	<DeskPage title="Measurement Books" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/measurement-books/new" class="desk-save-btn">+ New</RouterLink>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search MB, WO, project…"
			@row-click="onRowClick"
		>
			<template #cell-id="{ row }">
				<DeskLink
					:to="`/measurement-books/${row.id}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.id }}</DeskLink
				>
			</template>
			<template #cell-project="{ row }">
				<span class="text-xs text-ink-700">{{ projectName(row.project) }}</span>
			</template>
			<template #cell-work_order="{ row }">
				<DeskLink
					:to="`/subcontractor-work-orders/${row.work_order}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.work_order }}</DeskLink
				>
			</template>
			<template #cell-date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.date) }}</span>
			</template>
			<template #cell-measured="{ row }">
				<span class="text-xs tabular-nums text-info-700 font-medium">{{
					Number(row.measured || 0).toLocaleString("en-IN")
				}}</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{
						mbRes.loading
							? "Loading measurement books…"
							: "No measurement books recorded yet."
					}}
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
