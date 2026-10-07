<script setup>
// Quotation — printable document, rendered from the Frappe Print Format set as the doctype
// default in Desk (Customize Form → Default Print Format) plus the default / document Letter
// Head, so it carries the issuing company's branding. See ServerPrintDocument for the mechanism.
import ServerPrintDocument from "@/components/ServerPrintDocument.vue";
import { __ } from "@/utils/translate";

const props = defineProps({ id: { type: String, required: true } });
</script>

<template>
	<ServerPrintDocument
		doctype="Quotation"
		:name="props.id"
		:back-to="`/quotations/${props.id}`"
		:back-label="__('Back to {0}', [props.id])"
	/>
</template>
