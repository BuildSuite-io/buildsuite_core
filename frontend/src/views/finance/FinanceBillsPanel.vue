<script setup>
// Project Finance › Bills — LIVE unified payables: direct supplier bills (ERPNext Purchase
// Invoice) + submitted Subcontractor Bills. "+ New bill" asks the type and routes to the
// right create screen (supplier bill form here, or the Subcontract module); a row opens the
// matching detail screen. Rendering differs by kind. The list merges two doctypes, so it's a
// custom endpoint + table rather than DocTypeListView (which is single-doctype).
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import {
	listPayables,
	payablesSummary,
	recordSupplierBillPayment,
	recordSupplierAdvance,
	listBillPayAccounts,
	listSupplierBillPaymentModes,
} from "@/data/supplierBillApi";
import { listSuppliers } from "@/data/suppliersApi";
import { useProjectNames } from "@/composables/useProjectNames";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Bills" }];
const router = useRouter();
const { canCreate } = usePermissions();
// "+ New bill" opens a chooser for a Supplier bill (Purchase Invoice) or a Subcontractor
// bill; show the entry point only if the persona can create at least one of them.
const canNewBill = computed(() => canCreate("supplierBill") || canCreate("subcontractorBill"));
const { projectName } = useProjectNames();

const payables = ref([]);
const summary = reactive({ outstanding: 0, retention: 0, advances: 0 });
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		payables.value = await listPayables();
		payablesSummary()
			.then((r) =>
				Object.assign(summary, {
					outstanding: Number(r?.outstanding) || 0,
					retention: Number(r?.retention) || 0,
					advances: Number(r?.advances) || 0,
				})
			)
			.catch(() => {});
	} catch (err) {
		showToast(err.message || "Failed to load bills", "error");
	} finally {
		loading.value = false;
	}
}
load();

// --- filters ---
const search = ref("");
const typeFilter = ref("");
const statusFilter = ref("");
const projectFilter = ref("");
const fromDate = ref("");
const toDate = ref("");
const hasFilters = computed(
	() =>
		search.value ||
		typeFilter.value ||
		statusFilter.value ||
		projectFilter.value ||
		fromDate.value ||
		toDate.value
);
function clearFilters() {
	search.value = "";
	typeFilter.value = "";
	statusFilter.value = "";
	projectFilter.value = "";
	fromDate.value = "";
	toDate.value = "";
}
const rows = computed(() => {
	const term = search.value.trim().toLowerCase();
	return payables.value.filter(
		(r) =>
			(!typeFilter.value || r.kind === typeFilter.value) &&
			(!statusFilter.value || r.status === statusFilter.value) &&
			(!projectFilter.value || r.project === projectFilter.value) &&
			(!fromDate.value || (r.date && r.date >= fromDate.value)) &&
			(!toDate.value || (r.date && r.date <= toDate.value)) &&
			(!term ||
				r.name.toLowerCase().includes(term) ||
				(r.party || "").toLowerCase().includes(term) ||
				(r.project || "").toLowerCase().includes(term))
	);
});

// Client-side pagination over the filtered rows (the list merges two doctypes, so it
// can't use the single-doctype DocTypeListView).
const page = ref(1);
const pageSize = ref(10);
const totalPages = computed(() => Math.max(1, Math.ceil(rows.value.length / pageSize.value)));
const pagedRows = computed(() => {
	const start = (page.value - 1) * pageSize.value;
	return rows.value.slice(start, start + pageSize.value);
});
watch([rows, pageSize], () => {
	if (page.value > totalPages.value) page.value = 1;
});

function aging(row) {
	if (!(Number(row.outstanding) > 0.01) || !row.due_date) return null;
	const d = Math.floor((Date.now() - new Date(row.due_date).getTime()) / 86400000);
	if (d <= 0) return { label: "Not due", cls: "bg-ink-100 text-ink-500" };
	const bucket = d <= 30 ? "0–30" : d <= 60 ? "31–60" : d <= 90 ? "61–90" : "90+";
	const cls = d <= 30 ? "bg-warning-50 text-warning-700" : "bg-danger-50 text-danger-700";
	return { label: `${bucket} d`, cls };
}

function openDetail(row) {
	router.push(
		row.kind === "subcontractor"
			? `/subcontractor-bills/${row.name}`
			: `/project-finance/supplier-bills/${row.name}`
	);
}

// --- new bill (type chooser) ---
const newOpen = ref(false);
function newSupplierBill() {
	newOpen.value = false;
	router.push("/project-finance/supplier-bills/new");
}
function newSubcontractorBill() {
	newOpen.value = false;
	router.push("/subcontractor-bills/new");
}

