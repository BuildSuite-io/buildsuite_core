<script setup>
// Generic add/edit page for an admin-curated DocType — hosts DocTypeForm with the
// page chrome. /records/:doctype/new (create) and /records/:doctype/:name (edit).
import { computed } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeForm from "@/components/doctype/DocTypeForm.vue";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: "" },
});
const router = useRouter();

const isEdit = computed(() => !!props.name);
const title = computed(() => (isEdit.value ? props.name : `New ${props.doctype}`));
const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: props.doctype, to: `/records/${encodeURIComponent(props.doctype)}` },
	{ label: isEdit.value ? props.name : "New" },
]);

function toList() {
	router.push({ name: "records-list", params: { doctype: props.doctype } });
}
function onSaved(doc) {
	// After creating, move onto the saved record's edit page; after editing, back to the list.
	if (!isEdit.value && doc?.name) {
		router.replace({ name: "record-edit", params: { doctype: props.doctype, name: doc.name } });
	} else {
		toList();
	}
}
</script>

<template>
	<DeskPage :title="title" :breadcrumbs="breadcrumbs">
		<DocTypeForm
			:key="`${doctype}:${name}`"
			:doctype="doctype"
			:name="name"
			@saved="onSaved"
			@cancelled="toList"
		/>
	</DeskPage>
</template>
