<script setup>
// S229 — Settings › Bank & Cash Accounts. Master for the finance accounts that surface
// across Project Finance (Overview card, disburse / receive / pay modals, Cash & Bank
// statement). Backed by ERPNext Account (Bank / Cash) — balances are DERIVED (opening
// balance ± movements), so only the opening balance is editable here.
import { ref, computed, onMounted } from "vue";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { fmtINR } from "@/utils/format";
import { useConfirm } from "@/composables/useConfirm";
import {
	listFinanceAccounts,
	saveFinanceAccount,
	deleteFinanceAccount,
} from "@/data/financeAccountApi";

const store = useDataStore();
const confirmDialog = useConfirm();

const canManage = computed(() => store.isAdmin);

const accounts = ref([]);
const loading = ref(true);
const loadError = ref("");

async function reload() {
	loading.value = true;
	loadError.value = "";
	try {
		accounts.value = await listFinanceAccounts();
	} catch (err) {
		loadError.value = err.message || "Failed to load accounts.";
	} finally {
		loading.value = false;
	}
}
onMounted(reload);

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Bank & Cash Accounts" },
];

// --- add/edit modal ---
const modalOpen = ref(false);
const editingId = ref(null);
const form = ref(blank());
const error = ref("");
const saving = ref(false);

function blank() {
	return { name: "", type: "Bank", account_no: "", opening_balance: null };
}
function openNew() {
	editingId.value = null;
	form.value = blank();
	error.value = "";
	modalOpen.value = true;
}
function openEdit(acc) {
	editingId.value = acc.id;
	form.value = {
		name: acc.name,
		type: acc.type,
		account_no: acc.account_no || "",
		opening_balance: acc.opening_balance,
	};
	error.value = "";
	modalOpen.value = true;
}
async function save() {
	if (!form.value.name.trim()) {
		error.value = "Account name is required.";
		return;
	}
	saving.value = true;
	error.value = "";
	try {
		await saveFinanceAccount({
			account: editingId.value || undefined,
			name: form.value.name.trim(),
			type: form.value.type,
			account_no: form.value.account_no || "",
			opening_balance: form.value.opening_balance || 0,
		});
		modalOpen.value = false;
		await reload();
	} catch (err) {
		error.value = err.message || "Failed to save the account.";
	} finally {
		saving.value = false;
	}
}
async function del(acc) {
	const ok = await confirmDialog({
		title: "Delete account?",
		message: `Delete "${acc.name}"? Accounts with recorded movements can't be deleted.`,
		confirmLabel: "Delete",
		danger: true,
	});
	if (!ok) return;
	try {
		await deleteFinanceAccount(acc.id);
		await reload();
	} catch (err) {
		loadError.value = err.message || "Failed to delete the account.";
	}
}
</script>

