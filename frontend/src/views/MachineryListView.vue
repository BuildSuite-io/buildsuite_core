<script setup>
// Machinery register — Desk-styled list (Equipment workspace), mirrors the demo.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { usePermissions } from "@/composables/usePermissions";
import { fmtINR } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const router = useRouter();
const { canCreate } = usePermissions();

const machRes = useDocTypeList("Machinery", {
	fields: [
		"name",
		"machinery_name",
		"machinery_type",
		"ownership",
		"rate",
		"rate_unit",
		"owner_vendor",
		"status",
	],
	orderBy: "machinery_name asc",
	pageLength: 0,
	cache: "buildsuite-machinery-list",
	transform: (data) => data.map((m) => ({ id: m.name, ...m })),
});

const search = ref("");
const rows = computed(() => {
	let data = machRes.data || [];
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(m) =>
				(m.machinery_name || "").toLowerCase().includes(q) ||
				(m.machinery_type || "").toLowerCase().includes(q)
		);
	return data;
});

const columns = [
	{ key: "machinery_name", label: "Name" },
	{ key: "machinery_type", label: "Type" },
	{ key: "ownership", label: "Ownership" },
	{ key: "rate", label: "Rate", align: "right" },
	{ key: "owner_vendor", label: "Owner / Vendor" },
	{ key: "status", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery" },
];

function onRowClick(row) {
	router.push(`/machinery/${row.id}`);
}
</script>

<template>
	<DeskPage title="Machinery Register" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="canCreate('machinery')" to="/machinery/new" class="desk-save-btn"
				>+ New</RouterLink
			>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search name, type…"
			@row-click="onRowClick"
		>
			<template #cell-machinery_name="{ row }">
				<DeskLink :to="`/machinery/${row.id}`" class="font-medium" @click.stop>{{
					row.machinery_name
				}}</DeskLink>
			</template>
			<template #cell-machinery_type="{ row }">
				<span
					v-if="row.machinery_type"
					class="text-[11px] px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded"
					>{{ row.machinery_type }}</span
				>
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-rate="{ row }">
				<span class="tabular-nums text-ink-700">{{
					row.rate ? fmtINR(row.rate) + "/" + (row.rate_unit || "—") : "—"
				}}</span>
			</template>
			<template #cell-owner_vendor="{ row }">
				<span class="text-ink-500">{{ row.owner_vendor || "—" }}</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ machRes.loading ? "Loading machinery…" : "No machinery yet." }}
					<RouterLink
						v-if="!machRes.loading && canCreate('machinery')"
						to="/machinery/new"
						class="desk-link"
						>Add one →</RouterLink
					>
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
