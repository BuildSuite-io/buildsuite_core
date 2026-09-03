<script setup>
// Subcontractor Work Order — printable document, rendered from the Frappe Print Format
// set as the doctype default in Desk (Customize Form → Default Print Format) plus the
// default / document Letter Head. See ServerPrintDocument for the mechanism.
import ServerPrintDocument from "@/components/ServerPrintDocument.vue";

const props = defineProps({ id: { type: String, required: true } });
</script>

<template>
	<ServerPrintDocument
		doctype="Subcontractor Work Order"
		:name="props.id"
		:back-to="`/subcontractor-work-orders/${props.id}`"
		back-label="Back to work order"
	/>
</template>
