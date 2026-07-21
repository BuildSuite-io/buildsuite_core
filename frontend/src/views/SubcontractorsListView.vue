<script setup>
// Subcontractors master list — Desk-styled, mirrors the prototype.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const router = useRouter();

// Subcontractors are Suppliers of type "Subcontractor".
const subsRes = useDocTypeList("Supplier", {
	fields: ["name", "supplier_name", "custom_trade", "tax_id", "disabled"],
	filters: [["supplier_type", "=", "Subcontractor"]],
	orderBy: "supplier_name asc",
	pageLength: 0,
	cache: "buildsuite-subcontractor-list",
	transform: (data) =>
		data.map((s) => ({
			id: s.name,
			name: s.supplier_name,
			trade: s.custom_trade,
			tax_id: s.tax_id,
			status: s.disabled ? "Inactive" : "Active",
		})),
});

const search = ref("");
const rows = computed(() => {
	let data = subsRes.data || [];
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(s) =>
				(s.name || "").toLowerCase().includes(q) ||
				(s.trade || "").toLowerCase().includes(q) ||
				(s.tax_id || "").toLowerCase().includes(q),
		);
	return data;
});

const columns = [
	{ key: "id", label: "ID" },
	{ key: "name", label: "Name" },
	{ key: "trade", label: "Trade" },
	{ key: "tax_id", label: "Tax ID" },
	{ key: "status", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractors" },
];

function onRowClick(row) {
	router.push(`/subcontractors/${row.id}`);
}
</script>

<template>
	<DeskPage title="Subcontractors" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/subcontractors/new" class="desk-save-btn">+ New</RouterLink>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search name, trade, contact…"
			@row-click="onRowClick"
		>
			<template #cell-id="{ row }">
				<DeskLink
					:to="`/subcontractors/${row.id}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.id }}</DeskLink
				>
			</template>
			<template #cell-name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.name }}</span>
			</template>
			<template #cell-trade="{ row }">
				<span
					v-if="row.trade"
					class="text-[11px] px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded"
					>{{ row.trade }}</span
				>
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-tax_id="{ row }">
				<span class="text-xs font-mono text-ink-500">{{ row.tax_id || "—" }}</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ subsRes.loading ? "Loading subcontractors…" : "No subcontractors yet." }}
					<RouterLink v-if="!subsRes.loading" to="/subcontractors/new" class="desk-link"
						>Add one →</RouterLink
					>
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
