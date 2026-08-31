<script setup>
// Generic list page for an admin-curated DocType (/records/:doctype). Pulls the
// list config (columns/search/sort + filter fields) from the backend — all derived
// from the DocType's own Frappe meta — and renders it through the shared
// DocTypeListView. Filters are built from the meta's in_standard_filter / in_list_view
// fields. Rows open the generic form; "New" opens a blank one.
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { getDoctypeListConfig, getDoctypePermissions } from "@/data/workspaceSettingApi";

const props = defineProps({ doctype: { type: String, required: true } });
const router = useRouter();

const config = ref(null);
const perms = ref({ create: false });
const error = ref("");
const loading = ref(true);

// Reactive filter values keyed by fieldname, fed into DocTypeListView.
const filterState = reactive({});

async function load() {
	loading.value = true;
	error.value = "";
	config.value = null;
	Object.keys(filterState).forEach((k) => delete filterState[k]);
	try {
		config.value = await getDoctypeListConfig(props.doctype);
		for (const f of config.value.filters || []) filterState[f.fieldname] = "";
		perms.value = await getDoctypePermissions(props.doctype).catch(() => perms.value);
	} catch (err) {
		error.value = err.message || "This record type isn't available here.";
	} finally {
		loading.value = false;
	}
}
watch(() => props.doctype, load, { immediate: true });

const filters = computed(() => config.value?.filters || []);

// Free-text fields match with a `like` contains; everything else is exact equality.
const filterFieldMap = computed(() => {
	const map = {};
	for (const f of filters.value) {
		map[f.fieldname] =
			f.fieldtype === "Data" || f.fieldtype === "Small Text"
				? { field: f.fieldname, op: "like", like: true }
				: f.fieldname;
	}
	return map;
});

const activeFilters = computed(() =>
	filters.value.filter((f) => filterState[f.fieldname] !== "" && filterState[f.fieldname] != null)
);
function clearFilters() {
	for (const f of filters.value) filterState[f.fieldname] = "";
}
function selectOptions(f) {
	return (f.options || "").split("\n").map((o) => o.trim()).filter(Boolean);
}

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
			<button v-if="perms.create" type="button" class="desk-save-btn" @click="onNew">
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
			:filter-values="filterState"
			:filter-field-map="filterFieldMap"
			:cache-key="doctype"
			:search-placeholder="`Search ${config.label}…`"
			@row-click="onRow"
		>
			<template v-if="filters.length" #filter-chips>
				<div v-for="f in filters" :key="f.fieldname" class="flex items-center gap-1.5">
					<span class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
						{{ f.label }}
					</span>
					<!-- Link -->
					<DeskLinkPicker
						v-if="f.fieldtype === 'Link'"
						v-model="filterState[f.fieldname]"
						class="!w-44"
						:doctype="f.options || 'DocType'"
						:page-length="10"
						:placeholder="`Any`"
					/>
					<!-- Select -->
					<DeskSelect
						v-else-if="f.fieldtype === 'Select'"
						v-model="filterState[f.fieldname]"
						class="!w-40"
					>
						<option value="">Any</option>
						<option v-for="o in selectOptions(f)" :key="o" :value="o">{{ o }}</option>
					</DeskSelect>
					<!-- Check -->
					<DeskSelect
						v-else-if="f.fieldtype === 'Check'"
						v-model="filterState[f.fieldname]"
						class="!w-28"
					>
						<option value="">Any</option>
						<option value="1">Yes</option>
						<option value="0">No</option>
					</DeskSelect>
					<!-- Date / Datetime -->
					<DeskInput
						v-else-if="f.fieldtype === 'Date' || f.fieldtype === 'Datetime'"
						v-model="filterState[f.fieldname]"
						type="date"
						class="!w-40"
					/>
					<!-- Data / Small Text -->
					<DeskInput
						v-else
						v-model="filterState[f.fieldname]"
						class="!w-40"
						:placeholder="`Filter ${f.label.toLowerCase()}…`"
					/>
				</div>
				<button
					v-if="activeFilters.length"
					type="button"
					class="text-[11px] text-ink-500 hover:text-ink-800 underline"
					@click="clearFilters"
				>
					Clear
				</button>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
