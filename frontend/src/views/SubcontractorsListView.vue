<script setup>
// Subcontractors master list — Desk-styled, mirrors the prototype.

import { computed, ref, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { listSubcontractors } from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const router = useRouter();

// Subcontractors are Suppliers of type "Subcontractor"; the API joins each one's
// primary Contact so contact person + phone come back for the list columns.
const subs = ref([]);
const loading = ref(true);
async function loadSubs() {
	loading.value = true;
	try {
		subs.value = (await listSubcontractors()).map((s) => ({
			id: s.name,
			name: s.subcontractor_name,
			trade: s.trade,
			tax_id: s.tax_id,
			status: s.status,
			contact: s.contact_person,
			phone: s.phone,
		}));
	} finally {
		loading.value = false;
	}
}
onMounted(loadSubs);

// Trade filter — the Construction Trade master drives the dropdown.
const tradesRes = useDocTypeList("Construction Trade", {
	fields: ["name"],
	orderBy: "name asc",
	pageLength: 0,
	cache: "buildsuite-construction-trades",
});
const tradeOptions = computed(() => (tradesRes.data || []).map((t) => t.name));
const tradeFilter = ref("");

const search = ref("");
const rows = computed(() => {
	let data = subs.value;
	if (tradeFilter.value) data = data.filter((s) => s.trade === tradeFilter.value);
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(s) =>
				(s.name || "").toLowerCase().includes(q) ||
				(s.trade || "").toLowerCase().includes(q) ||
				(s.tax_id || "").toLowerCase().includes(q) ||
				(s.contact || "").toLowerCase().includes(q) ||
				(s.phone || "").toLowerCase().includes(q)
		);
	return data;
});

const columns = [
	{ key: "id", label: "ID" },
	{ key: "name", label: "Name" },
	{ key: "trade", label: "Trade" },
	{ key: "contact", label: "Contact" },
	{ key: "phone", label: "Phone" },
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
			<select
				v-model="tradeFilter"
				class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white text-ink-700 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
				title="Filter by trade"
			>
				<option value="">All trades</option>
				<option v-for="t in tradeOptions" :key="t" :value="t">{{ t }}</option>
			</select>
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
			<template #cell-contact="{ row }">
				<span v-if="row.contact" class="text-xs text-ink-700">{{ row.contact }}</span>
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-phone="{ row }">
				<span v-if="row.phone" class="text-xs font-mono text-ink-700">{{
					row.phone
				}}</span>
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
					{{ loading ? "Loading subcontractors…" : "No subcontractors yet." }}
					<RouterLink v-if="!loading" to="/subcontractors/new" class="desk-link"
						>Add one →</RouterLink
					>
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
