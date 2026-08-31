<script setup>
// Generic list page for an admin-curated DocType (/records/:doctype). Pulls the
// list config (columns/search/sort) from the backend — derived from the DocType's
// Frappe meta — and renders it through the shared DocTypeListView. Rows open the
// generic form; "New" opens a blank one.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { getDoctypeListConfig, getDoctypePermissions } from "@/data/workspaceSettingApi";

const props = defineProps({ doctype: { type: String, required: true } });
const router = useRouter();

const config = ref(null);
const perms = ref({ create: false });
const error = ref("");
const loading = ref(true);

async function load() {
	loading.value = true;
	error.value = "";
	config.value = null;
	try {
		config.value = await getDoctypeListConfig(props.doctype);
		perms.value = await getDoctypePermissions(props.doctype).catch(() => perms.value);
	} catch (err) {
		error.value = err.message || "This record type isn't available here.";
	} finally {
		loading.value = false;
	}
}
watch(() => props.doctype, load, { immediate: true });

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: config.value?.label || props.doctype },
]);

function onNew() {
	router.push({ name: "record-new", params: { doctype: props.doctype } });
}
function onRow(row) {
	router.push({ name: "record-edit", params: { doctype: props.doctype, name: row.name } });
}
</script>

<template>
	<DeskPage :title="config?.label || doctype" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button
				v-if="perms.create"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				@click="onNew"
			>
				+ New
			</button>
		</template>

		<div v-if="error" class="bg-warning-50 border border-warning-200 rounded-lg px-4 py-6 text-sm text-warning-700">
			{{ error }}
		</div>
		<div v-else-if="loading" class="text-sm text-ink-500 py-10 text-center">Loading…</div>
		<DocTypeListView
			v-else-if="config"
			:doctype="doctype"
			:field-order="config.fieldOrder"
			:search-fields="config.searchFields"
			:initial-order-by="config.initialOrderBy"
			:cache-key="doctype"
			:search-placeholder="`Search ${config.label}…`"
			@row-click="onRow"
		/>
	</DeskPage>
</template>
