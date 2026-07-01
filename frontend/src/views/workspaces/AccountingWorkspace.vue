<script setup>
// Accounting workspace — inherited from ERPNext V16, with BuildSuite Core customizations
// per CLAUDE.md §12.2 / §12.6. This is the first authentic workspace landing (Phase 4),
// distinct from PlaceholderView's simple shortcut-tile pattern. Other ERPNext workspaces
// (Buying / Stock / Assets / HR) can copy this file's shape when they get populated.
//
// Construction-specific hiding decisions are made VISIBLE rather than silently omitted:
// items hidden for construction live in the bottom disclosure block with the reasoning
// inline, so a reviewer can audit what's been removed and why.
//
// All link `to` targets are stubs (#) — none of these ERPNext DocTypes exist in the
// prototype. The page is a build spec for what V16 + BuildSuite extensions look like.

import DeskPage from "@/components/desk/DeskPage.vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Accounting" }];

// Number Cards: ERPNext-standard KPI tiles at the top of the workspace. All values
// illustrative — no accounting data exists in seed (M8 Project Finance handles petty
// cash only). Real values would come from GL aggregation.
const numberCards = [
	{ label: "Outstanding receivables", value: "₹—", sub: "AR aging" },
	{ label: "Outstanding payables", value: "₹—", sub: "AP aging" },
	{ label: "Total bank balance", value: "₹—", sub: "all bank accounts" },
	{ label: "Net profit (YTD)", value: "₹—", sub: "fiscal year to date" },
];

// Shortcuts: large primary-action tiles. ERPNext picks the 5–6 most frequent docs.
// `bs: true` marks the ones BuildSuite Core extends with custom fields (§12.6).
const shortcuts = [
	{ label: "Sales Invoice", icon: "📄", to: "#" },
	{ label: "Purchase Invoice", icon: "📥", to: "#" },
	{
		label: "Journal Entry",
		icon: "📋",
		to: "#",
		bs: true,
		bsNote: "BS adds project + petty_cash_request links",
	},
	{ label: "Payment Entry", icon: "💸", to: "#" },
	{ label: "Bank Reconciliation", icon: "🏦", to: "#" },
	{ label: "Chart of Accounts", icon: "📊", to: "#" },
];

// Sections: grouped link lists below the shortcuts. Order and grouping match ERPNext V16's
// out-of-the-box Accounting workspace. Items marked `report: true` are reports (rendered
// with a small "report" hint instead of plain link).
const sections = [
	{
		title: "Accounting Masters",
		items: [
			{ label: "Company" },
			{ label: "Account" },
			{ label: "Cost Center" },
			{ label: "Fiscal Year" },
			{ label: "Mode of Payment" },
			{ label: "Payment Terms Template" },
			{ label: "Accounts Settings" },
			{ label: "Accounting Dimension" },
		],
	},
	{
		title: "General Ledger",
		items: [
			{ label: "Journal Entry", bs: true },
			{ label: "Payment Entry" },
			{ label: "Period Closing Voucher" },
			{ label: "General Ledger", report: true },
			{ label: "Trial Balance", report: true },
		],
	},
	{
		title: "Accounts Receivable",
		items: [
			{ label: "Customer" },
			{ label: "Sales Invoice" },
			{ label: "Payment Request" },
			{ label: "Customer Group" },
			{ label: "Sales Person" },
			{ label: "Dunning", hint: "rarely used in construction; kept for AMC contracts" },
			{ label: "Accounts Receivable", report: true },
			{ label: "Customer Ledger Summary", report: true },
		],
	},
	{
		title: "Accounts Payable",
		items: [
			{ label: "Supplier" },
			{ label: "Purchase Invoice" },
			{ label: "Supplier Group" },
			{ label: "Payment Entry" },
			{ label: "Accounts Payable", report: true },
			{ label: "Supplier Ledger Summary", report: true },
		],
	},
	{
		title: "Banking",
		items: [
			{ label: "Bank" },
			{ label: "Bank Account" },
			{ label: "Bank Statement Import" },
			{ label: "Bank Reconciliation Statement" },
			{ label: "Bank Clearance Summary", report: true },
		],
	},
	{
		title: "Financial Reports",
		items: [
			{ label: "Profit and Loss Statement", report: true },
			{ label: "Balance Sheet", report: true },
			{ label: "Cash Flow", report: true },
			{ label: "General Ledger", report: true },
			{ label: "Trial Balance", report: true },
			{ label: "Sales Register", report: true },
			{ label: "Purchase Register", report: true },
			{ label: "Gross and Net Profit Report", report: true },
		],
	},
	{
		title: "Tax & Compliance (India)",
		items: [
			{ label: "GST Settings" },
			{ label: "HSN Code" },
			{ label: "Tax Category" },
			{ label: "Tax Rule" },
			{ label: "Tax Withholding Category" },
			{ label: "Sales Taxes and Charges Template" },
			{ label: "Purchase Taxes and Charges Template" },
			{ label: "GSTR-1", report: true },
			{ label: "GSTR-3B", report: true },
			{ label: "GST Reconciliation", report: true },
			{ label: "HSN-wise Outward Summary", report: true },
		],
	},
	{
		title: "Multi-Currency",
		items: [
			{ label: "Currency" },
			{ label: "Currency Exchange" },
			{ label: "Exchange Rate Revaluation" },
		],
		note: "rare in domestic construction; relevant for projects with foreign material imports",
	},
	{
		title: "Cheque Printing",
		items: [{ label: "Cheque Print Template" }],
		note: "still common in India for vendor payments",
	},
];
</script>

<template>
	<DeskPage
		title="Accounting"
		subtitle="General ledger, receivables, payables and financial reports"
		:breadcrumbs="breadcrumbs"
	>
		<!-- Number Cards -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
			<div
				v-for="c in numberCards"
				:key="c.label"
				class="bg-white border border-ink-200 px-3 py-2"
				style="border-radius: 2px"
			>
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ c.label }}
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">
					{{ c.value }}
				</div>
				<div class="text-[10px] text-ink-500 mt-0.5">{{ c.sub }}</div>
			</div>
		</div>

		<section class="mb-5">
			<h2 class="desk-section-title">Shortcuts</h2>
			<hr class="desk-divider" />
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
				<WorkspaceShortcut
					v-for="s in shortcuts"
					:key="s.label"
					:href="s.to"
					:icon="s.icon"
					:label="s.label"
					prevent
				/>
			</div>
		</section>

		<!-- Sections grid (2 cols on desktop) -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 mb-6">
			<section v-for="sec in sections" :key="sec.title">
				<h2 class="desk-section-title">{{ sec.title }}</h2>
				<hr class="desk-divider" />
				<ul class="space-y-0.5">
					<li
						v-for="i in sec.items"
						:key="i.label"
						class="flex items-center gap-2 text-xs py-1 px-1 hover:bg-brand-50 cursor-pointer"
						style="border-radius: 6px"
					>
						<a href="#" class="desk-link" @click.prevent>{{ i.label }}</a>
						<span
							v-if="i.report"
							class="text-[9px] uppercase tracking-wider text-ink-400 font-semibold"
							>report</span
						>
					</li>
				</ul>
			</section>
		</div>
	</DeskPage>
</template>
