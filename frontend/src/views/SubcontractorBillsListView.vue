<script setup>
// Subcontractor Bill list — Desk-styled. Each bill generates a Purchase
// Invoice on submit; the list shows gross / retention / net payable + status.

import { computed, reactive, ref, onMounted } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { listBills } from "@/data/subcontractApi";
import { useProjectNames } from "@/composables/useProjectNames";
import { usePermissions } from "@/composables/usePermissions";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const router = useRouter();
const { projectName } = useProjectNames();
const { canCreate } = usePermissions();

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

// Filters (match the prototype S313): party, project, workflow state and billed period.
const BLANK = { sub: "", project: "", state: "", from: "", to: "" };
const f = reactive({ ...BLANK });
const anyFilter = computed(
	() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]) || !!search.value
);
function clearFilters() {
	Object.assign(f, BLANK);
	search.value = "";
}
const subOptions = computed(() =>
	[...new Set(allBills.value.map((b) => b.subcontractor).filter(Boolean))]
		.sort((a, b) => a.localeCompare(b))
		.map((s) => ({ value: s, label: s }))
);
const projectOptions = computed(() =>
	[...new Set(allBills.value.map((b) => b.project).filter(Boolean))]
		.map((p) => ({ value: p, label: projectName(p) }))
		.sort((a, b) => a.label.localeCompare(b.label))
);

const rows = computed(() => {
	let data = allBills.value;
	if (f.sub) data = data.filter((b) => b.subcontractor === f.sub);
	if (f.project) data = data.filter((b) => b.project === f.project);
	if (f.state) data = data.filter((b) => (b.status || "Draft") === f.state);
	if (f.from) data = data.filter((b) => (b.date || "") >= f.from);
	if (f.to) data = data.filter((b) => (b.date || "") <= f.to);
	const q = search.value.trim().toLowerCase();
	if (q)
		data = data.filter(
			(b) =>
				(b.id || "").toLowerCase().includes(q) ||
				(b.subcontractor || "").toLowerCase().includes(q) ||
				(b.project || "").toLowerCase().includes(q) ||
				projectName(b.project).toLowerCase().includes(q)
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
			<RouterLink
				v-if="canCreate('subcontractorBill')"
				to="/subcontractor-bills/new"
				class="desk-save-btn"
				>+ New</RouterLink
			>
		</template>

		<ReportFilters
			:active="anyFilter"
			:shown="rows.length"
			:total="allBills.length"
			noun="bills"
			@clear="clearFilters"
		>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>Subcontractor</span
				>
				<span class="w-52 inline-block"
					><DeskSearchableSelect
						v-model="f.sub"
						:options="subOptions"
						allow-clear
						placeholder="All subcontractors"
						search-placeholder="Search…"
				/></span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>Project</span
				>
				<span class="w-52 inline-block"
					><DeskSearchableSelect
						v-model="f.project"
						:options="projectOptions"
						allow-clear
						placeholder="All projects"
						search-placeholder="Search…"
				/></span>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>Status</span
				>
				<DeskSelect v-model="f.state" class="!w-36">
					<option value="">Any</option>
					<option value="Draft">Draft</option>
					<option value="Submitted">Submitted</option>
					<option value="Cancelled">Cancelled</option>
				</DeskSelect>
			</label>
			<label class="flex items-center gap-1.5">
				<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>Billed</span
				>
				<DeskInput v-model="f.from" type="date" class="!w-36" />
				<span class="text-[11px] text-ink-400">to</span>
				<DeskInput v-model="f.to" type="date" class="!w-36" />
			</label>
		</ReportFilters>

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
				<span class="text-xs text-ink-500">{{ projectName(row.project) }}</span>
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
