<script setup>
// Tasks list — use the generic DocType list shell so sort controls stay
// consistent with other meta-backed list screens.

import { ref, computed } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { usePermissions } from "@/composables/usePermissions";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DocTypeListView from "@/components/doctype/DocTypeListView.vue";
import { useUserNames } from "@/composables/useUserNames";
import { fmtDate } from "@/utils/format";

const store = useDataStore();
const router = useRouter();
const adapter = createDataAdapter(store);
const { canCreate } = usePermissions();
const { userName } = useUserNames();

const statusFilter = ref("");
const priorityFilter = ref("");
const projectFilter = ref("");
const assigneeFilter = ref("");
const taskTypeFilter = ref("");

function resourceRows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

const projectsResource = adapter.list("Project", {
	fields: ["name", "project_name"],
	orderBy: "project_name asc",
	pageLength: 100,
	cache: "buildsuite-task-project-filters",
});
const projectRows = computed(() => resourceRows(projectsResource));
const projectsMap = computed(() => {
	const map = {};
	projectRows.value.forEach((p) => {
		map[p.name] = p.project_name || p.name;
	});
	return map;
});

const wpsResource = adapter.list("Work Package", {
	fields: ["name", "work_package_name"],
	pageLength: 200,
	cache: "buildsuite-task-wp-map-v2",
});
const wpRows = computed(() => resourceRows(wpsResource));
const wpsMap = computed(() => {
	const map = {};
	wpRows.value.forEach((wp) => {
		map[wp.name] = wp.work_package_name || wp.name;
	});
	return map;
});

function projectName(id) {
	return projectsMap.value[id] || id;
}
function wpName(id) {
	return wpsMap.value[id] || id;
}

// Assignee is Frappe-native `_assign` (a JSON list of users); the UI is
// single-assignee, so surface the first entry.
function assignedUser(row) {
	try {
		const list = JSON.parse(row?._assign || "[]");
		return Array.isArray(list) && list.length ? list[0] : "";
	} catch {
		return "";
	}
}

const filterValues = computed(() => ({
	status: statusFilter.value,
	priority: priorityFilter.value,
	project: projectFilter.value,
	assignee: assigneeFilter.value,
	taskType: taskTypeFilter.value,
}));

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Task" }];

function onRowClick(row) {
	router.push(`/tasks/${row.name}`);
}
</script>

<template>
	<DeskPage title="Task" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink v-if="canCreate('task')" to="/tasks/new" class="desk-save-btn"
				>+ New</RouterLink
			>
		</template>

		<DocTypeListView
			doctype="Task"
			:field-order="[
				'subject',
				'project',
				'work_package',
				'task_status',
				'priority',
				'type',
				'_assign',
				'exp_end_date',
				'progress',
				'modified',
			]"
			:columns="[
				{ key: 'subject', label: 'Task' },
				{ key: 'project', label: 'Project · WP', fields: ['project', 'work_package'] },
				{ key: 'task_status', label: 'Status', preset: 'status' },
				{ key: 'priority', label: 'Priority', preset: 'status' },
				{ key: 'type', label: 'Task Type', preset: 'status' },
				{ key: 'assignee', label: 'Assignee', fields: ['_assign'] },
				{ key: 'exp_end_date', label: 'Due' },
				{ key: 'progress', label: 'Progress', preset: 'progress' },
			]"
			:search-fields="['subject', 'name']"
			:filter-values="filterValues"
			:filter-field-map="{
				status: 'task_status',
				priority: 'priority',
				project: 'project',
				assignee: { field: '_assign', op: 'like', like: true },
				taskType: 'type',
			}"
			cache-key="buildsuite-task-list-generic"
			row-key="name"
			search-placeholder="Search tasks…"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<!-- Status: select when empty, chip when set -->
				<DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-36">
					<option value="">Status: Any</option>
					<option>Yet To Start</option>
					<option>In Progress</option>
					<option>In Delay</option>
					<option>Completed</option>
					<option>Blocked</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Status"
					:value="statusFilter"
					@remove="statusFilter = ''"
				/>

				<!-- Priority -->
				<DeskSelect v-if="!priorityFilter" v-model="priorityFilter" class="!w-36">
					<option value="">Priority: Any</option>
					<option>Low</option>
					<option>Medium</option>
					<option>High</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Priority"
					:value="priorityFilter"
					@remove="priorityFilter = ''"
				/>

				<!-- Project -->
				<DeskSelect v-if="!projectFilter" v-model="projectFilter" class="!w-48">
					<option value="">Project: Any</option>
					<option v-for="p in projectRows" :key="p.name" :value="p.name">
						{{ p.project_name || p.name }}
					</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Project"
					:value="projectName(projectFilter)"
					@remove="projectFilter = ''"
				/>

				<!-- Assignee — picks a real User so it matches the backend `owner` field. -->
				<DeskLinkPicker
					v-if="!assigneeFilter"
					v-model="assigneeFilter"
					class="!w-44"
					doctype="User"
					label-field="full_name"
					value-field="name"
					:search-fields="['full_name', 'name', 'email']"
					:filters="[['enabled', '=', 1]]"
					order-by="full_name asc"
					:page-length="20"
					placeholder="Assignee: Any"
				/>
				<DeskFilterChip
					v-else
					label="Assignee"
					:value="userName(assigneeFilter)"
					@remove="assigneeFilter = ''"
				/>

				<!-- Task Type (proposal §M2 Select) -->
				<DeskSelect v-if="!taskTypeFilter" v-model="taskTypeFilter" class="!w-40">
					<option value="">Task Type: Any</option>
					<option>Activity</option>
					<option>Milestone</option>
					<option>Inspection</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Task Type"
					:value="taskTypeFilter"
					@remove="taskTypeFilter = ''"
				/>
			</template>

			<template #cell-subject="{ row }">
				<span class="text-ink-900 font-medium">{{
					row.subject || row.name || "Untitled task"
				}}</span>
			</template>
			<template #cell-project="{ row }">
				<div class="text-xs text-ink-500">
					<div>{{ projectName(row.project || "") }}</div>
					<div v-if="row.work_package" class="text-ink-400">
						{{ wpName(row.work_package) }}
					</div>
				</div>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status || 'Open'" />
			</template>
			<template #cell-priority="{ row }">
				<StatusBadge :status="row.priority || 'Medium'" size="xs" />
			</template>
			<template #cell-type="{ row }">
				<StatusBadge :status="row.type || 'Activity'" size="xs" />
			</template>
			<template #cell-assignee="{ row }">
				<UserAvatar
					v-if="assignedUser(row)"
					:user-id="assignedUser(row)"
					:show-name="true"
					size="xs"
				/>
				<span v-else class="text-[10px] text-ink-300">—</span>
			</template>
			<template #cell-exp_end_date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.exp_end_date) }}</span>
			</template>
			<template #cell-progress="{ row }">
				<div class="flex items-center justify-end gap-2">
					<div class="w-14 h-1.5 bg-ink-100 overflow-hidden" style="border-radius: 2px">
						<div
							class="h-full"
							:class="
								Number(row.progress) === 100 ? 'bg-success-500' : 'bg-info-500'
							"
							:style="`width:${Number(row.progress) || 0}%`"
						></div>
					</div>
					<span class="text-xs tabular-nums w-8 text-right"
						>{{ Number(row.progress) || 0 }}%</span
					>
				</div>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					No tasks match these filters ·
					<RouterLink v-if="canCreate('task')" to="/tasks/new" class="desk-link"
						>Create a task →</RouterLink
					>
				</div>
			</template>
		</DocTypeListView>
	</DeskPage>
</template>