// --- pay refs ---
const payAccounts = ref([]);
const payModes = ref([]);
async function ensurePayRefs() {
	if (payAccounts.value.length) return;
	try {
		[payAccounts.value, payModes.value] = await Promise.all([
			listBillPayAccounts(),
			listSupplierBillPaymentModes(),
		]);
	} catch {
		/* fall through */
	}
}

// --- pay a supplier bill inline (subcontractor bills are paid from their detail screen) ---
const pay = reactive({
	open: false,
	row: null,
	amount: null,
	pay_from: "",
	date: "",
	mode_of_payment: "",
	reference_no: "",
	saving: false,
});
async function openPay(row) {
	await ensurePayRefs();
	Object.assign(pay, {
		open: true,
		row,
		amount: Number(row.outstanding) || null,
		pay_from:
			payAccounts.value.find((a) => a.account_type === "Bank")?.name ||
			payAccounts.value[0]?.name ||
			"",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	});
}
async function savePay() {
	const amt = Number(pay.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(pay.row.outstanding) + 0.01)
		return showToast(`Can't exceed the outstanding ${fmtINR(pay.row.outstanding)}.`, "error");
	if (!pay.pay_from) return showToast("Pick the account to pay from.", "error");
	pay.saving = true;
	try {
		await recordSupplierBillPayment({
			name: pay.row.name,
			amount: amt,
			date: pay.date,
			mode_of_payment: pay.mode_of_payment || undefined,
			pay_from: pay.pay_from,
			reference_no: pay.reference_no || undefined,
		});
		pay.open = false;
		load();
		showToast("Payment made.");
	} catch (err) {
		showToast(err.message || "Payment failed", "error");
	} finally {
		pay.saving = false;
	}
}

// --- record advance (supplier OR subcontractor) ---
// Subcontractors are Suppliers (supplier_type "Subcontractor"), so both are advanced via
// a Supplier Payment Entry (party_type Supplier). One grouped dropdown lists both, like
// the prototype; the party type is implicit in the supplier record.
const parties = ref([]);
async function ensureParties() {
	if (parties.value.length) return;
	try {
		parties.value = await listSuppliers();
	} catch {
		/* leave empty — the field just shows no options */
	}
}
const advancePartyOptions = computed(() => {
	const suppliers = [];
	const subs = [];
	for (const s of parties.value) {
		const opt = { value: s.name, label: s.supplier_name || s.name };
		if (s.supplier_type === "Subcontractor") subs.push({ ...opt, group: "Subcontractors" });
		else suppliers.push({ ...opt, group: "Suppliers" });
	}
	return [...suppliers, ...subs];
});

const adv = reactive({
	open: false,
	supplier: "",
	amount: null,
	pay_from: "",
	date: "",
	mode_of_payment: "",
	reference_no: "",
	saving: false,
});
async function openAdvance() {
	await Promise.all([ensurePayRefs(), ensureParties()]);
	Object.assign(adv, {
		open: true,
		supplier: "",
		amount: null,
		pay_from:
			payAccounts.value.find((a) => a.account_type === "Bank")?.name ||
			payAccounts.value[0]?.name ||
			"",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	});
}
async function saveAdvance() {
	if (!adv.supplier) return showToast("Pick a party.", "error");
	if (!(Number(adv.amount) > 0)) return showToast("Enter an amount greater than zero.", "error");
	if (!adv.pay_from) return showToast("Pick the account to pay from.", "error");
	adv.saving = true;
	try {
		await recordSupplierAdvance({
			supplier: adv.supplier,
			amount: Number(adv.amount),
			date: adv.date,
			pay_from: adv.pay_from,
			mode_of_payment: adv.mode_of_payment || undefined,
			reference_no: adv.reference_no || undefined,
		});
		adv.open = false;
		load();
		showToast("Advance recorded.");
	} catch (err) {
		showToast(err.message || "Failed to record advance", "error");
	} finally {
		adv.saving = false;
	}
}
</script>

