<script setup>
// Machinery Register — the Equipment Register report (Equipment workspace). Owned + hired
// plant with their rates, with the prototype's filter strip (type, ownership, status).

import { computed, onMounted, reactive, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";

import DeskLink from "@/components/desk/DeskLink.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { usePermissions } from "@/composables/usePermissions";
import { getMachineryRegister } from "@/data/equipmentApi";
import { fmtINR } from "@/utils/format";

const router = useRouter();
const { canCreate } = usePermissions();

const all = ref([]);
const loading = ref(true);
const error = ref("");

onMounted(async () => {
	try {
		all.value = (await getMachineryRegister()) || [];
	} catch (e) {
		error.value = e.message || "Failed to load machinery.";
	} finally {
		loading.value = false;
	}
});

const search = ref("");
const BLANK = { type: "", ownership: "", status: "" };
const f = reactive({ ...BLANK });
const anyFilter = computed(
	() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]) || !!search.value
);
function clearFilters() {
	Object.assign(f, BLANK);
	search.value = "";
}
const typeOptions = computed(() =>
	[...new Set(all.value.map((m) => m.machinery_type).filter(Boolean))]
		.map((v) => ({ value: v, label: v }))
		.sort((a, b) => a.label.localeCompare(b.label))
);

const rows = computed(() => {
	const t = search.value.trim().toLowerCase();
	return all.value.filter(
		(m) =>
			(!f.type || m.machinery_type === f.type) &&
			(!f.ownership || m.ownership === f.ownership) &&
			(!f.status || m.status === f.status) &&
			(!t ||
				(m.machinery_name || "").toLowerCase().includes(t) ||
				(m.machinery_type || "").toLowerCase().includes(t))
	);
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
	router.push(`/machinery/${row.name}`);
}
</script>

<template>
	<DeskPage title="Machinery Register" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="canCreate('machinery')" to="/machinery/new" class="desk-save-btn">+ New</RouterLink>
		</template>

		<div v-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<template v-else>
			<ReportFilters
				:active="anyFilter"
				:shown="rows.length"
				:total="all.length"
				noun="machines"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Type</span
					>
					<span class="w-44 inline-block">
						<DeskSearchableSelect
							v-model="f.type"
							:options="typeOptions"
							allow-clear
							placeholder="All types"
							search-placeholder="Search…"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Ownership</span
					>
					<DeskSelect v-model="f.ownership" class="!w-36">
						<option value="">Any</option>
						<option value="Owned">Owned</option>
						<option value="Hired">Hired</option>
					</DeskSelect>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Status</span
					>
					<DeskSelect v-model="f.status" class="!w-36">
						<option value="">Any</option>
						<option value="Active">Active</option>
						<option value="Inactive">Inactive</option>
					</DeskSelect>
				</label>
			</ReportFilters>

			<DeskList
				v-model="search"
				:rows="rows"
				:columns="columns"
				row-key="name"
				search-placeholder="Search machinery…"
				@row-click="onRowClick"
			>
				<template #cell-machinery_name="{ row }">
					<DeskLink :to="`/machinery/${row.name}`" class="font-medium" @click.stop>{{
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
						{{ loading ? "Loading machinery…" : "No machinery yet." }}
						<RouterLink v-if="!loading && canCreate('machinery')" to="/machinery/new" class="desk-link"
							>Add one →</RouterLink
						>
					</div>
				</template>
			</DeskList>
		</template>
	</DeskPage>
</template>