<template>
	<DeskPage
		title="Bank & Cash Accounts"
		subtitle="Accounts shown across Project Finance — balances derive from movements"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button v-if="canManage" type="button" class="desk-save-btn !text-xs" @click="openNew">
				+ New Account
			</button>
		</template>

		<div
			v-if="!canManage"
			class="bg-warning-50 border border-warning-200 rounded-lg px-4 py-6 text-sm text-warning-700"
		>
			You don't have permission to manage finance accounts.
		</div>

		<template v-else>
			<div
				v-if="loadError"
				class="bg-danger-50 border border-danger-200 rounded-lg px-4 py-4 text-sm text-danger-700 mb-3"
			>
				{{ loadError }}
			</div>

			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<table class="w-full text-xs">
					<thead
						class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50"
					>
						<tr>
							<th class="text-left px-4 py-2">Account</th>
							<th class="text-left px-4 py-2">Type</th>
							<th class="text-left px-4 py-2">Account no.</th>
							<th class="text-right px-4 py-2">Opening balance</th>
							<th class="text-right px-4 py-2">Current balance</th>
							<th class="px-4 py-2"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="acc in accounts"
							:key="acc.id"
							class="border-b border-ink-100 last:border-0 hover:bg-brand-50/30"
						>
							<td class="px-4 py-2.5">
								<div class="flex items-center gap-2">
									<div
										class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
										:class="
											acc.type === 'Bank'
												? 'bg-info-50 text-info-700'
												: 'bg-success-50 text-success-700'
										"
									>
										<svg
											width="16"
											height="16"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.75"
											stroke-linecap="round"
											stroke-linejoin="round"
											v-html="
												getWorkspaceIconPath(
													acc.type === 'Bank'
														? 'building-2'
														: 'hand-coins'
												)
											"
										></svg>
									</div>
									<span class="text-ink-900 font-medium">{{ acc.name }}</span>
								</div>
							</td>
							<td class="px-4 py-2.5">
								<span
									class="text-[10px] px-1.5 py-0.5 rounded-full"
									:class="
										acc.type === 'Bank'
											? 'bg-info-50 text-info-700'
											: 'bg-success-50 text-success-700'
									"
									>{{ acc.type }}</span
								>
							</td>
							<td class="px-4 py-2.5 font-mono text-ink-500">
								{{ acc.account_no || "—" }}
							</td>
							<td class="px-4 py-2.5 text-right tabular-nums text-ink-700">
								{{ fmtINR(acc.opening_balance) }}
							</td>
							<td
								class="px-4 py-2.5 text-right tabular-nums font-semibold text-ink-900"
							>
								{{ fmtINR(acc.current_balance) }}
							</td>
							<td class="px-4 py-2.5 text-right whitespace-nowrap">
								<button
									type="button"
									class="text-[11px] px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
									@click="openEdit(acc)"
								>
									Edit
								</button>
								<button
									type="button"
									class="text-[11px] px-2 py-1 ml-1 text-danger-600 hover:underline"
									@click="del(acc)"
								>
									Delete
								</button>
							</td>
						</tr>
						<tr v-if="loading">
							<td colspan="6" class="px-4 py-10 text-center text-xs text-ink-400">
								Loading accounts…
							</td>
						</tr>
						<tr v-else-if="!accounts.length">
							<td
								colspan="6"
								class="px-4 py-10 text-center text-xs text-ink-400 italic"
							>
								No accounts yet — add your bank and cash accounts.
							</td>
						</tr>
					</tbody>
				</table>
			</section>

			<p class="text-[11px] text-ink-400 mt-3">
				Current balance = opening balance ± every recorded movement (receipts, payments,
				disbursements, advances). Accounts with history can't be deleted.
			</p>
		</template>

		<!-- Add/edit modal -->
		<Teleport to="body">
			<div
				v-if="modalOpen"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6"
				@click.self="modalOpen = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-md shadow-fp-lg rounded-xl"
					@click.stop
				>
					<header
						class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
					>
						<h2 class="text-sm font-semibold text-ink-900">
							{{ editingId ? "Edit account" : "New account" }}
						</h2>
						<button
							type="button"
							class="text-ink-400 hover:text-ink-900"
							@click="modalOpen = false"
						>
							✕
						</button>
					</header>
					<div class="px-4 py-4 space-y-3">
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Account name <span class="text-danger-600">*</span></label
							>
							<input
								v-model="form.name"
								type="text"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
								placeholder="e.g. ICICI Current A/c"
							/>
						</div>
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label
									class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
									>Type</label
								>
								<select
									v-model="form.type"
									:disabled="!!editingId"
									class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 disabled:bg-ink-50 disabled:text-ink-400"
								>
									<option value="Bank">Bank</option>
									<option value="Cash">Cash</option>
									<option value="Petty Cash">Petty Cash</option>
								</select>
							</div>
							<div>
								<label
									class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
									>Opening balance</label
								>
								<input
									v-model.number="form.opening_balance"
									type="number"
									class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md text-right focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
									placeholder="0"
								/>
							</div>
						</div>
						<div v-if="form.type === 'Bank'">
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Account no.
								<span class="text-ink-400 normal-case">(optional)</span></label
							>
							<input
								v-model="form.account_no"
								type="text"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md font-mono focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
						</div>
						<div v-if="error" class="text-[11px] text-danger-600">{{ error }}</div>
					</div>
					<footer
						class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
							@click="modalOpen = false"
						>
							Cancel
						</button>
						<button
							type="button"
							class="text-xs px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-md disabled:opacity-50"
							:disabled="saving"
							@click="save"
						>
							{{ saving ? "Saving…" : "Save" }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>
</template>
