<script setup>
// A settings page that is just a Single DocType (declared by an installed app through the
// buildsuite_settings_pages hook, or any readable Single): the generic form on the doctype's own
// record. /settings/doc/:doctype. Saving is gated by the DocType's own permissions.
import { computed } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeForm from "@/components/doctype/DocTypeForm.vue";
import { __ } from "@/utils/translate";

const props = defineProps({ doctype: { type: String, required: true } });

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: props.doctype },
]);
</script>

<template>
	<DeskPage :title="doctype" :breadcrumbs="breadcrumbs">
		<DocTypeForm :key="doctype" :doctype="doctype" :name="doctype" />
	</DeskPage>
</template>