<template>
	<DeskPage title="Bills" :breadcrumbs="breadcrumbs">
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
				<button v-if="canNewBill" type="button" class="desk-save-btn" @click="newOpen = true">
					+ New bill
				</button>
			</div>
		</template>

		<div class="space-y-4">
			<div class="flex items-center gap-6 text-sm">
				<div class="flex items-center gap-1.5">
					<span class="text-ink-500">Payable</span>
					<span class="font-semibold text-ink-900 tabular-nums">{{
						fmtINR(summary.outstanding)
					}}</span>
				</div>
				<div v-if="summary.retention > 0" class="flex items-center gap-1.5">
					<span class="text-ink-500">Retention held</span>
					<span class="font-semibold text-warning-700 tabular-nums">{{
						fmtINR(summary.retention)
					}}</span>
				</div>
				<div v-if="summary.advances > 0" class="flex items-center gap-1.5">
					<span class="text-ink-500">Advances paid</span>
					<span class="font-semibold text-info-700 tabular-nums">{{
						fmtINR(summary.advances)
					}}</span>
				</div>
			</div>

			<div class="flex items-center gap-2 flex-wrap">
				<input
					v-model="search"
					type="text"
					placeholder="Search bill, party, project…"
					class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 w-64 max-w-full"
				/>
				<select
					v-model="typeFilter"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				>
					<option value="">All types</option>
					<option value="supplier">Supplier</option>
					<option value="subcontractor">Subcontractor</option>
				</select>
				<select
					v-model="statusFilter"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				>
					<option value="">All statuses</option>
					<option>Unpaid</option>
					<option>Partly Paid</option>
					<option>Paid</option>
				</select>
				<div class="w-44">
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
					title="From date"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<input
					v-model="toDate"
					type="date"
					title="To date"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<button
					v-if="hasFilters"
					type="button"
					class="text-[11px] text-danger-600 hover:underline"
					@click="clearFilters"
				>
					Clear filters
				</button>
				<span class="text-[11px] text-ink-400 ml-auto"
					>{{ rows.length }} bill{{ rows.length === 1 ? "" : "s" }}</span
				>
			</div>

			<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
				<table v-if="rows.length" class="w-full text-xs" style="min-width: 880px">
					<thead
						class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200"
					>
						<tr>
							<th class="text-left px-3 py-2">Bill</th>
							<th class="text-left px-3 py-2">Party</th>
							<th class="text-left px-3 py-2">Project</th>
							<th class="text-left px-3 py-2">Date</th>
							<th class="text-left px-3 py-2">Due</th>
							<th class="text-left px-3 py-2">Aging</th>
							<th class="text-right px-3 py-2">Total</th>
							<th class="text-right px-3 py-2">Outstanding</th>
							<th class="text-right px-3 py-2">Retention</th>
							<th class="text-left px-3 py-2">Status</th>
							<th class="px-3 py-2"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="r in pagedRows"
							:key="r.kind + r.name"
							class="border-t border-ink-100 hover:bg-brand-50/40 cursor-pointer"
							@click="openDetail(r)"
						>
							<td class="px-3 py-2">
								<div class="flex items-center gap-1.5">
									<span class="font-mono text-[11px] text-ink-500">{{
										r.name
									}}</span>
									<span
										v-if="r.kind === 'subcontractor'"
										class="text-[9px] px-1.5 py-0.5 bg-info-50 text-info-700 rounded-full uppercase tracking-wider whitespace-nowrap"
										>Subcontractor</span
									>
								</div>
							</td>
							<td class="px-3 py-2 text-ink-900">{{ r.party }}</td>
							<td class="px-3 py-2 text-ink-500">
								{{ projectName(r.project) || "—" }}
							</td>
							<td class="px-3 py-2 text-ink-500 whitespace-nowrap">
								{{ fmtDate(r.date) }}
							</td>
							<td class="px-3 py-2 text-ink-500 whitespace-nowrap">
								{{ r.due_date ? fmtDate(r.due_date) : "—" }}
							</td>
							<td class="px-3 py-2">
								<span
									v-if="aging(r)"
									class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap"
									:class="aging(r).cls"
									>{{ aging(r).label }}</span
								><span v-else class="text-ink-300">—</span>
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ fmtINR(r.total) }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums font-medium"
								:class="r.outstanding > 0.01 ? 'text-ink-900' : 'text-ink-400'"
							>
								{{ fmtINR(r.outstanding) }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums"
								:class="r.retention > 0.01 ? 'text-warning-700' : 'text-ink-300'"
							>
								{{ r.retention > 0.01 ? fmtINR(r.retention) : "—" }}
							</td>
							<td class="px-3 py-2"><StatusBadge :status="r.status" size="xs" /></td>
							<td class="px-3 py-2 text-right whitespace-nowrap">
								<button
									v-if="
										r.kind === 'supplier' &&
										r.outstanding > 0.01 &&
										canCreate('advance')
									"
									type="button"
									class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded"
									@click.stop="openPay(r)"
								>
									Pay
								</button>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-else class="px-4 py-12 text-center text-xs text-ink-400 italic">
					{{ loading ? "Loading…" : "No bills yet." }}
				</div>
			</section>

			<!-- Pagination -->
			<div
				v-if="totalPages > 1"
				class="flex items-center justify-between text-xs text-ink-500"
			>
				<span
					>Showing {{ (page - 1) * pageSize + 1 }}–{{
						Math.min(page * pageSize, rows.length)
					}}
					of {{ rows.length }}</span
				>
				<div class="flex items-center gap-2">
					<button
						type="button"
						class="px-2 py-1 border border-ink-200 rounded-md disabled:opacity-40 hover:bg-ink-50"
						:disabled="page <= 1"
						@click="page--"
					>
						← Prev
					</button>
					<span>Page {{ page }} / {{ totalPages }}</span>
					<button
						type="button"
						class="px-2 py-1 border border-ink-200 rounded-md disabled:opacity-40 hover:bg-ink-50"
						:disabled="page >= totalPages"
						@click="page++"
					>
						Next →
					</button>
				</div>
			</div>
		</div>

		<!-- New bill type chooser -->
		<div
			v-if="newOpen"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="newOpen = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">New bill</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="newOpen = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 space-y-2">
					<button
						v-if="canCreate('supplierBill')"
						type="button"
						class="w-full text-left border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 rounded-lg px-4 py-3 transition-colors"
						@click="newSupplierBill"
					>
						<div class="text-sm font-medium text-ink-900">Supplier bill</div>
						<div class="text-[11px] text-ink-500 mt-0.5">
							A direct purchase from a supplier (materials, services) — an ERPNext
							Purchase Invoice.
						</div>
					</button>
					<button
						v-if="canCreate('subcontractorBill')"
						type="button"
						class="w-full text-left border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 rounded-lg px-4 py-3 transition-colors"
						@click="newSubcontractorBill"
					>
						<div class="text-sm font-medium text-ink-900">Subcontractor bill</div>
						<div class="text-[11px] text-ink-500 mt-0.5">
							An RA / work-done bill against a Subcontractor Work Order (with
							retention).
						</div>
					</button>
				</div>
			</div>
		</div>

		<!-- Pay modal (supplier bill) -->
		<div
			v-if="pay.open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="pay.open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Pay bill</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="pay.open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 space-y-3">
					<div class="text-sm text-ink-700">
						Pay <span class="font-medium">{{ pay.row?.party }}</span> against
						<span class="font-mono text-xs">{{ pay.row?.name }}</span
						>. Outstanding
						<span class="font-semibold text-ink-900 tabular-nums">{{
							fmtINR(pay.row?.outstanding)
						}}</span
						>.
					</div>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Amount" required
							><DeskInput v-model.number="pay.amount" type="number" min="0"
						/></DeskField>
						<DeskField label="Date"
							><DeskInput v-model="pay.date" type="date"
						/></DeskField>
					</div>
					<DeskField label="Pay from" required>
						<DeskSelect v-model="pay.pay_from"
							><option value="" disabled>Bank / Cash account…</option>
							<option v-for="a in payAccounts" :key="a.name" :value="a.name">
								{{ a.name }} ({{ a.account_type }})
							</option></DeskSelect
						>
					</DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Mode of payment"
							><DeskSelect v-model="pay.mode_of_payment"
								><option value="">—</option>
								<option v-for="m in payModes" :key="m" :value="m">
									{{ m }}
								</option></DeskSelect
							></DeskField
						>
						<DeskField label="Reference no."
							><DeskInput v-model="pay.reference_no" placeholder="UTR / cheque no."
						/></DeskField>
					</div>
				</div>
				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="pay.open = false"
					>
						Cancel
					</button>
					<button
						type="button"
						class="text-xs desk-save-btn"
						:disabled="pay.saving"
						@click="savePay"
					>
						{{ pay.saving ? "Paying…" : "Record payment" }}
					</button>
				</footer>
			</div>
		</div>

		<!-- Record supplier advance modal -->
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
					<h2 class="text-sm font-semibold text-ink-900">Record advance</h2>
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
						Money paid to a supplier or subcontractor before (or without) a bill — it
						stays on the party's account until a later bill draws it down.
					</p>
					<DeskField label="Party" required>
						<DeskSearchableSelect
							v-model="adv.supplier"
							:options="advancePartyOptions"
							placeholder="Pick a supplier or subcontractor…"
							search-placeholder="Search parties…"
						/>
					</DeskField>
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
					<DeskField label="Pay from" required>
						<DeskSelect v-model="adv.pay_from"
							><option value="" disabled>Bank / Cash account…</option>
							<option v-for="a in payAccounts" :key="a.name" :value="a.name">
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
