<script setup>
import { computed, ref } from "vue";
import { useRouter, useRoute, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import UserAvatar from "@/components/UserAvatar.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { usePermissions } from "@/composables/usePermissions";
import { useListCounts } from "@/composables/useListCounts";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const store = useDataStore();
const router = useRouter();
const route = useRoute();
const adapter = createDataAdapter(store);
const { canCreate, canRead } = usePermissions();

const taskFilter = ref(route.query.task || "");
const enteredByFilter = ref("");
const blockerOnly = ref(false);

const TODAY = new Date().toISOString().slice(0, 10);
function daysAgo(n) {
	const d = new Date();
	d.setDate(d.getDate() - n);
	return d.toISOString().slice(0, 10);
}
const SEVEN_DAYS_AGO = daysAgo(6);

// The generic DocTypeListView owns paging, sort and the Add-filter editor; the KPI strip counts the
// whole (company-scoped) set on the server, independent of the list's filters.
const { counts: kpis } = useListCounts("Task Progress Entry", () => ({
	total: [],
	today: [["entry_date", "=", TODAY]],
	thisWeek: [["entry_date", ">=", SEVEN_DAYS_AGO]],
	blockers: [["blocker", "=", 1]],
}));

// The list's own chips map onto doctype fields; "entered by" is the document owner.
const filterValues = computed(() => ({
	task: taskFilter.value,
	enteredBy: enteredByFilter.value,
	blocker: blockerOnly.value ? 1 : 0,
}));

// Task names for the Task column (the entry stores the Task id).
const tasksResource = adapter.list("Task", {
	fields: ["name", "subject", "status"],
	orderBy: "modified desc",
	pageLength: 0, // need every task so the name->subject map resolves all entries
	transform(rows) {
		return rows.map((row) => ({
			id: row?.name || "",
			name: row?.subject || row?.name || "",
		}));
	},
	// Don't fetch (and 403) when the persona has no Task Progress Entry read — the
	// template shows the restricted notice instead. Mirrors the StagePlanningsView gate.
	auto: canRead("taskProgressEntry"),
});
function toArray(data) {
	if (Array.isArray(data)) return data;
	if (Array.isArray(data?.value)) return data.value;
	return [];
}
const tasksMap = computed(() => {
	const map = {};
	toArray(tasksResource.data).forEach((t) => {
		map[t.id] = t.name;
	});
	return map;
});

function taskName(id) {
	return tasksMap.value[id] || id;
}

const WEATHER_ICON = {
	Clear: "☀️",
	Rainy: "🌧️",
	Hot: "🌡️",
	Cold: "❄️",
	Storm: "⛈️",
};

// Non-field columns name the real fields their cells read, so those are fetched.
const columns = [
	{ key: "name", label: __("ID") },
	{ key: "entry_date", label: __("Date") },
	{ key: "task", label: __("Task") },
	{ key: "cumulative_progress", label: __("Progress"), align: "right" },
	{ key: "labour", label: __("Labour"), align: "right", fields: ["skilled", "unskilled"] },
	{ key: "weather", label: __("Weather") },
	{ key: "flags", label: __("Flags"), fields: ["blocker", "blocker_detail"] },
	{ key: "owner", label: __("Entered by") },
];

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Task Progress Entry") },
];

const shown = ref(0);
const subtitle = computed(() =>
	kpis.value.total == null ? "" : __("{0} of {1}", [shown.value, kpis.value.total])
);

function onRowClick(row) {
	router.push(`/progress-entries/${row.name}`);
}
</script>

