<script setup>
// Maps /project-finance/report/:slug to its report component.
import { computed, defineAsyncComponent } from "vue";

const props = defineProps({ slug: String });

const reports = {
	pnl: defineAsyncComponent(() => import("@/views/finance/reports/PnlReport.vue")),
	position: defineAsyncComponent(() => import("@/views/finance/reports/FinancialPositionReport.vue")),
	aged: defineAsyncComponent(() => import("@/views/finance/reports/AgedReport.vue")),
	petty: defineAsyncComponent(() => import("@/views/finance/reports/PettyCashReport.vue")),
	expenses: defineAsyncComponent(() => import("@/views/finance/reports/ExpenseSummaryReport.vue")),
	cashbank: defineAsyncComponent(() => import("@/views/finance/reports/CashBankStatementReport.vue")),
};
const comp = computed(() => reports[props.slug] || null);
</script>

<template>
	<component :is="comp" v-if="comp" />
	<div v-else class="max-w-3xl mx-auto px-6 py-16 text-center text-ink-500">Unknown report.</div>
</template>
