<script setup>
// Project Finance › Suppliers master. Desk-styled list (DeskList + filter chips +
// Tax ID). Subcontractors ARE suppliers (ERPNext model) — they appear here as rows
// of type "Subcontractor", read live from the same Supplier master. Row behaviour:
//   - regular supplier  → edit modal (create + edit live here)
//   - subcontractor row → routes to the Subcontract master detail (managed there)
// Backed by buildsuite_core.api.suppliers.*.
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { listSuppliers, addSupplier, updateSupplier } from "@/data/suppliersApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import PartyFormModal from "./PartyFormModal.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtINR } from "@/utils/format";

const router = useRouter();
const store = useDataStore();
const { canCreate } = usePermissions();
// Regular suppliers are created AND edited here; create and write role-sets coincide
// (Procurement / PM / Director / admin tier), so one capability gates both.
const canManage = computed(() => canCreate("supplier"));

// The real supplier_type options (subcontractors are managed in the Subcontract module).
const TYPE_OPTIONS = ["Company", "Individual", "Partnership", "Subcontractor"];
const MODAL_TYPES = ["Company", "Individual", "Partnership"];

const suppliers = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		suppliers.value = await listSuppliers();
	} catch (err) {
		showToast(err.message || "Failed to load suppliers", "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

const search = ref("");
const typeFilter = ref("");

const rows = computed(() => {
	const t = search.value.trim().toLowerCase();
	let list = suppliers.value;
	if (typeFilter.value) list = list.filter((s) => s.type === typeFilter.value);
	if (t)
		list = list.filter(
			(s) =>
				(s.name || "").toLowerCase().includes(t) ||
				(s.contactPerson || "").toLowerCase().includes(t) ||
				(s.gstin || "").toLowerCase().includes(t) ||
				(s.trade || "").toLowerCase().includes(t)
		);
	return list;
});

const columns = [
	{ key: "name", label: "Name" },
	{ key: "type", label: "Type" },
	{ key: "contactPerson", label: "Contact" },
	{ key: "phone", label: "Phone" },
	{ key: "gstin", label: "Tax ID" },
	{ key: "advance", label: "Advance paid", align: "right" },
];

// --- create / edit modal (regular suppliers only) ---
const modalOpen = ref(false);
const modalError = ref("");
const editing = ref(null);

function openCreate() {
	editing.value = null;
	modalError.value = "";
	modalOpen.value = true;
}
function onRowClick(row) {
	if (row.is_subcontractor) {
		router.push(`/subcontractors/${row.id}`);
		return;
	}
	if (!canManage.value) return;
	editing.value = row;
	modalError.value = "";
	modalOpen.value = true;
}
async function onSave(payload) {
	modalError.value = "";
	try {
		if (editing.value) await updateSupplier(editing.value.id, payload);
		else await addSupplier(payload);
		modalOpen.value = false;
		await load();
	} catch (err) {
		modalError.value = err.message || "Save failed.";
	}
}

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Suppliers" }];
</script>

<template>
	<DeskPage title="Suppliers" :breadcrumbs="breadcrumbs">
		<div>
			<div v-if="canManage" class="flex items-center justify-end mb-2">
				<button type="button" class="desk-save-btn" @click="openCreate">
					+ New Supplier
				</button>
			</div>

			<DeskList
				v-model="search"
				:rows="rows"
				:columns="columns"
				row-key="id"
				search-placeholder="Search name, contact, trade, tax ID…"
				@row-click="onRowClick"
			>
				<template #filter-chips>
					<DeskFilterChip
						v-if="typeFilter"
						:label="`Type: ${typeFilter}`"
						@remove="typeFilter = ''"
					/>
					<DeskSelect v-else v-model="typeFilter" class="!w-44">
						<option value="">All types</option>
						<option v-for="t in TYPE_OPTIONS" :key="t">{{ t }}</option>
					</DeskSelect>
				</template>

				<template #cell-name="{ row }">
					<span class="text-ink-900 font-medium">{{ row.name }}</span>
					<span v-if="row.trade" class="ml-1.5 text-[10px] text-ink-400">{{
						row.trade
					}}</span>
				</template>
				<template #cell-type="{ row }">
					<span
						v-if="row.is_subcontractor"
						class="text-[11px] px-1.5 py-0.5 bg-info-50 text-info-700 rounded"
						>Subcontractor</span
					>
					<span
						v-else-if="row.type"
						class="text-[11px] px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded"
						>{{ row.type }}</span
					>
					<span v-else class="text-ink-400">—</span>
				</template>
				<template #cell-contactPerson="{ row }">
					<span class="text-xs text-ink-700">{{ row.contactPerson || "—" }}</span>
				</template>
				<template #cell-phone="{ row }">
					<span class="text-xs text-ink-500">{{ row.phone || "—" }}</span>
				</template>
				<template #cell-gstin="{ row }">
					<span class="text-xs font-mono text-ink-500">{{ row.gstin || "—" }}</span>
				</template>
				<template #cell-advance="{ row }">
					<span
						v-if="row.advance > 0"
						class="text-xs tabular-nums text-info-700 font-medium"
						>{{ fmtINR(row.advance) }}</span
					>
					<span v-else class="text-ink-400">—</span>
				</template>

				<template #empty>
					<div class="text-sm text-ink-500">
						{{ loading ? "Loading suppliers…" : "No suppliers yet." }}
						<template v-if="canManage && !loading">
							·
							<button type="button" class="desk-link" @click="openCreate">
								Add one →
							</button>
						</template>
					</div>
				</template>
			</DeskList>
			<p class="text-[11px] text-ink-400 mt-2">
				Subcontractors are suppliers of type "Subcontractor" — click one to open its master
				in the Subcontract module.
			</p>

			<PartyFormModal
				:open="modalOpen"
				:title="editing ? 'Edit Supplier' : 'New Supplier'"
				type-label="Supplier type"
				:type-options="MODAL_TYPES"
				:initial="editing"
				:server-error="modalError"
				@save="onSave"
				@close="modalOpen = false"
			/>
		</div>
	</DeskPage>
</template>
