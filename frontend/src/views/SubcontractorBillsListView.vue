<script setup>
// Subcontractor Bill list — Desk-styled. Each bill generates a Purchase
// Invoice on submit; the list shows gross / retention / net payable + status.

import { computed, ref, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { listBills } from "@/data/subcontractApi";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const router = useRouter();

// Loaded via list_bills so each row carries the workflow state AND the derived payment status.
const allBills = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		allBills.value = (await listBills()).map((b) => ({
			id: b.name,
			ra_no: b.ra_no,
			is_direct: b.is_direct,
			subcontractor: b.subcontractor_name,
			project: b.project,
			date: b.date,
			gross: b.gross,
			retention: b.retention_amount,
			net: b.net_payable,
			status: b.status,
			payment_status: b.payment_status,
		}));
	} catch (err) {
		showToast(err.message || "Failed to load bills", "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

const search = ref("");
const rows = computed(() => {
	let data = allBills.value;
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(b) =>
				(b.id || "").toLowerCase().includes(q) ||
				(b.subcontractor || "").toLowerCase().includes(q) ||
				(b.project || "").toLowerCase().includes(q)
		);
	return data;
});

const columns = [
	{ key: "id", label: "Bill ID" },
	{ key: "ra_no", label: "Bill #" },
	{ key: "subcontractor", label: "Subcontractor" },
	{ key: "project", label: "Project" },
	{ key: "date", label: "Date" },
	{ key: "gross", label: "Gross", align: "right" },
	{ key: "retention", label: "Retention", align: "right" },
	{ key: "net", label: "Net payable", align: "right" },
	{ key: "status", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractor Bills" },
];

function onRowClick(row) {
	router.push(`/subcontractor-bills/${row.id}`);
}
</script>

<template>
	<DeskPage title="Subcontractor Bills" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/subcontractor-bills/new" class="desk-save-btn">+ New</RouterLink>
		</template>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search bill, subcontractor, project…"
			@row-click="onRowClick"
		>
			<template #cell-id="{ row }">
				<DeskLink
					:to="`/subcontractor-bills/${row.id}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.id }}</DeskLink
				>
			</template>
			<template #cell-ra_no="{ row }">
				<span class="text-xs text-ink-700"
					>Bill {{ row.ra_no
					}}<span v-if="row.is_direct" class="text-ink-400"> · direct</span></span
				>
			</template>
			<template #cell-subcontractor="{ row }">
				<span class="text-xs font-medium text-ink-900">{{ row.subcontractor }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-xs text-ink-500">{{ row.project }}</span>
			</template>
			<template #cell-date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.date) }}</span>
			</template>
			<template #cell-gross="{ row }">
				<span class="text-xs tabular-nums font-medium">{{ fmtINR(row.gross) }}</span>
			</template>
			<template #cell-retention="{ row }">
				<span class="text-xs tabular-nums text-warning-700">{{
					fmtINR(row.retention)
				}}</span>
			</template>
			<template #cell-net="{ row }">
				<span class="text-xs tabular-nums font-medium">{{ fmtINR(row.net) }}</span>
			</template>
			<template #cell-status="{ row }">
				<div class="flex items-center gap-1.5">
					<StatusBadge :status="row.status" />
					<StatusBadge
						v-if="row.payment_status"
						:status="row.payment_status"
						size="xs"
					/>
				</div>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ loading ? "Loading bills…" : "No subcontractor bills yet." }}
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
