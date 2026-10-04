<script setup>
import { ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { fmtCompactINR } from "@/utils/format";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { usePermissions } from "@/composables/usePermissions";
import { __ } from "@/utils/translate";

const router = useRouter();
const store = useDataStore();
const { canCreate } = usePermissions();

const statusFilter = ref("");
const typeFilter = ref("");
// The project list follows the topbar company switcher: it defaults to the working company
// and re-queries when the user switches. Empty = all companies (single-company site or an
// explicit "All companies" pick in the filter chip).
const companyFilter = ref(store.activeCompany || "");
watch(
	() => store.activeCompany,
	(company) => {
		companyFilter.value = company || "";
	}
);

const companiesResource = useDocTypeList("Company", {
	fields: ["name", "abbr"],
	orderBy: "name asc",
	cache: "buildsuite-companies-for-project-list",
	transform(companies) {
		return companies.map((c) => ({
			id: c.name,
			name: c.name,
			abbr: c.abbr || "",
		}));
	},
});

const isMultiCompany = computed(() => (companiesResource.data?.length ?? 0) > 1);

// Honor ?status= deep links (Home "Active projects" tile). "active" = the live project statuses
// (base filter); a real status seeds the status chip. Mirrors home.py's _ACTIVE set.
const route = useRoute();
const ACTIVE_PROJECT_STATUSES = ["New", "Ongoing", "Delayed"];
const queryStatus = route.query.status || "";
if (queryStatus && queryStatus !== "active") statusFilter.value = queryStatus;
const baseFilters = computed(() => {
	const f = [["parent_project", "is", "not set"]];
	if (queryStatus === "active") f.push(["project_status", "in", ACTIVE_PROJECT_STATUSES]);
	return f;
});

const filterValues = computed(() => ({
	status: statusFilter.value,
	type: typeFilter.value,
	company: companyFilter.value,
}));

function companyName(id) {
	return companiesResource.data?.find((c) => c.id === id)?.name || id;
}

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: __("Project") }];

function onRowClick(row) {
	const key = row.name;
	router.push(`/projects/${key}`);
}
</script>

<template>
	<DeskPage :title="__('Project')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="canCreate('project')" to="/projects/new" class="desk-save-btn"
				>{{ __("+ New") }}</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Project"
			:field-order="[
				'custom_project_id',
				'project_name',
				'customer',
				'project_category',
				'project_status',
				'estimated_costing',
				'percent_complete',
				'expected_start_date',
				'expected_end_date',
				'company',
			]"
			:columns="[
				{ key: 'custom_project_id', label: __('Project ID') },
				{ key: 'project_name', label: __('Project Name') },
				{ key: 'customer', label: __('Client') },
				{ key: 'project_category', label: __('Project Category') },
				{
					key: 'project_status',
					label: __('Status'),
					preset: 'status',
				},
				{ key: 'estimated_costing', label: __('Budget') },
				{ key: 'percent_complete', label: __('Progress'), preset: 'progress' },
				{
					key: 'timeline',
					label: __('Timeline'),
					preset: 'timeline',
					fields: ['expected_start_date', 'expected_end_date'],
				},
				{ key: 'company', label: __('Company') },
			]"
			:search-fields="['project_name', 'custom_project_id', 'customer', 'name']"
			:base-filters="baseFilters"
			:filter-values="filterValues"
			:filter-field-map="{
				status: 'project_status',
				type: 'project_category',
				company: 'company',
			}"
			cache-key="buildsuite-project-list-generic"
			row-key="name"
			:search-placeholder="__('Search by name, code, client…')"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<DeskSelect v-model="statusFilter" class="!w-32">
					<option value="">{{ __("Status: Any") }}</option>
					<option value="New">{{ __("New") }}</option>
					<option value="Ongoing">{{ __("Ongoing") }}</option>
					<option value="Delayed">{{ __("Delayed") }}</option>
					<option value="Completed">{{ __("Completed") }}</option>
				</DeskSelect>

				<DeskSelect v-model="typeFilter" class="!w-40">
					<option value="">{{ __("Category: Any") }}</option>
					<option value="Commercial">{{ __("Commercial") }}</option>
					<option value="Residential">{{ __("Residential") }}</option>
					<option value="Infrastructure">{{ __("Infrastructure") }}</option>
					<option value="Industrial">{{ __("Industrial") }}</option>
					<option value="Renovation">{{ __("Renovation") }}</option>
				</DeskSelect>

				<DeskLinkPicker
					v-if="isMultiCompany"
					v-model="companyFilter"
					class="!w-44"
					doctype="Company"
					label-field="name"
					value-field="name"
					:search-fields="['name', 'abbr']"
					:page-length="10"
					:placeholder="__('Company: Any')"
				/>
			</template>

			<template #cell-custom_project_id="{ row }">
				<DeskLink :to="`/projects/${row.name}`" @click.stop class="font-mono text-xs">
					{{ row.custom_project_id || row.name }}
				</DeskLink>
			</template>

			<template #cell-project_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.project_name || row.name }}</span>
			</template>

			<template #cell-estimated_costing="{ row }">
				<span class="tabular-nums">{{ fmtCompactINR(row.estimated_costing || 0) }}</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ __("No projects match your filters") }} ·
					<DeskLink to="/projects/new">{{ __("Create one →") }}</DeskLink>
				</div>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
