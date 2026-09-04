<script setup>
// Project Finance › Customers master. Desk-styled list (DeskList + filter chips +
// Tax ID). Rows open an edit modal — customers are created AND edited from here,
// backed by the real Customer master (buildsuite_core.api.customers.*).
import { ref, computed, onMounted } from "vue";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { listCustomers, addCustomer, updateCustomer } from "@/data/customersApi";
import { createDataAdapter } from "@/data/adapters";
import { useConfirm } from "@/composables/useConfirm";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import PartyFormModal from "./PartyFormModal.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtINR } from "@/utils/format";

const store = useDataStore();
const { canCreate, canDelete } = usePermissions();
const adapter = createDataAdapter(store);
const confirmDialog = useConfirm();
// Customers are created AND edited from this panel; the create and write role-sets
// coincide (Director / PM / Accountant / admin tier), so one capability gates both.
const canManage = computed(() => canCreate("customer"));

const TYPE_OPTIONS = ["Company", "Individual", "Partnership"];

const customers = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		customers.value = await listCustomers();
	} catch (err) {
		showToast(err.message || "Failed to load customers", "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

const search = ref("");
const typeFilter = ref("");

const rows = computed(() => {
	const t = search.value.trim().toLowerCase();
	let list = customers.value;
	if (typeFilter.value) list = list.filter((c) => c.type === typeFilter.value);
	if (t)
		list = list.filter(
			(c) =>
				(c.name || "").toLowerCase().includes(t) ||
				(c.contactPerson || "").toLowerCase().includes(t) ||
				(c.gstin || "").toLowerCase().includes(t)
		);
	return list;
});

const columns = [
	{ key: "name", label: "Name" },
	{ key: "type", label: "Type" },
	{ key: "contactPerson", label: "Contact" },
	{ key: "phone", label: "Phone" },
	{ key: "gstin", label: "Tax ID" },
	{ key: "advance", label: "Advance held", align: "right" },
];

// --- create / edit modal ---
const modalOpen = ref(false);
const modalError = ref("");
const editing = ref(null); // customer record when editing, null for create

function openCreate() {
	editing.value = null;
	modalError.value = "";
	modalOpen.value = true;
}
function onRowClick(row) {
	if (!canManage.value) return;
	editing.value = row;
	modalError.value = "";
	modalOpen.value = true;
}
async function onSave(payload) {
	modalError.value = "";
	try {
		if (editing.value) await updateCustomer(editing.value.id, payload);
		else await addCustomer(payload);
		modalOpen.value = false;
		await load();
	} catch (err) {
		modalError.value = err.message || "Save failed.";
	}
}
async function onDelete() {
	if (!editing.value) return;
	const ok = await confirmDialog({
		title: `Delete ${editing.value.name}?`,
		message:
			"This customer master record will be removed permanently. Deletion is blocked if it has linked transactions (invoices, payments).",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	modalError.value = "";
	try {
		await adapter.remove("Customer", editing.value.id);
		modalOpen.value = false;
		await load();
		showToast("Customer deleted.");
	} catch (err) {
		modalError.value =
			err.message || "Delete failed — the customer may have linked transactions.";
	}
}

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Customers" }];
</script>

<template>
	<DeskPage title="Customers" :breadcrumbs="breadcrumbs">
		<div>
			<div v-if="canManage" class="flex items-center justify-end mb-2">
				<button type="button" class="desk-save-btn" @click="openCreate">
					+ New Customer
				</button>
			</div>

			<DeskList
				v-model="search"
				:rows="rows"
				:columns="columns"
				row-key="id"
				search-placeholder="Search name, contact, tax ID…"
				@row-click="onRowClick"
			>
				<template #filter-chips>
					<DeskFilterChip
						v-if="typeFilter"
						:label="`Type: ${typeFilter}`"
						@remove="typeFilter = ''"
					/>
					<DeskSelect v-else v-model="typeFilter" class="!w-40">
						<option value="">All types</option>
						<option v-for="t in TYPE_OPTIONS" :key="t">{{ t }}</option>
					</DeskSelect>
				</template>

				<template #cell-name="{ row }">
					<span class="text-ink-900 font-medium">{{ row.name }}</span>
				</template>
				<template #cell-type="{ row }">
					<span
						v-if="row.type"
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
						{{ loading ? "Loading customers…" : "No customers yet." }}
						<template v-if="canManage && !loading">
							·
							<button type="button" class="desk-link" @click="openCreate">
								Add one →
							</button>
						</template>
					</div>
				</template>
			</DeskList>

			<PartyFormModal
				:open="modalOpen"
				:title="editing ? 'Edit Customer' : 'New Customer'"
				type-label="Customer type"
				:type-options="TYPE_OPTIONS"
				:initial="editing"
				:server-error="modalError"
				:can-delete="canDelete('customer')"
				@save="onSave"
				@delete="onDelete"
				@close="modalOpen = false"
			/>
		</div>
	</DeskPage>
</template>
