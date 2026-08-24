<script setup>
// Project Finance › Invoices — LIVE over ERPNext Sales Invoice (money in). The list is the
// standard DocTypeListView (pagination / sort / filter / search for free); an invoice IS a
// Sales Invoice. Rows show two status badges — submission (Draft/Submitted/Cancelled) and, for
// submitted invoices, the payment status (Unpaid/Overdue/Partly Paid/Paid) — both colour-coded.
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import {
	recordInvoiceReceipt,
	recordCustomerAdvance,
	invoiceReceivablesSummary,
	listDepositAccounts,
	listInvoicePaymentModes,
} from "@/data/invoiceApi";
import { useProjectNames } from "@/composables/useProjectNames";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Invoices" }];
const router = useRouter();
const { canCreate } = usePermissions();
const { projectName } = useProjectNames();
const activeCompany = useActiveCompany();
const baseFilters = computed(() =>
	activeCompany.value ? [["company", "=", activeCompany.value]] : []
);

// The list is a doctype resource; bump this to force a refresh after receive/advance.
const listKey = ref(0);
function refreshList() {
	listKey.value += 1;
	loadSummary();
}

// --- header summary (across all invoices, not just the page) ---
const summary = reactive({ outstanding: 0, advances: 0 });
async function loadSummary() {
	try {
		const r = await invoiceReceivablesSummary();
		summary.outstanding = Number(r?.outstanding) || 0;
		summary.advances = Number(r?.advances) || 0;
	} catch {
		/* ignore */
	}
}
loadSummary();

// --- status derivation from the native Sales Invoice `status` ---
function submissionOf(s) {
	if (s === "Draft") return "Draft";
	if (s === "Cancelled") return "Cancelled";
	return "Submitted";
}
function paymentOf(s) {
	return s === "Draft" || s === "Cancelled" ? null : s; // Unpaid / Overdue / Partly Paid / Paid
}
function canReceive(row) {
	return submissionOf(row.status) === "Submitted" && Number(row.outstanding_amount) > 0.01;
}

// --- aging (submitted + still owed) ---
function aging(row) {
	if (submissionOf(row.status) !== "Submitted" || !(Number(row.outstanding_amount) > 0.01))
		return null;
	if (!row.due_date) return null;
	const d = Math.floor((Date.now() - new Date(row.due_date).getTime()) / 86400000);
	if (d <= 0) return { label: "Not due", cls: "bg-ink-100 text-ink-500" };
	const bucket = d <= 30 ? "0–30" : d <= 60 ? "31–60" : d <= 90 ? "61–90" : "90+";
	const cls = d <= 30 ? "bg-warning-50 text-warning-700" : "bg-danger-50 text-danger-700";
	return { label: `${bucket} d`, cls };
}

const statusFilter = ref("");
const projectFilter = ref("");
const fromDate = ref("");
const toDate = ref("");
const filterValues = computed(() => ({
	status: statusFilter.value,
	project: projectFilter.value,
	fromDate: fromDate.value,
	toDate: toDate.value,
}));
// Map filter keys → Sales Invoice fields; the two dates bracket posting_date.
const filterFieldMap = {
	status: "status",
	project: "project",
	fromDate: { field: "posting_date", op: ">=" },
	toDate: { field: "posting_date", op: "<=" },
};

function openDetail(row) {
	router.push(`/project-finance/invoices/${row.name}`);
}
function openNew() {
	router.push("/project-finance/invoices/new");
}

// --- receive payment ---
const depositAccounts = ref([]);
const payModes = ref([]);
async function ensurePayRefs() {
	if (depositAccounts.value.length) return;
	try {
		[depositAccounts.value, payModes.value] = await Promise.all([
			listDepositAccounts(),
			listInvoicePaymentModes(),
		]);
	} catch {
		/* fall through */
	}
}
const rec = reactive({
	open: false,
	inv: null,
	amount: null,
	deposit_to: "",
	date: "",
	mode_of_payment: "",
	reference_no: "",
	saving: false,
});
async function openReceive(row) {
	await ensurePayRefs();
	Object.assign(rec, {
		open: true,
		inv: {
			name: row.name,
			customer_name: row.customer_name,
			outstanding: Number(row.outstanding_amount) || 0,
		},
		amount: Number(row.outstanding_amount) || null,
		deposit_to:
			depositAccounts.value.find((a) => a.account_type === "Bank")?.name ||
			depositAccounts.value[0]?.name ||
			"",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	});
}
async function saveReceive() {
	const amt = Number(rec.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(rec.inv.outstanding) + 0.01)
		return showToast(`Can't exceed the outstanding ${fmtINR(rec.inv.outstanding)}.`, "error");
	if (!rec.deposit_to) return showToast("Pick the account to deposit into.", "error");
	rec.saving = true;
	try {
		await recordInvoiceReceipt({
			name: rec.inv.name,
			amount: amt,
			date: rec.date,
			mode_of_payment: rec.mode_of_payment || undefined,
			deposit_to: rec.deposit_to,
			reference_no: rec.reference_no || undefined,
		});
		rec.open = false;
		refreshList();
		showToast("Payment received.");
	} catch (err) {
		showToast(err.message || "Receipt failed", "error");
	} finally {
		rec.saving = false;
	}
}

