<script setup>
import { computed, ref } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const fin = useFinanceMock();
const search = ref("");
const rows = computed(() => {
	const q = search.value.trim().toLowerCase();
	return fin.subcontractors.filter((c) => !q || c.name.toLowerCase().includes(q) || (c.trade || "").toLowerCase().includes(q));
});
const columns = [
	{ key: "name", label: "Name" },
	{ key: "trade", label: "Trade" },
	{ key: "contactPerson", label: "Contact" },
	{ key: "phone", label: "Phone" },
	{ key: "gstin", label: "GST no." },
	{ key: "status", label: "Status" },
];
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Subcontractors" }];
</script>

<template>
	<DeskPage title="Subcontractors" :breadcrumbs="breadcrumbs">
		<DeskList v-model="search" :rows="rows" :columns="columns" row-key="id" search-placeholder="Search subcontractors…">
			<template #cell-gstin="{ row }"><span class="font-mono text-xs text-ink-500">{{ row.gstin || "—" }}</span></template>
			<template #cell-status="{ row }"><StatusBadge :status="row.status" /></template>
			<template #empty>
				<div class="text-sm text-ink-500">Subcontractors are managed in the Subcontract workspace. This is a read-only finance view.</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
