<script setup>
// Maps /project-finance/:section to its panel (petty-cash has its own explicit live route).
import { computed, defineAsyncComponent } from "vue";

const props = defineProps({ section: String });

const panels = {
	overview: defineAsyncComponent(() => import("@/views/finance/FinanceOverviewPanel.vue")),
	expenses: defineAsyncComponent(() => import("@/views/finance/FinanceExpensesPanel.vue")),
	invoices: defineAsyncComponent(() => import("@/views/finance/FinanceInvoicesPanel.vue")),
	bills: defineAsyncComponent(() => import("@/views/finance/FinanceBillsPanel.vue")),
	payments: defineAsyncComponent(() => import("@/views/finance/FinancePaymentsPanel.vue")),
	customers: defineAsyncComponent(() => import("@/views/finance/FinanceCustomersPanel.vue")),
	suppliers: defineAsyncComponent(() => import("@/views/finance/FinanceSuppliersPanel.vue")),
	subcontractors: defineAsyncComponent(() => import("@/views/finance/FinanceSubcontractorsPanel.vue")),
};
const comp = computed(() => panels[props.section] || null);
</script>

<template>
	<component :is="comp" v-if="comp" />
	<div v-else class="max-w-3xl mx-auto px-6 py-16 text-center text-ink-500">Unknown finance section.</div>
</template>