// --- record customer advance (on-account receipt) ---
const adv = reactive({
	open: false,
	customer: "",
	amount: null,
	deposit_to: "",
	date: "",
	mode_of_payment: "",
	reference_no: "",
	saving: false,
});
async function openAdvance() {
	await ensurePayRefs();
	Object.assign(adv, {
		open: true,
		customer: "",
		amount: null,
		deposit_to:
			depositAccounts.value.find((a) => a.account_type === "Bank")?.name ||
			depositAccounts.value[0]?.name ||
			"",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	});
}
async function saveAdvance() {
	if (!adv.customer) return showToast("Pick a customer.", "error");
	if (!(Number(adv.amount) > 0)) return showToast("Enter an amount greater than zero.", "error");
	if (!adv.deposit_to) return showToast("Pick the account to deposit into.", "error");
	adv.saving = true;
	try {
		await recordCustomerAdvance({
			customer: adv.customer,
			amount: Number(adv.amount),
			date: adv.date,
			deposit_to: adv.deposit_to,
			mode_of_payment: adv.mode_of_payment || undefined,
			reference_no: adv.reference_no || undefined,
		});
		adv.open = false;
		refreshList();
		showToast("Advance recorded.");
	} catch (err) {
		showToast(err.message || "Failed to record advance", "error");
	} finally {
		adv.saving = false;
	}
}
</script>

