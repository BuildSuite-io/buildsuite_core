<script setup>
// Companies — Settings sub-page. The generic DocTypeListView over Company (server paging, sort and
// the Add-filter editor); the colour badge, short name and per-company project count come from the
// store's company list, keyed by company id. CRUD is admin-only (route is gated below); non-admins
// who hit /app/settings/companies directly land on the empty-state redirect.

import { computed, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const store = useDataStore();
const router = useRouter();

// Derived company facts the Company doctype itself doesn't carry (colour, short name, projects).
const byId = computed(() => Object.fromEntries(store.companies.map((c) => [c.id, c])));
const meta = (id) => byId.value[id] || {};

// Derived columns name the stored fields their cells read, so those are fetched.
const columns = [
	{ key: "name", label: __("ID") },
	{ key: "company_name", label: __("Company"), fields: ["company_name", "abbr"] },
	{ key: "projects", label: __("Projects"), align: "right", fields: ["name"] },
	{ key: "active", label: __("Active"), fields: ["name"] },
];

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Settings"), to: "/settings" },
	{ label: __("Companies") },
];

const shown = ref(0);
const subtitle = computed(() =>
	__("{0} of {1} · multi-company per CLAUDE.md §14", [shown.value, store.companies.length])
);

function onRowClick(row) {
	router.push(`/settings/companies/${row.name}`);
}
</script>

<template>
	<DeskPage :title="__('Company')" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="store.isAdmin" to="/settings/companies/new" class="desk-save-btn"
				>+ {{ __("New Company") }}</RouterLink
			>
		</template>

		<!-- Non-admin guard — direct URL access still works but the New CTA hides
         and the page reads as informational only. -->
		<div
			v-if="!store.isAdmin"
			class="mb-3 px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700"
			style="border-radius: 2px"
		>
			{{
				__(
					"Read-only view. Creating / editing / deleting companies requires the System Manager role."
				)
			}}
		</div>

		<DocTypeListView
			doctype="Company"
			:field-order="['name', 'company_name', 'abbr']"
			:columns="columns"
			:search-fields="['name', 'company_name', 'abbr']"
			initial-order-by="company_name asc"
			cache-key="buildsuite-company-list"
			row-key="name"
			:search-placeholder="__('Search by id, name, abbreviation…')"
			@row-click="onRowClick"
			@total-change="shown = $event"
		>
			<template #cell-name="{ row }">
				<DeskLink
					:to="`/settings/companies/${row.name}`"
					@click.stop
					class="font-mono text-xs"
					>{{ row.name }}</DeskLink
				>
			</template>
			<template #cell-company_name="{ row }">
				<div class="flex items-center gap-2">
					<span
						:class="meta(row.name).color"
						class="w-3 h-3 flex-shrink-0"
						style="border-radius: 2px"
					></span>
					<div>
						<div class="text-sm font-medium text-ink-900">
							{{ row.company_name || row.name }}
						</div>
						<div class="text-[11px] text-ink-500">{{ row.abbr || row.name }}</div>
					</div>
				</div>
			</template>
			<template #cell-projects="{ row }">
				<span
					class="text-xs tabular-nums"
					:class="
						meta(row.name).projectCount ? 'text-ink-900 font-medium' : 'text-ink-400'
					"
				>
					{{ meta(row.name).projectCount ?? 0 }}
				</span>
			</template>
			<template #cell-active="{ row }">
				<span
					v-if="row.name === store.activeCompany"
					class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 font-medium"
					style="border-radius: 2px"
					>{{ __("Active") }}</span
				>
				<span v-else class="text-[10px] text-ink-400">—</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ __("No companies match this search.") }}
					<RouterLink
						v-if="store.isAdmin"
						to="/settings/companies/new"
						class="desk-link"
						>{{ __("Create a company →") }}</RouterLink
					>
				</div>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
