<script setup>
// Crews — a standing gang of field employees, usable on any project. Member
// count comes from the denormalised `members_count` field: the list API
// doesn't return child tables.

import { RouterLink, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { usePermissions } from "@/composables/usePermissions";

const router = useRouter();
const { workerName } = useFieldEmployeeOptions();
const { canCreate } = usePermissions();

function onRowClick(row) {
	router.push(`/crews/${row.name}`);
}

const columns = [
	{ key: "crew_name", label: "Crew" },
	{ key: "crew_leader", label: "Leader" },
	{ key: "trade", label: "Trade" },
	{ key: "members_count", label: "Members", align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Crews" },
];
</script>

<template>
	<DeskPage title="Crew" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="canCreate('crew')" to="/crews/new" class="desk-save-btn !text-xs"
				>+ New</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Crew"
			:field-order="['crew_name', 'crew_leader', 'trade', 'members_count']"
			:columns="columns"
			:search-fields="['crew_name', 'name', 'trade']"
			cache-key="buildsuite-crews"
			row-key="name"
			initial-order-by="crew_name asc"
			search-placeholder="Search crews…"
			@row-click="onRowClick"
		>
			<template #cell-crew_name="{ row }">
				<DeskLink :to="`/crews/${row.name}`" @click.stop>
					{{ row.crew_name || row.name }}
				</DeskLink>
			</template>

			<template #cell-crew_leader="{ row }">
				<span class="text-ink-700">{{ workerName(row.crew_leader) || "—" }}</span>
			</template>

			<template #cell-trade="{ row }">
				<span class="text-ink-700">{{ row.trade || "—" }}</span>
			</template>

			<template #cell-members_count="{ row }">
				<span class="tabular-nums text-ink-700">{{ row.members_count || 0 }}</span>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
