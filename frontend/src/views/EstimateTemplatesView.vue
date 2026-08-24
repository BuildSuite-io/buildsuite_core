<script setup>
import { useRouter, RouterLink } from "vue-router";
import { fmtINR, fmtDate } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { usePermissions } from "@/composables/usePermissions";

const router = useRouter();
const { canCreate } = usePermissions();

function onRowClick(row) {
	router.push(`/estimate-template/${row.name}`);
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Estimate Template" },
];

const FIELDS = [
	"name",
	"template_code",
	"template_name",
	"project_category",
	"enabled",
	"row_count",
	"estimated_total",
	"modified",
];

const columns = [
	{ key: "template_code", label: "Code" },
	{ key: "template_name", label: "Name" },
	{ key: "project_category", label: "Project Category" },
	{ key: "row_count", label: "Rows", align: "right" },
	{ key: "estimated_total", label: "Estimated", align: "right" },
	{ key: "modified", label: "Updated" },
	{ key: "enabled", label: "Status" },
];
</script>

<template>
	<DeskPage title="Estimate Template" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskLink to="/assembly" class="text-xs">View Assemblies →</DeskLink>
			<RouterLink
				v-if="canCreate('estimateTemplate')"
				to="/estimate-template/new"
				class="desk-save-btn"
				>+ New</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Estimate Template"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['template_code', 'template_name']"
			cache-key="buildsuite-estimate-template-list"
			row-key="name"
			search-placeholder="Search by code or name…"
			empty-message="No estimate templates yet."
			@row-click="onRowClick"
		>
			<template #cell-template_code="{ row }">
				<DeskLink
					:to="`/estimate-template/${row.name}`"
					class="font-mono text-xs"
					@click.stop
					>{{ row.template_code }}</DeskLink
				>
			</template>
			<template #cell-template_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.template_name }}</span>
			</template>
			<template #cell-project_category="{ row }">
				<span
					v-if="row.project_category"
					class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-700 font-medium"
					style="border-radius: 9999px"
					>{{ row.project_category }}</span
				>
				<span v-else class="text-ink-300">Any</span>
			</template>
			<template #cell-row_count="{ row }">
				<span class="text-xs text-ink-700 tabular-nums">{{ row.row_count || 0 }}</span>
			</template>
			<template #cell-estimated_total="{ row }">
				<span class="text-sm font-medium text-ink-900 tabular-nums">{{
					fmtINR(row.estimated_total)
				}}</span>
			</template>
			<template #cell-modified="{ row }">
				<span class="text-xs text-ink-500 whitespace-nowrap">{{
					fmtDate(row.modified)
				}}</span>
			</template>
			<template #cell-enabled="{ row }">
				<span
					v-if="row.enabled"
					class="text-[10px] px-2 py-0.5 bg-success-50 text-success-700 font-medium"
					style="border-radius: 9999px"
					>Enabled</span
				>
				<span
					v-else
					class="text-[10px] px-2 py-0.5 bg-ink-100 text-ink-500 font-medium"
					style="border-radius: 9999px"
					>Disabled</span
				>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
