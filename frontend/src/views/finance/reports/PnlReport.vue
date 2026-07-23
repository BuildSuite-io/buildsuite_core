<script setup>
import { computed } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Profit & Loss" }];

const income = computed(() => fin.postedInvoices.reduce((a, i) => a + (i.gross || 0), 0));
const byCostType = (t) => fin.verifiedExpenses.filter((e) => e.cost_type === t).reduce((a, e) => a + e.amount, 0);
const materials = computed(() => byCostType("Material") + fin.bills.reduce((a, b) => a + (b.gross || 0), 0));
const labour = computed(() => byCostType("Labour"));
const plant = computed(() => byCostType("Plant & Machinery"));
const subcontract = computed(() => fin.subcontractorBills.reduce((a, b) => a + (b.gross || 0), 0) + byCostType("Subcontract"));
const overheads = computed(() => byCostType("Overhead"));
const directCosts = computed(() => materials.value + labour.value + plant.value + subcontract.value);
const grossProfit = computed(() => income.value - directCosts.value);
const netProfit = computed(() => grossProfit.value - overheads.value);
const pct = (v) => (income.value ? ((v / income.value) * 100).toFixed(1) + "%" : "—");

const lines = computed(() => [
	{ label: "Income", value: income.value, bold: true },
	{ label: "Materials", value: -materials.value, indent: true },
	{ label: "Labour", value: -labour.value, indent: true },
	{ label: "Plant & Machinery", value: -plant.value, indent: true },
	{ label: "Subcontract", value: -subcontract.value, indent: true },
	{ label: "Gross profit", value: grossProfit.value, bold: true, rule: true },
	{ label: "Overheads", value: -overheads.value, indent: true },
	{ label: "Net profit", value: netProfit.value, bold: true, rule: true },
]);
</script>

<template>
	<DeskPage title="Profit & Loss" :breadcrumbs="breadcrumbs">
		<div class="bg-white border border-ink-200 rounded-lg overflow-hidden max-w-2xl">
			<table class="w-full text-sm">
				<tbody>
					<tr v-for="(l, i) in lines" :key="i" :class="[l.rule ? 'border-t-2 border-ink-200' : 'border-t border-ink-100', l.bold ? 'font-semibold text-ink-900' : 'text-ink-700']">
						<td class="px-4 py-2" :class="l.indent ? 'pl-8 text-ink-600' : ''">{{ l.label }}</td>
						<td class="px-4 py-2 text-right tabular-nums" :class="l.value < 0 ? 'text-danger-700' : ''">{{ fmtINR(Math.abs(l.value)) }}</td>
						<td class="px-4 py-2 text-right text-[11px] text-ink-400 tabular-nums">{{ pct(Math.abs(l.value)) }}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</DeskPage>
</template>
