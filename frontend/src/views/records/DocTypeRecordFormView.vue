<script setup>
// Generic add/edit page for an admin-curated DocType — hosts DocTypeForm with the
// page chrome. /records/:doctype/new (create) and /records/:doctype/:name (edit).
// DocTypeForm owns its own navigation (back to list, on to a created/amended doc).
import { computed } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeForm from "@/components/doctype/DocTypeForm.vue";
import { __ } from "@/utils/translate";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: "" },
});

const isEdit = computed(() => !!props.name);
const title = computed(() => (isEdit.value ? props.name : __("New {0}", [props.doctype])));
const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: props.doctype, to: `/records/${encodeURIComponent(props.doctype)}` },
	{ label: isEdit.value ? props.name : __("New") },
]);
</script>

<template>
	<DeskPage :title="title" :breadcrumbs="breadcrumbs">
		<DocTypeForm :key="`${doctype}:${name}`" :doctype="doctype" :name="name" />
	</DeskPage>
</template>
