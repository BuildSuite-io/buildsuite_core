<script setup>
// Notifications — the full list, built on the GENERIC doctype-list stack (DocTypeListView over
// Frappe's Notification Log), the same components every other list view uses. The bespoke bits are
// the bell dropdown and the detail page; the list itself is generic. Rows open the detail view.
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import { NOTIFICATION_TYPES, notificationType } from "@/data/notificationTypes";
import { fmtDate } from "@/utils/format";

const router = useRouter();

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Notifications" },
];

const FIELDS = ["name", "subject", "type", "from_user", "document_type", "document_name", "read", "creation"];

const typeFilter = ref("");
// read is a Check (0/1); DocTypeListView drops falsy filter values, so use string "0"/"1" — MariaDB
// coerces them and the empty string switches the filter off.
const readFilter = ref("");

const filterValues = computed(() => ({
	type: typeFilter.value,
	read: readFilter.value,
}));

const columns = [
	{ key: "type", label: "Type" },
	{ key: "subject", label: "Notification", fields: ["subject", "from_user", "read", "name"] },
	{ key: "document_type", label: "Reference", fields: ["document_type", "document_name"] },
	{ key: "read", label: "Status" },
	{ key: "creation", label: "When" },
];
</script>

<template>
	<DeskPage
		title="Notifications"
		subtitle="Assignments, mentions, shares and alerts addressed to you."
		:breadcrumbs="breadcrumbs"
	>
		<DocTypeListView
			doctype="Notification Log"
			:field-order="FIELDS"
			:columns="columns"
			:filter-values="filterValues"
			:filter-field-map="{ type: 'type', read: 'read' }"
			:search-fields="['subject', 'document_type', 'document_name']"
			cache-key="buildsuite-notification-list"
			row-key="name"
			search-placeholder="Search subject / reference"
			empty-message="Nothing here yet. Assignments, mentions, shares and alerts land here."
			initial-order-by="creation desc"
			@row-click="(row) => router.push({ name: 'notification-detail', params: { id: row.name } })"
		>
			<template #filter-chips>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Type</span>
					<DeskSelect v-model="typeFilter" class="!w-40">
						<option value="">Any</option>
						<option v-for="t in NOTIFICATION_TYPES" :key="t.id" :value="t.id">{{ t.label }}</option>
					</DeskSelect>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Status</span>
					<DeskSelect v-model="readFilter" class="!w-32">
						<option value="">Any</option>
						<option value="0">Unread</option>
						<option value="1">Read</option>
					</DeskSelect>
				</label>
			</template>

			<template #cell-type="{ row }">
				<span class="inline-flex items-center gap-1.5">
					<span
						class="w-6 h-6 rounded-lg flex items-center justify-center shrink-0"
						:class="notificationType(row.type).tint"
						:title="row.type"
					>
						<WorkspaceIcon :slug="notificationType(row.type).icon" :size="13" />
					</span>
					<span class="text-[11px] text-ink-600">{{ notificationType(row.type).label }}</span>
				</span>
			</template>

			<template #cell-subject="{ row }">
				<div class="text-ink-900" :class="row.read ? '' : 'font-semibold'">
					<span
						v-if="!row.read"
						class="inline-block w-1.5 h-1.5 rounded-full bg-brand-600 align-middle mr-1.5"
						title="Unread"
					></span>{{ row.subject }}
				</div>
				<div v-if="row.from_user" class="text-[10px] text-ink-500 mt-0.5">from {{ row.from_user }}</div>
			</template>

			<template #cell-document_type="{ row }">
				<span v-if="!row.document_type" class="text-ink-400">—</span>
				<template v-else>
					<div class="text-ink-700">{{ row.document_type }}</div>
					<div class="text-[10px] text-ink-500 font-mono">{{ row.document_name }}</div>
				</template>
			</template>

			<template #cell-read="{ row }">
				<span
					v-if="!row.read"
					class="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-brand-50 text-brand-700"
					>Unread</span
				>
				<span v-else class="text-[11px] text-ink-400">Read</span>
			</template>

			<template #cell-creation="{ row }">
				<span class="text-ink-600">{{ fmtDate(String(row.creation).slice(0, 10)) }}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