<template>
	<DeskPage :title="__('Task Progress Entry')" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink
				v-if="canCreate('taskProgressEntry')"
				to="/progress-entries/new"
				class="desk-save-btn"
				>+ {{ __("New Entry") }}</RouterLink
			>
		</template>

		<!-- PRM-014 — roles without Task Progress Entry access get a restricted notice. -->
		<div
			v-if="!canRead('taskProgressEntry')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ __("You don't have access to Task Progress Entries.") }}
		</div>

		<!-- KPI strip -->
		<div
			v-if="canRead('taskProgressEntry')"
			class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4"
		>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Total entries") }}
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5">
					{{ kpis.total ?? "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Filed today") }}
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5">
					{{ kpis.today ?? "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Last 7 days") }}
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5">
					{{ kpis.thisWeek ?? "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Flagged blockers") }}
				</div>
				<div
					class="text-base font-semibold mt-0.5"
					:class="kpis.blockers > 0 ? 'text-danger-700' : 'text-ink-900'"
				>
					{{ kpis.blockers ?? "—" }}
				</div>
			</div>
		</div>

		<DocTypeListView
			v-if="canRead('taskProgressEntry')"
			doctype="Task Progress Entry"
			:field-order="[
				'name',
				'entry_date',
				'task',
				'cumulative_progress',
				'skilled',
				'unskilled',
				'weather',
				'blocker',
				'blocker_detail',
				'owner',
			]"
			:columns="columns"
			:search-fields="['name', 'narrative', 'blocker_detail']"
			:link-search="[{ field: 'task', doctype: 'Task', titleField: 'subject' }]"
			:filter-values="filterValues"
			:filter-field-map="{ task: 'task', enteredBy: 'owner', blocker: 'blocker' }"
			initial-order-by="entry_date desc"
			cache-key="buildsuite-progress-entry-list"
			row-key="name"
			:search-placeholder="__('Search narrative, task, blocker note…')"
			@row-click="onRowClick"
			@total-change="shown = $event"
		>
			<template #filter-chips>
				<!-- Task filter -->
				<DeskLinkPicker
					v-model="taskFilter"
					class="!w-56"
					doctype="Task"
					label-field="subject"
					value-field="name"
					:search-fields="['subject', 'name']"
					:page-length="10"
					:placeholder="__('Task: Any')"
				/>

				<!-- Entered by filter -->
				<DeskLinkPicker
					v-model="enteredByFilter"
					class="!w-44"
					doctype="User"
					label-field="full_name"
					value-field="name"
					:search-fields="['full_name', 'name']"
					:page-length="10"
					:placeholder="__('Entered by: Any')"
				/>

				<!-- Blocker-only toggle -->
				<button
					v-if="!blockerOnly"
					type="button"
					class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
					style="border-radius: 2px"
					@click="blockerOnly = true"
				>
					🚩 {{ __("Blockers only") }}
				</button>
				<DeskFilterChip
					v-else
					:label="__('Blockers')"
					value="only"
					@remove="blockerOnly = false"
				/>
			</template>

			<template #cell-name="{ row }">
				<DeskLink
					:to="`/progress-entries/${row.name}`"
					@click.stop
					class="font-mono text-xs"
					>{{ row.name }}</DeskLink
				>
			</template>
			<template #cell-entry_date="{ row }">
				<span class="text-xs text-ink-700">{{ fmtDate(row.entry_date) }}</span>
			</template>
			<template #cell-task="{ row }">
				<DeskLink :to="`/tasks/${row.task}`" @click.stop>{{
					taskName(row.task)
				}}</DeskLink>
			</template>
			<template #cell-cumulative_progress="{ row }">
				<div class="flex items-center justify-end gap-2">
					<div class="w-14 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px">
						<div
							class="h-full"
							:class="
								Number(row.cumulative_progress) === 100
									? 'bg-success-500'
									: Number(row.cumulative_progress) > 0
									? 'bg-brand-500'
									: 'bg-ink-300'
							"
							:style="`width:${Number(row.cumulative_progress) || 0}%`"
						></div>
					</div>
					<span class="text-xs tabular-nums w-8 text-right font-medium"
						>{{ Number(row.cumulative_progress) || 0 }}%</span
					>
				</div>
			</template>
			<template #cell-labour="{ row }">
				<span class="text-xs text-ink-700 tabular-nums">
					{{ Number(row.skilled) || 0 }}+{{ Number(row.unskilled) || 0 }}
					<span class="text-ink-400"
						>({{ (Number(row.skilled) || 0) + (Number(row.unskilled) || 0) }})</span
					>
				</span>
			</template>
			<template #cell-weather="{ row }">
				<span v-if="row.weather" class="text-xs">
					<span class="mr-1">{{ WEATHER_ICON[row.weather] || "" }}</span
					>{{ __(row.weather) }}
				</span>
				<span v-else class="text-[10px] text-ink-300">—</span>
			</template>
			<template #cell-flags="{ row }">
				<span
					v-if="Number(row.blocker)"
					class="text-[10px] px-1.5 py-0.5 bg-danger-50 text-danger-700 font-medium"
					style="border-radius: 2px"
					:title="row.blocker_detail || __('Blocker flagged')"
					>🚩 {{ __("Blocker") }}</span
				>
				<span v-else class="text-[10px] text-ink-300">—</span>
			</template>
			<template #cell-owner="{ row }">
				<div v-if="row.owner" class="inline-flex items-center gap-2">
					<UserAvatar :user-id="row.owner" size="xs" />
					<span class="text-xs text-ink-700">{{ row.owner }}</span>
				</div>
				<span v-else class="text-[10px] text-ink-300">—</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ __("No progress entries match these filters") }} ·
					<RouterLink
						v-if="canCreate('taskProgressEntry')"
						to="/progress-entries/new"
						class="desk-link"
						>{{ __("File a new entry") }} →</RouterLink
					>
				</div>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
