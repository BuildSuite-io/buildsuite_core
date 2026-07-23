<script setup>
// Project Finance workspace landing — Transactions / Masters / Reports shortcut grids.
// Every section is dummy data (client-side mock) except Petty Cash, which is live.
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useFinanceMock } from "@/data/financeMock";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { fmtCompactINR } from "@/utils/format";

const fin = useFinanceMock();
const today = new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
const cashBank = computed(() => fin.totalCashBank);

const TX = [
	{ label: "Expenses", to: "/project-finance/expenses", icon: "file-text", live: false },
	{ label: "Petty Cash", to: "/project-finance/petty-cash", icon: "project-finance", live: true },
	{ label: "Invoices", to: "/project-finance/invoices", icon: "chart-line", live: false },
	{ label: "Bills", to: "/project-finance/bills", icon: "clipboard-list", live: false },
	{ label: "Payments", to: "/project-finance/payments", icon: "refresh-ccw", live: false },
];
const MASTERS = [
	{ label: "Customers", to: "/project-finance/customers", icon: "building-2" },
	{ label: "Suppliers", to: "/project-finance/suppliers", icon: "hard-hat" },
	{ label: "Subcontractors", to: "/project-finance/subcontractors", icon: "users-2" },
];
const REPORTS = [
	{ label: "Profit & Loss", slug: "pnl" },
	{ label: "Financial Position", slug: "position" },
	{ label: "Aged Receivables & Payables", slug: "aged" },
	{ label: "Petty Cash Statement", slug: "petty" },
	{ label: "Expense Summary", slug: "expenses" },
	{ label: "Cash & Bank Statement", slug: "cashbank" },
];
</script>

<template>
	<div class="max-w-6xl mx-auto px-4 py-6">
		<div class="mb-6">
			<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
			<h1 class="text-2xl font-semibold text-ink-900">Project Finance</h1>
		</div>

		<RouterLink
			to="/project-finance/overview"
			class="block mb-6 bg-brand-50 border border-brand-200 hover:border-brand-400 hover:bg-brand-100 rounded-xl p-5 transition-colors"
		>
			<div class="flex items-center justify-between gap-3">
				<div class="flex items-center gap-3">
					<svg class="w-5 h-5 text-brand-700 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('project-finance')" />
					<div>
						<div class="text-[10px] uppercase tracking-wider text-brand-700 font-medium">Overview</div>
						<div class="text-sm text-ink-700 mt-0.5">Cash &amp; bank, receivables, payables and what needs attention</div>
					</div>
				</div>
				<div class="text-right">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Cash &amp; bank</div>
					<div class="text-xl font-semibold text-ink-900 tabular-nums">{{ fmtCompactINR(cashBank) }}</div>
				</div>
			</div>
		</RouterLink>

		<section class="mb-6">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-500 mb-2">Transactions</h3>
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
				<RouterLink v-for="t in TX" :key="t.to" :to="t.to" class="bg-white border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 rounded-lg p-3 transition-colors group">
					<svg class="w-5 h-5 text-ink-500 group-hover:text-brand-600 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath(t.icon)" />
					<div class="text-sm font-medium text-ink-900 mt-2 flex items-center gap-1.5">
						{{ t.label }}
						<span v-if="t.live" class="text-[9px] px-1 py-0.5 bg-success-100 text-success-700 rounded uppercase tracking-wider">Live</span>
					</div>
				</RouterLink>
			</div>
		</section>

		<section class="mb-6">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-500 mb-2">Masters</h3>
			<div class="grid grid-cols-2 md:grid-cols-3 gap-3">
				<RouterLink v-for="m in MASTERS" :key="m.to" :to="m.to" class="bg-white border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 rounded-lg p-3 transition-colors group">
					<svg class="w-5 h-5 text-ink-500 group-hover:text-brand-600 transition-colors" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath(m.icon)" />
					<div class="text-sm font-medium text-ink-900 mt-2">{{ m.label }}</div>
				</RouterLink>
			</div>
		</section>

		<section>
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-500 mb-2">Reports</h3>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				<RouterLink v-for="r in REPORTS" :key="r.slug" :to="`/project-finance/report/${r.slug}`" class="bg-white border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 rounded-lg p-3 transition-colors flex items-center gap-2.5 group">
					<svg class="w-4 h-4 text-ink-500 group-hover:text-brand-600 transition-colors flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="getWorkspaceIconPath('chart-bar')" />
					<span class="text-sm font-medium text-ink-900 flex-1">{{ r.label }}</span>
					<span class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 rounded uppercase tracking-wider">Report</span>
				</RouterLink>
			</div>
		</section>
	</div>
</template>
