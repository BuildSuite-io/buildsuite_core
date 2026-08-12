<script setup>
// Machinery Usage log — Desk-styled list (Equipment workspace), mirrors the demo.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { fmtINR, fmtDate } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const router = useRouter();
const { projectName } = useProjectNames();

const usageRes = useDocTypeList("Machinery Usage", {
	fields: [
		"name",
		"machine",
		"project",
		"task",
		"date",
		"quantity",
		"unit",
		"rate",
		"fuel_cost",
	],
	orderBy: "date desc",
	pageLength: 0,
	cache: "buildsuite-machinery-usage-list",
	transform: (data) => data.map((u) => ({ id: u.name, ...u })),
});

// The usage log stores machine + task ids; resolve them to readable names for display.
const machineryRes = useDocTypeList("Machinery", {
	fields: ["name", "machinery_name"],
	pageLength: 0,
	cache: "buildsuite-machinery-names",
});
const machineNameById = computed(() => {
	const map = {};
	for (const m of machineryRes.data || []) map[m.name] = m.machinery_name;
	return map;
});
const machineName = (id) => machineNameById.value[id] || id;

const taskRes = useDocTypeList("Task", {
	fields: ["name", "subject"],
	pageLength: 0,
	cache: "buildsuite-task-subjects",
});
const taskSubjectById = computed(() => {
	const map = {};
	for (const t of taskRes.data || []) map[t.name] = t.subject;
	return map;
});
const taskSubject = (id) => taskSubjectById.value[id] || id;

function totalFor(row) {
	return (Number(row.quantity) || 0) * (Number(row.rate) || 0) + (Number(row.fuel_cost) || 0);
}

const search = ref("");
const rows = computed(() => {
	let data = usageRes.data || [];
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(u) =>
				machineName(u.machine).toLowerCase().includes(q) ||
				taskSubject(u.task).toLowerCase().includes(q) ||
				(u.project || "").toLowerCase().includes(q) ||
				projectName(u.project).toLowerCase().includes(q)
		);
	return data;
});

const columns = [
	{ key: "date", label: "Date" },
	{ key: "machine", label: "Machine" },
	{ key: "project", label: "Project" },
	{ key: "task", label: "Task" },
	{ key: "quantity", label: "Qty", align: "right" },
	{ key: "total", label: "Total", align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery Usage" },
];

function onRowClick(row) {
	router.push(`/machinery-usage/${row.id}`);
}
</script>

<template>
	<DeskPage title="Machinery Usage Log" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/machinery-usage/new" class="desk-save-btn">+ Log usage</RouterLink>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search machine, project…"
			@row-click="onRowClick"
		>
			<template #cell-machine="{ row }">
				<DeskLink :to="`/machinery/${row.machine}`" @click.stop>{{
					machineName(row.machine)
				}}</DeskLink>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700">{{ projectName(row.project) || "—" }}</span>
			</template>
			<template #cell-task="{ row }">
				<span class="text-ink-500">{{ row.task ? taskSubject(row.task) : "—" }}</span>
			</template>
			<template #cell-date="{ row }">
				<span class="text-ink-500">{{ fmtDate(row.date) }}</span>
			</template>
			<template #cell-quantity="{ row }">
				<span class="tabular-nums">{{ row.quantity }} {{ row.unit }}</span>
			</template>
			<template #cell-total="{ row }">
				<span class="tabular-nums text-ink-900 font-medium">{{
					fmtINR(totalFor(row))
				}}</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ usageRes.loading ? "Loading usage log…" : "No usage logged yet." }}
					<RouterLink
						v-if="!usageRes.loading"
						to="/machinery-usage/new"
						class="desk-link"
						>Log usage →</RouterLink
					>
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
