<script setup>
// Project Finance › Financial Overview. Mirrors the prototype's richer overview:
// a clickable KPI strip (cash & bank · receivables · payables · retention · net
// position), cash/bank accounts, a "needs attention" action queue, quick actions,
// receivable/payable chase-lists and the latest money movements. Finance is
// client-side dummy data for now (except Petty Cash, which is live) — everything
// here derives from useFinanceMock; the KPI links jump to each section.
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { usePermissions } from "@/composables/usePermissions";
import { fmtDate, fmtINR, fmtCompactINR } from "@/utils/format";

const fin = useFinanceMock();
const router = useRouter();
const { canCreate } = usePermissions();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Overview" }];

function go(section) {
	router.push(`/project-finance/${section}`);
}
function daysOverdue(due) {
	if (!due) return 0;
	return Math.round((Date.now() - new Date(due).getTime()) / 86400000);
}

// ---- KPIs ----
const accounts = computed(() => fin.sortedFinanceAccounts || []);
const cashBankAccounts = computed(() => accounts.value.filter((a) => a.type !== "Petty Cash"));
const totalCashBank = computed(() => fin.totalCashBank);
const receivable = computed(() => fin.totalReceivable);
const overdueCount = computed(
	() => fin.openInvoices.filter((i) => daysOverdue(i.due_date) > 0).length
);
const payable = computed(() => fin.totalPayable);
const retention = computed(() => fin.retentionHeld);
const netPosition = computed(() => totalCashBank.value + receivable.value - payable.value);

// ---- Needs attention (each row jumps to its queue) ----
const draftInvoices = computed(
	() => fin.invoices.filter((i) => (i.workflow_state || "Submitted") === "Draft").length
);
const attention = computed(() => {
	const out = [];
	const ex = fin.expensesToVerify.length;
	if (ex > 0)
		out.push({
			text: `${ex} expense${ex === 1 ? "" : "s"} awaiting submit`,
			section: "expenses",
			tone: "warning",
		});
	if (draftInvoices.value > 0)
		out.push({
			text: `${draftInvoices.value} draft invoice${
				draftInvoices.value === 1 ? "" : "s"
			} not yet posted`,
			section: "invoices",
			tone: "info",
		});
	if (overdueCount.value > 0)
		out.push({
			text: `${overdueCount.value} invoice${
				overdueCount.value === 1 ? "" : "s"
			} overdue — chase receivables`,
			section: "invoices",
			tone: "danger",
		});
	return out;
});

// ---- Chase lists ----
const topOverdue = computed(() =>
	fin.openInvoices
		.map((i) => ({
			id: i.id,
			party: fin.customerById(i.customer)?.name || i.customer,
			amount: fin.invoiceOutstanding(i),
			days: daysOverdue(i.due_date),
		}))
		.filter((r) => r.days > 0)
		.sort((a, b) => b.days - a.days)
		.slice(0, 4)
);
const topPayables = computed(() =>
	fin.unifiedPayables
		.filter((p) => p.outstanding > 0.01)
		.sort((a, b) => (a.due_date || "").localeCompare(b.due_date || ""))
		.slice(0, 4)
);

// ---- Recent movements (top 5 across all documents) ----
const recentMovements = computed(() => fin.allPayments.slice(0, 5));

const quickActions = [
	{ key: "new-expense", section: "expenses", icon: "receipt", label: "New Expense", caps: ["expense"] },
	{ key: "req-petty", section: "petty-cash", icon: "hand-coins", label: "Request Petty Cash", caps: ["pettyCash"] },
	{ key: "new-invoice", section: "invoices", icon: "file-text", label: "New Invoice", caps: ["salesInvoice"] },
	{ key: "new-bill", section: "bills", icon: "banknote", label: "New Bill", caps: ["supplierBill", "subcontractorBill"] },
];
// Only surface a quick action the persona can actually act on (its create capability).
const visibleQuickActions = computed(() =>
	quickActions.filter((qa) => qa.caps.some((c) => canCreate(c)))
);

