<script setup>
// Field Employees — ERPNext Employee rows carrying the BuildSuite `is_labour`
// flag. Trade links to Labour Trade, contractor to Supplier (blank = engaged
// directly). Wage type is deliberately not modelled — the wage fields carry it.

import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useContractorOptions } from "@/composables/useContractorOptions";
import { fmtINR } from "@/utils/format";

const router = useRouter();
const { contractorName } = useContractorOptions();

function onRowClick(row) {
	router.push(`/field-employees/${row.name}`);
}

const columns = [
	// `name` is the record id, not a meta field, so the label must be explicit —
	// the auto-label would fall back to the raw key.
	{ key: "name", label: "Code" },
	{ key: "employee_name", label: "Name" },
	{ key: "custom_trade", label: "Trade" },
	{ key: "custom_wage", label: "Daily rate", align: "right" },
	{ key: "custom_contractor", label: "Contractor" },
	{ key: "status", label: "Status", preset: "status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Field Employees" },
];
</script>

<template>
	<DeskPage title="Field Employee" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/field-employees/new" class="desk-save-btn !text-xs">+ New</RouterLink>
		</template>

		<DocTypeListView
			doctype="Employee"
			:field-order="[
				'name',
				'employee_name',
				'custom_trade',
				'custom_wage',
				'custom_contractor',
				'status',
			]"
			:columns="columns"
			:search-fields="['employee_name', 'name', 'custom_trade', 'custom_contractor']"
			:base-filters="[['is_labour', '=', 1]]"
			cache-key="buildsuite-field-employees"
			row-key="name"
			initial-order-by="employee_name asc"
			search-placeholder="Search workers…"
			@row-click="onRowClick"
		>
			<template #cell-name="{ row }">
				<DeskLink
					:to="`/field-employees/${row.name}`"
					@click.stop
					class="font-mono text-xs"
				>
					{{ row.name }}
				</DeskLink>
			</template>

			<template #cell-employee_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.employee_name || row.name }}</span>
			</template>

			<template #cell-custom_trade="{ row }">
				<span class="text-ink-700">{{ row.custom_trade || "—" }}</span>
			</template>

			<template #cell-custom_wage="{ row }">
				<span class="tabular-nums text-ink-700">{{
					row.custom_wage ? fmtINR(row.custom_wage) : "—"
				}}</span>
			</template>

			<template #cell-custom_contractor="{ row }">
				<span class="text-ink-500">{{
					contractorName(row.custom_contractor) || "—"
				}}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
