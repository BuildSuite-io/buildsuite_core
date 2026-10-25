<script setup>
import DeskPage from "@/components/desk/DeskPage.vue";
import FinanceCustomersPanel from "@/views/finance/FinanceCustomersPanel.vue";
import { __ } from "@/utils/translate";

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Sales"), to: "/sales" },
	{ label: __("Customers") },
];
</script>

<template>
	<DeskPage :title="__('Customers')" :breadcrumbs="breadcrumbs">
		<FinanceCustomersPanel />
	</DeskPage>
</template>