const toneDot = {
	danger: "bg-danger-500",
	warning: "bg-warning-500",
	info: "bg-info-500",
};
</script>

<template>
	<DeskPage title="Finance Overview" :breadcrumbs="breadcrumbs">
		<div class="space-y-5">
			<!-- ===== KPI strip ===== -->
			<div class="grid grid-cols-2 md:grid-cols-5 gap-2">
				<button
					type="button"
					class="bg-white border border-ink-200 hover:border-brand-400 px-3 py-2.5 rounded-lg text-left transition-colors"
					@click="go('payments')"
				>
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Cash &amp; bank
					</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-0.5">
						{{ fmtCompactINR(totalCashBank) }}
					</div>
					<div class="text-[10px] text-ink-500">
						{{ cashBankAccounts.length }} account{{
							cashBankAccounts.length === 1 ? "" : "s"
						}}
					</div>
				</button>
				<button
					type="button"
					class="bg-white border border-ink-200 hover:border-brand-400 px-3 py-2.5 rounded-lg text-left transition-colors"
					@click="go('invoices')"
				>
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Receivables
					</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-0.5">
						{{ fmtCompactINR(receivable) }}
					</div>
					<div
						class="text-[10px]"
						:class="overdueCount > 0 ? 'text-danger-700 font-medium' : 'text-ink-500'"
					>
						{{ overdueCount > 0 ? `${overdueCount} overdue` : "none overdue" }}
					</div>
				</button>
				<button
					type="button"
					class="bg-white border border-ink-200 hover:border-brand-400 px-3 py-2.5 rounded-lg text-left transition-colors"
					@click="go('bills')"
				>
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Payables
					</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-0.5">
						{{ fmtCompactINR(payable) }}
					</div>
					<div class="text-[10px] text-ink-500">
						retention {{ fmtCompactINR(retention) }}
					</div>
				</button>
				<button
					type="button"
					class="bg-white border border-ink-200 hover:border-brand-400 px-3 py-2.5 rounded-lg text-left transition-colors"
					@click="go('bills')"
				>
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						Retention held
					</div>
					<div class="text-lg font-semibold text-warning-700 tabular-nums mt-0.5">
						{{ fmtCompactINR(retention) }}
					</div>
					<div class="text-[10px] text-ink-500">withheld on sub-bills</div>
				</button>
				<button
					type="button"
					class="px-3 py-2.5 rounded-lg text-left transition-colors border"
					:class="
						netPosition >= 0
							? 'bg-brand-50 border-brand-200 hover:border-brand-400'
							: 'bg-danger-50 border-danger-200 hover:border-danger-400'
					"
					@click="router.push('/project-finance/report/position')"
				>
					<div
						class="text-[10px] uppercase tracking-wider font-medium"
						:class="netPosition >= 0 ? 'text-brand-700' : 'text-danger-700'"
					>
						Net position
					</div>
					<div class="text-lg font-semibold text-ink-900 tabular-nums mt-0.5">
						{{ fmtCompactINR(netPosition) }}
					</div>
					<div class="text-[10px] text-ink-500">have − owe · report →</div>
				</button>
			</div>

			<!-- ===== Accounts + Needs attention + Quick actions ===== -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
				<!-- Cash & Bank accounts -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div
						class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between"
					>
						<h3
							class="text-xs uppercase tracking-wider font-semibold text-ink-700 flex items-center gap-1.5"
						>
							<svg
								class="w-3.5 h-3.5 text-ink-400"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
								v-html="getWorkspaceIconPath('wallet')"
							/>
							Accounts
						</h3>
						<RouterLink
							to="/settings/finance-accounts"
							class="text-[11px] text-brand-700 hover:underline"
							>Manage</RouterLink
						>
					</div>
					<div class="divide-y divide-ink-100">
						<div
							v-for="acc in accounts"
							:key="acc.id"
							class="px-4 py-2.5 flex items-center justify-between"
						>
							<div class="flex items-center gap-2.5 min-w-0">
								<div
									class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
									:class="
										acc.type === 'Bank'
											? 'bg-info-50 text-info-700'
											: 'bg-success-50 text-success-700'
									"
								>
									<svg
										class="w-4 h-4"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.75"
										stroke-linecap="round"
										stroke-linejoin="round"
										v-html="
											getWorkspaceIconPath(
												acc.type === 'Bank' ? 'building-2' : 'hand-coins'
											)
										"
									/>
								</div>
								<div class="min-w-0">
									<div class="text-xs text-ink-900 font-medium truncate">
										{{ acc.name }}
									</div>
									<div class="text-[10px] text-ink-500">{{ acc.type }}</div>
								</div>
							</div>
							<div class="text-sm font-semibold text-ink-900 tabular-nums">
								{{ fmtINR(fin.accountBalance(acc.id)) }}
							</div>
						</div>
						<div
							v-if="!accounts.length"
							class="px-4 py-8 text-center text-xs text-ink-400 italic"
						>
							No accounts defined.
						</div>
					</div>
				</section>

				<!-- Needs attention -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div class="px-4 py-2.5 bg-ink-50 border-b border-ink-200">
						<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
							Needs attention
						</h3>
					</div>
					<div v-if="attention.length" class="divide-y divide-ink-100">
						<button
							v-for="(a, i) in attention"
							:key="i"
							type="button"
							class="w-full text-left px-4 py-2.5 flex items-center gap-2 hover:bg-brand-50/40 transition-colors"
							@click="go(a.section)"
						>
							<span
								class="w-1.5 h-1.5 rounded-full flex-shrink-0"
								:class="toneDot[a.tone]"
							></span>
							<span class="text-xs text-ink-800 flex-1">{{ a.text }}</span>
							<span class="text-ink-400 text-xs">→</span>
						</button>
					</div>
					<div
						v-else
						class="px-4 py-8 text-center text-xs text-success-700 flex items-center justify-center gap-1.5"
					>
						<svg
							class="w-3.5 h-3.5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							v-html="getWorkspaceIconPath('check-circle')"
						/>
						All clear — nothing pending.
					</div>
				</section>

				<!-- Quick actions -->
				<section
					v-if="visibleQuickActions.length"
					class="bg-white border border-ink-200 rounded-lg overflow-hidden"
				>
					<div class="px-4 py-2.5 bg-ink-50 border-b border-ink-200">
						<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
							Quick actions
						</h3>
					</div>
					<div class="p-3 grid grid-cols-2 gap-2">
						<button
							v-for="qa in visibleQuickActions"
							:key="qa.key"
							type="button"
							class="border border-ink-200 hover:border-brand-400 hover:shadow-sm p-2.5 rounded-lg text-left transition-all group flex items-center gap-2"
							@click="go(qa.section)"
						>
							<div
								class="w-8 h-8 rounded-lg bg-ink-50 text-ink-600 group-hover:bg-brand-50 group-hover:text-brand-700 flex items-center justify-center flex-shrink-0 transition-colors"
							>
								<svg
									class="w-4 h-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
									v-html="getWorkspaceIconPath(qa.icon)"
								/>
							</div>
							<span class="text-xs font-medium text-ink-900 leading-tight">{{
								qa.label
							}}</span>
						</button>
					</div>
				</section>
			</div>

			<!-- ===== Chase lists ===== -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<!-- Overdue receivables -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div
						class="px-4 py-2.5 bg-ink-50 border-b border-ink-200 flex items-center justify-between"
					>
						<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
							Overdue receivables
						</h3>
						<button
							type="button"
							class="text-[11px] text-brand-700 hover:underline"
							@click="go('invoices')"
						>
							All invoices →
						</button>
					</div>
					<div v-if="topOverdue.length" class="divide-y divide-ink-100">
						<div
							v-for="r in topOverdue"
							:key="r.id"
							class="px-4 py-2.5 flex items-center justify-between gap-2"
						>
							<div class="min-w-0">
								<div class="text-xs text-ink-900 font-medium truncate">
									{{ r.party }}
								</div>
								<div class="text-[10px] text-ink-400 font-mono">{{ r.id }}</div>
							</div>
							<div class="text-right flex-shrink-0">
								<div class="text-xs font-semibold text-ink-900 tabular-nums">
									{{ fmtINR(r.amount) }}
								</div>
								<div class="text-[10px] text-danger-700 font-medium">
									{{ r.days }}d overdue
								</div>
							</div>
						</div>
					</div>
					<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
						Nothing overdue.
					</div>
				</section>

				<!-- Payables due -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div
						class="px-4 py-2.5 bg-ink-50 border-b border-ink-200 flex items-center justify-between"
					>
						<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
							Payables due
						</h3>
						<button
							type="button"
							class="text-[11px] text-brand-700 hover:underline"
							@click="go('bills')"
						>
							All bills →
						</button>
					</div>
					<div v-if="topPayables.length" class="divide-y divide-ink-100">
						<div
							v-for="p in topPayables"
							:key="p.kind + p.id"
							class="px-4 py-2.5 flex items-center justify-between gap-2"
						>
							<div class="min-w-0">
								<div class="flex items-center gap-1.5">
									<div class="text-xs text-ink-900 font-medium truncate">
										{{ fin.supplierById(p.supplier)?.name || p.supplier }}
									</div>
									<span
										v-if="p.kind === 'subcontractor'"
										class="text-[9px] px-1.5 py-0.5 bg-info-50 text-info-700 rounded-full uppercase tracking-wider flex-shrink-0"
										>Sub</span
									>
								</div>
								<div class="text-[10px] text-ink-400">
									due {{ fmtDate(p.due_date) }}
								</div>
							</div>
							<div
								class="text-xs font-semibold text-ink-900 tabular-nums flex-shrink-0"
							>
								{{ fmtINR(p.outstanding) }}
							</div>
						</div>
					</div>
					<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
						Nothing payable.
					</div>
				</section>
			</div>

			<!-- ===== Recent movements ===== -->
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div
					class="px-4 py-2.5 bg-ink-50 border-b border-ink-200 flex items-center justify-between"
				>
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Recent transactions
					</h3>
					<button
						type="button"
						class="text-[11px] text-brand-700 hover:underline"
						@click="go('payments')"
					>
						All payments →
					</button>
				</div>
				<div v-if="recentMovements.length" class="divide-y divide-ink-100">
					<div
						v-for="(m, i) in recentMovements"
						:key="i"
						class="px-4 py-2.5 flex items-center gap-3"
					>
						<span
							class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap flex-shrink-0"
							:class="
								m.dir === 'in'
									? 'bg-success-50 text-success-700'
									: 'bg-warning-50 text-warning-700'
							"
							>{{ m.type }}</span
						>
						<span class="text-xs text-ink-900 flex-1 truncate">{{ m.party }}</span>
						<span class="text-[10px] text-ink-400 flex-shrink-0">{{
							fmtDate(m.date)
						}}</span>
						<span
							class="text-xs font-semibold tabular-nums w-24 text-right flex-shrink-0"
							:class="m.dir === 'in' ? 'text-success-700' : 'text-danger-700'"
							>{{ m.dir === "in" ? "+" : "−" }}{{ fmtINR(m.amount) }}</span
						>
					</div>
				</div>
				<div v-else class="px-4 py-8 text-center text-xs text-ink-400 italic">
					No transactions yet.
				</div>
			</section>
		</div>
	</DeskPage>
</template>
