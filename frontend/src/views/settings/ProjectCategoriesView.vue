<script setup>
// Project Categories — settings list (backend-backed via the Project Category
// doctype). Admin / BSA gated. Construction categories drive project templating.

import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const store = useDataStore();
const router = useRouter();

const columns = [
	{ key: "category_name", label: "Category" },
	{ key: "work_package_label", label: "Work Package label" },
	{ key: "work_package_label_plural", label: "Plural" },
	{ key: "sort_order", label: "Sort", align: "right" },
	{ key: "enabled", label: "Enabled" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Project Categories" },
];

function onRowClick(row) {
	router.push(`/settings/project-categories/${row.name}`);
}

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) router.replace("/settings");
});
</script>

<template>
	<DeskPage title="Project Categories" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskLink to="/settings/project-categories/new" class="desk-save-btn">
				+ New Category
			</DeskLink>
		</template>

		<DocTypeListView
			doctype="Project Category"
			:field-order="[
				'category_name',
				'work_package_label',
				'work_package_label_plural',
				'sort_order',
				'enabled',
			]"
			:columns="columns"
			:search-fields="['category_name']"
			cache-key="buildsuite-project-categories"
			row-key="name"
			initial-order-by="sort_order asc"
			search-placeholder="Search categories…"
			@row-click="onRowClick"
		>
			<template #cell-enabled="{ row }">
				<span
					class="text-[10px] px-1.5 py-0.5 font-medium"
					:class="
						row.enabled ? 'bg-success-50 text-success-700' : 'bg-ink-100 text-ink-500'
					"
					style="border-radius: 9999px"
					>{{ row.enabled ? "Enabled" : "Disabled" }}</span
				>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
