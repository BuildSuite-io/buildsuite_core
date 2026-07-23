<script setup>
import { computed } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Aged" }];

const receivables = computed(() =>
	fin.openInvoices.map((i) => ({ party: fin.customerById(i.customer)?.name || i.customer, due: i.due_date, bucket: fin.agingBucket(i.due_date), amount: fin.invoiceOutstanding(i) })),
);
const payables = computed(() =>
	fin.unifiedPayables
		.filter((b) => b.outstanding > 0.5)
		.map((b) => ({ party: (b.kind === "subcontractor" ? fin.subcontractors.find((s) => s.id === b.supplier)?.name : fin.supplierById(b.supplier)?.name) || b.supplier, due: b.due_date, bucket: b.due_date ? fin.agingBucket(b.due_date) : "—", amount: b.outstanding, retention: b.retention || 0 })),
);
</script>

<template>
	<DeskPage title="Aged Receivables & Payables" :breadcrumbs="breadcrumbs">
		<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-success-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-success-800">Receivables</h3></div>
				<table class="w-full text-xs">
					<thead class="bg-white text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-3 py-2">Customer</th><th class="text-left px-3 py-2">Due</th><th class="text-left px-3 py-2">Bucket</th><th class="text-right px-3 py-2">Outstanding</th></tr></thead>
					<tbody>
						<tr v-for="(r, i) in receivables" :key="i" class="border-t border-ink-100"><td class="px-3 py-2 text-ink-900">{{ r.party }}</td><td class="px-3 py-2 text-ink-500">{{ fmtDate(r.due) }}</td><td class="px-3 py-2 text-ink-600">{{ r.bucket }}</td><td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(r.amount) }}</td></tr>
						<tr v-if="!receivables.length"><td colspan="4" class="px-3 py-3 text-center text-ink-400 italic">Nothing outstanding.</td></tr>
					</tbody>
				</table>
			</section>
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-danger-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-danger-800">Payables</h3></div>
				<table class="w-full text-xs">
					<thead class="bg-white text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-3 py-2">Supplier</th><th class="text-left px-3 py-2">Due</th><th class="text-left px-3 py-2">Bucket</th><th class="text-right px-3 py-2">Outstanding</th><th class="text-right px-3 py-2">Retention</th></tr></thead>
					<tbody>
						<tr v-for="(r, i) in payables" :key="i" class="border-t border-ink-100"><td class="px-3 py-2 text-ink-900">{{ r.party }}</td><td class="px-3 py-2 text-ink-500">{{ fmtDate(r.due) }}</td><td class="px-3 py-2 text-ink-600">{{ r.bucket }}</td><td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(r.amount) }}</td><td class="px-3 py-2 text-right tabular-nums text-warning-700">{{ r.retention ? fmtINR(r.retention) : "—" }}</td></tr>
						<tr v-if="!payables.length"><td colspan="5" class="px-3 py-3 text-center text-ink-400 italic">Nothing outstanding.</td></tr>
					</tbody>
				</table>
			</section>
		</div>
	</DeskPage>
</template>