<template>
	<DeskPage title="Invoices" :breadcrumbs="breadcrumbs">
		<template #actions>
			<div class="flex items-center gap-2">
				<button
					v-if="canCreate('advance')"
					type="button"
					class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
					@click="openAdvance"
				>
					Record advance
				</button>
				<button v-if="canCreate('salesInvoice')" type="button" class="desk-save-btn" @click="openNew">+ New invoice</button>
			</div>
		</template>

		<div class="space-y-4">
			<div class="flex items-center gap-6 text-sm">
				<div class="flex items-center gap-1.5">
					<span class="text-ink-500">Outstanding</span>
					<span class="font-semibold text-ink-900 tabular-nums">{{
						fmtINR(summary.outstanding)
					}}</span>
				</div>
				<div v-if="summary.advances > 0" class="flex items-center gap-1.5">
					<span class="text-ink-500">Advances held</span>
					<span class="font-semibold text-info-700 tabular-nums">{{
						fmtINR(summary.advances)
					}}</span>
				</div>
			</div>

			<DocTypeListView
				v-if="activeCompany"
				:key="listKey"
				doctype="Sales Invoice"
				:field-order="[
					'customer_name',
					'project',
					'posting_date',
					'due_date',
					'grand_total',
					'outstanding_amount',
					'status',
				]"
				:columns="[
					{ key: 'name', label: 'Invoice' },
					{ key: 'customer_name', label: 'Customer' },
					{ key: 'project', label: 'Project' },
					{ key: 'posting_date', label: 'Date' },
					{ key: 'due_date', label: 'Due' },
					{
						key: 'aging',
						label: 'Aging',
						fields: ['due_date', 'outstanding_amount', 'status'],
					},
					{ key: 'grand_total', label: 'Total', align: 'right' },
					{ key: 'outstanding_amount', label: 'Outstanding', align: 'right' },
					{ key: 'status', label: 'Status', fields: ['status', 'outstanding_amount'] },
					{ key: 'actions', label: '', align: 'right' },
				]"
				:search-fields="['name', 'customer_name']"
				:base-filters="baseFilters"
				:filter-values="filterValues"
				:filter-field-map="filterFieldMap"
				cache-key="buildsuite-invoice-list"
				row-key="name"
				initial-order-by="posting_date desc"
				search-placeholder="Search invoice, customer…"
				empty-message="No invoices yet."
				@row-click="openDetail"
			>
				<template #filter-chips>
					<DeskSelect v-model="statusFilter" class="!w-40">
						<option value="">Status: Any</option>
						<option>Draft</option>
						<option>Unpaid</option>
						<option>Overdue</option>
						<option>Partly Paid</option>
						<option>Paid</option>
						<option>Cancelled</option>
					</DeskSelect>
					<div class="w-48">
						<DeskLinkPicker
							v-model="projectFilter"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							placeholder="All projects"
						/>
					</div>
					<input
						v-model="fromDate"
						type="date"
						title="From date (posting date)"
						class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
					/>
					<input
						v-model="toDate"
						type="date"
						title="To date (posting date)"
						class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
					/>
				</template>

				<template #cell-name="{ row }"
					><span class="font-mono text-[11px] text-ink-500">{{
						row.name
					}}</span></template
				>
				<template #cell-customer_name="{ row }"
					><span class="text-ink-900">{{ row.customer_name }}</span></template
				>
				<template #cell-project="{ row }"
					><span class="text-ink-500">{{
						projectName(row.project) || "—"
					}}</span></template
				>
				<template #cell-posting_date="{ row }"
					><span class="text-ink-500 whitespace-nowrap">{{
						fmtDate(row.posting_date)
					}}</span></template
				>
				<template #cell-due_date="{ row }"
					><span class="text-ink-500 whitespace-nowrap">{{
						fmtDate(row.due_date)
					}}</span></template
				>
				<template #cell-aging="{ row }">
					<span
						v-if="aging(row)"
						class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap"
						:class="aging(row).cls"
						>{{ aging(row).label }}</span
					>
					<span v-else class="text-ink-300">—</span>
				</template>
				<template #cell-grand_total="{ row }"
					><span class="tabular-nums text-ink-900">{{
						fmtINR(row.grand_total)
					}}</span></template
				>
				<template #cell-outstanding_amount="{ row }"
					><span
						class="tabular-nums font-medium"
						:class="
							Number(row.outstanding_amount) > 0.01 ? 'text-ink-900' : 'text-ink-400'
						"
						>{{ fmtINR(row.outstanding_amount) }}</span
					></template
				>
				<template #cell-status="{ row }">
					<div class="flex items-center gap-1.5">
						<StatusBadge :status="submissionOf(row.status)" size="xs" />
						<StatusBadge
							v-if="paymentOf(row.status)"
							:status="paymentOf(row.status)"
							size="xs"
						/>
					</div>
				</template>
				<template #cell-actions="{ row }">
					<button
						v-if="canReceive(row)"
						type="button"
						class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded"
						@click.stop="openReceive(row)"
					>
						Receive
					</button>
				</template>
			</DocTypeListView>
		</div>

		<!-- Receive payment modal -->
		<div
			v-if="rec.open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="rec.open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Receive payment</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="rec.open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 space-y-3">
					<div class="text-sm text-ink-700">
						From <span class="font-medium">{{ rec.inv?.customer_name }}</span> against
						<span class="font-mono text-xs">{{ rec.inv?.name }}</span
						>. Outstanding
						<span class="font-semibold text-ink-900 tabular-nums">{{
							fmtINR(rec.inv?.outstanding)
						}}</span
						>.
					</div>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Amount" required
							><DeskInput v-model.number="rec.amount" type="number" min="0"
						/></DeskField>
						<DeskField label="Date"
							><DeskInput v-model="rec.date" type="date"
						/></DeskField>
					</div>
					<DeskField label="Deposit into" required>
						<DeskSelect v-model="rec.deposit_to"
							><option value="" disabled>Bank / Cash account…</option>
							<option v-for="a in depositAccounts" :key="a.name" :value="a.name">
								{{ a.name }} ({{ a.account_type }})
							</option></DeskSelect
						>
					</DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Mode of payment"
							><DeskSelect v-model="rec.mode_of_payment"
								><option value="">—</option>
								<option v-for="m in payModes" :key="m" :value="m">
									{{ m }}
								</option></DeskSelect
							></DeskField
						>
						<DeskField label="Reference no."
							><DeskInput v-model="rec.reference_no" placeholder="UTR / cheque no."
						/></DeskField>
					</div>
				</div>
				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="rec.open = false"
					>
						Cancel
					</button>
					<button
						type="button"
						class="text-xs desk-save-btn"
						:disabled="rec.saving"
						@click="saveReceive"
					>
						{{ rec.saving ? "Receiving…" : "Record receipt" }}
					</button>
				</footer>
			</div>
		</div>

		<!-- Record customer advance modal -->
		<div
			v-if="adv.open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="adv.open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Record customer advance</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="adv.open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 space-y-3">
					<p class="text-[11px] text-ink-500">
						Money received before (or without) an invoice — it stays on the customer's
						account until a later invoice draws it down.
					</p>
					<DeskField label="Customer" required
						><DeskLinkPicker
							v-model="adv.customer"
							doctype="Customer"
							label-field="customer_name"
							value-field="name"
							placeholder="Pick a customer…"
					/></DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Amount" required
							><DeskInput
								v-model.number="adv.amount"
								type="number"
								min="0"
								placeholder="0"
						/></DeskField>
						<DeskField label="Date"
							><DeskInput v-model="adv.date" type="date"
						/></DeskField>
					</div>
					<DeskField label="Deposit into" required>
						<DeskSelect v-model="adv.deposit_to"
							><option value="" disabled>Bank / Cash account…</option>
							<option v-for="a in depositAccounts" :key="a.name" :value="a.name">
								{{ a.name }} ({{ a.account_type }})
							</option></DeskSelect
						>
					</DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Mode of payment"
							><DeskSelect v-model="adv.mode_of_payment"
								><option value="">—</option>
								<option v-for="m in payModes" :key="m" :value="m">
									{{ m }}
								</option></DeskSelect
							></DeskField
						>
						<DeskField label="Reference no."
							><DeskInput v-model="adv.reference_no" placeholder="UTR / cheque no."
						/></DeskField>
					</div>
				</div>
				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="adv.open = false"
					>
						Cancel
					</button>
					<button
						type="button"
						class="text-xs desk-save-btn"
						:disabled="adv.saving"
						@click="saveAdvance"
					>
						{{ adv.saving ? "Recording…" : "Record advance" }}
					</button>
				</footer>
			</div>
		</div>
	</DeskPage>
</template>
