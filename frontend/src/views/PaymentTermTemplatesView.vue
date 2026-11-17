<script setup>
// Payment Term Templates list. Copied from the demo's PaymentTermsTemplatesView;
// new and edit both open PaymentTermTemplateModal.

import { ref } from "vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import PaymentTermTemplateModal from "@/components/PaymentTermTemplateModal.vue";
import { __ } from "@/utils/translate";

const DOCTYPE = "BuildSuite Payment Term Template";
const listRef = ref(null);
const modalOpen = ref(false);
const editingName = ref(null);

function openModal(name = null) {
	editingName.value = name;
	modalOpen.value = true;
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("Estimation"), to: "/estimation" },
	{ label: __("Payment Term Templates") },
];

const FIELDS = [
	"name",
	"payment_term_name",
	"description",
	"project_category",
	"milestones_count",
	"total_percentage",
	"enabled",
];

const columns = [
	{
		key: "payment_term_name",
		label: __("Template"),
		fields: ["payment_term_name", "description"],
	},
	{ key: "project_category", label: __("Project Category") },
	{ key: "milestones_count", label: __("Milestones") },
	{ key: "total_percentage", label: __("Total") },
	{ key: "enabled", label: __("Status") },
];
</script>

<template>
	<DeskPage :title="__('Payment Term Templates')" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn" @click="openModal()">
				{{ __("+ New template") }}
			</button>
		</template>

		<p class="text-xs text-ink-500 mb-3 max-w-3xl">
			{{
				__(
					"A template is copied into a quotation, tender or project when it is loaded, so changing one here never moves an offer that already went out.",
				)
			}}
		</p>

		<DocTypeListView
			ref="listRef"
			:doctype="DOCTYPE"
			:field-order="FIELDS"
			:columns="columns"
			:search-fields="['payment_term_name']"
			cache-key="buildsuite-payment-term-template-list"
			row-key="name"
			:search-placeholder="__('Search by name…')"
			:empty-message="__('No templates yet.')"
			@row-click="(row) => openModal(row.name)"
		>
			<template #cell-payment_term_name="{ row }">
				<div class="text-ink-900 font-medium">{{ row.payment_term_name }}</div>
				<div v-if="row.description" class="text-xs text-ink-500 mt-0.5 line-clamp-1">
					{{ row.description }}
				</div>
			</template>
			<template #cell-project_category="{ row }">
				<span v-if="row.project_category" class="text-ink-700">{{
					row.project_category
				}}</span>
				<span v-else class="text-ink-300">{{ __("Any") }}</span>
			</template>
			<template #cell-milestones_count="{ row }">
				<span class="text-ink-700">{{ row.milestones_count }}</span>
			</template>
			<template #cell-total_percentage="{ row }">
				<span class="text-ink-700">{{ row.total_percentage }}%</span>
			</template>

			<template #cell-enabled="{ row }">
				<span
					v-if="row.enabled"
					class="text-[10px] px-2 py-0.5 bg-success-50 text-success-700 font-medium"
					style="border-radius: 9999px"
					>{{ __("Enabled") }}</span
				>
				<span
					v-else
					class="text-[10px] px-2 py-0.5 bg-ink-100 text-ink-500 font-medium"
					style="border-radius: 9999px"
					>{{ __("Disabled") }}</span
				>
			</template>
		</DocTypeListView>

		<PaymentTermTemplateModal
			:open="modalOpen"
			:name="editingName"
			@close="modalOpen = false"
			@saved="listRef?.reload()"
		/>
	</DeskPage>
</template>
