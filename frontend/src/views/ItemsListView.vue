<script setup>
// Items — the ERPNext Item master. Row click opens the edit dialog straight from
// the row object: the list already fetches every field the form needs.

import { computed, ref } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import ItemFormModal from "@/components/ItemFormModal.vue";
import { fmtINR } from "@/utils/format";

const ITEM_FIELDS = [
	"name",
	"item_name",
	"item_group",
	"stock_uom",
	"standard_rate",
	"custom_rate_master",
	"disabled",
];

const columns = [
	// `name` is the docname, which for Item is the item_code.
	{ key: "name", label: "Code" },
	{ key: "item_name", label: "Item" },
	{ key: "item_group", label: "Group" },
	{ key: "stock_uom", label: "UOM" },
	{ key: "standard_rate", label: "Standard rate", align: "right" },
	{ key: "custom_rate_master", label: "Rate Master" },
	{ key: "disabled", label: "Status" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Items" },
];

const groupFilter = ref("");
const filterValues = computed(() => ({ itemGroup: groupFilter.value }));

const listRef = ref(null);
const formOpen = ref(false);
const editingItem = ref(null);

function openNew() {
	editingItem.value = null;
	formOpen.value = true;
}

function openEdit(row) {
	editingItem.value = row;
	formOpen.value = true;
}
</script>

<template>
	<DeskPage title="Item" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn !text-xs" @click="openNew">
				+ New Item
			</button>
		</template>

		<DocTypeListView
			ref="listRef"
			doctype="Item"
			:field-order="ITEM_FIELDS"
			:columns="columns"
			:search-fields="['name', 'item_name', 'item_group']"
			:filter-values="filterValues"
			:filter-field-map="{ itemGroup: 'item_group' }"
			cache-key="buildsuite-items"
			row-key="name"
			initial-order-by="item_name asc"
			search-placeholder="Search item, code, group…"
			@row-click="openEdit"
		>
			<template #filter-chips>
				<DeskLinkPicker
					v-if="!groupFilter"
					v-model="groupFilter"
					class="!w-56"
					doctype="Item Group"
					:page-length="10"
					placeholder="Group: Any"
				/>
				<DeskFilterChip
					v-else
					label="Group"
					:value="groupFilter"
					@remove="groupFilter = ''"
				/>
			</template>

			<template #cell-name="{ row }">
				<span class="font-mono text-xs text-ink-700">{{ row.name }}</span>
			</template>

			<template #cell-item_name="{ row }">
				<span class="text-ink-900 font-medium">{{ row.item_name || row.name }}</span>
			</template>

			<template #cell-item_group="{ row }">
				<span class="text-ink-700">{{ row.item_group || "—" }}</span>
			</template>

			<template #cell-stock_uom="{ row }">
				<span class="text-ink-700">{{ row.stock_uom || "—" }}</span>
			</template>

			<template #cell-standard_rate="{ row }">
				<span class="tabular-nums text-ink-700">
					{{ row.standard_rate ? fmtINR(row.standard_rate) : "—" }}
				</span>
			</template>

			<template #cell-custom_rate_master="{ row }">
				<span class="font-mono text-[11px] text-ink-500">
					{{ row.custom_rate_master || "—" }}
				</span>
			</template>

			<template #cell-disabled="{ row }">
				<StatusBadge :status="row.disabled ? 'Disabled' : 'Active'" />
			</template>
		</DocTypeListView>

		<ItemFormModal
			:open="formOpen"
			:item="editingItem"
			@close="formOpen = false"
			@saved="listRef?.reload()"
		/>
	</DeskPage>
</template>
