<script setup>
import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { __ } from "@/utils/translate";
import { fmtINR } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { usePermissions } from "@/composables/usePermissions";

const router = useRouter();
const { canCreate } = usePermissions();

function onRowClick(row) {
	router.push(`/assembly/${row.name}`);
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Estimation"), to: "/estimation" },
	{ label: __("Assembly") },
];

const FIELDS = [
	"name",
	"assembly_code",
	"assembly_name",
	"category",
	"uom",
	"rate_per_unit",
	"component_count",
	"notes",
];

const columns = [
	{ key: "assembly_code", label: __("Code") },
	{ key: "assembly_name", label: __("Name") },
	{ key: "category", label: __("Category") },
	{ key: "uom", label: __("Unit") },
	{ key: "component_count", label: __("Components"), align: "right" },
	{ key: "rate_per_unit", label: __("Rate / unit"), align: "right" },
];

const categoryFilter = ref("");
const filterValues = computed(() => ({ category: categoryFilter.value }));
const filterFieldMap = { category: "category" };
</script>

<template>
	<DeskPage :title="__('Assembly')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskLink to="/rate-master" class="text-xs">{{ __("View Rate Master →") }}</DeskLink>
			<RouterLink v-if="canCreate('assembly')" to="/assembly/new" class="desk-save-btn"
				>{{ __("+ New") }}</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Assembly"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['assembly_code', 'assembly_name']"
			:filter-values="filterValues"
			:filter-field-map="filterFieldMap"
			cache-key="buildsuite-assembly-list"
			row-key="name"
			:search-placeholder="__('Search by code or name…')"
			:empty-message="__('No assemblies match your filters.')"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<DeskLinkPicker
					v-if="!categoryFilter"
					v-model="categoryFilter"
					doctype="Assembly Category"
					label-field="name"
					value-field="name"
					:placeholder="__('Category: Any')"
					class="!w-40"
				/>
				<DeskFilterChip
					v-else
					:label="__('Category')"
					:value="categoryFilter"
					@remove="categoryFilter = ''"
				/>
			</template>

			<template #cell-assembly_code="{ row }">
				<DeskLink :to="`/assembly/${row.name}`" class="font-mono text-xs" @click.stop>{{
					row.assembly_code
				}}</DeskLink>
			</template>
			<template #cell-assembly_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.assembly_name }}</span>
				<div v-if="row.notes" class="text-[11px] text-ink-500 truncate">
					{{ row.notes }}
				</div>
			</template>
			<template #cell-category="{ row }">
				<span
					v-if="row.category"
					class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-700 font-medium"
					style="border-radius: 9999px"
					>{{ row.category }}</span
				>
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-uom="{ row }">
				<span class="text-ink-600 text-xs">{{ row.uom }}</span>
			</template>
			<template #cell-component_count="{ row }">
				<span class="text-xs text-ink-700 tabular-nums">{{
					row.component_count || 0
				}}</span>
			</template>
			<template #cell-rate_per_unit="{ row }">
				<span class="text-sm font-medium text-ink-900 tabular-nums">{{
					fmtINR(row.rate_per_unit)
				}}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
