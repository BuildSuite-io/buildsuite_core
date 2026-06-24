<script setup>
// StageTaskPicker — self-contained WP-grouped task picker for Stage Planning.
//
// Two display modes:
//   - mode="modal"    → wraps in Teleport + backdrop (default)
//   - mode="embedded" → renders inline (use as wizard step 2)
//
// Drives selection of tasks for inclusion in a Stage Planning's child table
// (stagePlanningTasks). Preserves per-task plannedStart/End/Qty/Unit overrides
// for tasks already in the stage; defaults from underlying task dates for
// newly checked tasks. Supports date-overlap suggestion against the stage
// window, search/assignee/status filters, tristate WP-level checkboxes, and
// a cross-stage co-occurrence hint.
//
// Parent reads the final selection either via the `save` emit OR by calling
// the exposed getCurrentSelection() method (useful for wizard step capture).

import { ref, computed, watch } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { fmtDate } from "@/utils/format";

const props = defineProps({
	open: { type: Boolean, default: false },
	projectId: { type: String, required: true },
	stageName: { type: String, default: "" },
	plannedStart: { type: String, default: "" },
	plannedEnd: { type: String, default: "" },
	initialSelectedTaskIds: { type: Array, default: () => [] },
	existingTaskRows: { type: Array, default: () => [] },
	mode: { type: String, default: "modal" }, // 'modal' | 'embedded'
});

const emit = defineEmits(["update:open", "save", "cancel"]);

const store = useDataStore();
const adapter = createDataAdapter(store);

function toArray(data) {
	if (Array.isArray(data)) return data;
	if (Array.isArray(data?.value)) return data.value;
	return [];
}

// ----- Reactive Adapter Data Resources ---------------------------------------

const tasksResource = ref(null);
watch(
	() => props.projectId,
	(newVal) => {
		if (!newVal) {
			tasksResource.value = null;
			return;
		}
		tasksResource.value = adapter.list("Task", {
			fields: [
				"name",
				"subject",
				"project",
				"work_package",
				"task_status",
				"type as task_type",
				"owner",
				"exp_start_date",
				"exp_end_date",
			],
			filters: [["project", "=", newVal]],
			pageLength: 500,
			cache: `stage-picker-tasks:${newVal}`,
			transform(rows) {
				return rows.map((row) => ({
					id: row?.name || row?.id,
					name: row?.subject || row?.task_name || row?.name || "",
					projectId: row?.project || "",
					workPackageId: row?.work_package || "",
					status: row?.task_status || "Yet To Start",
					priority: row?.priority || "Medium",
					task_type: row?.task_type || "Activity",
					assignee: row?.owner || row?.assignee || "",
					startDate: row?.exp_start_date || row?.start_date || null,
					endDate: row?.exp_end_date || row?.end_date || null,
				}));
			},
		});
	},
	{ immediate: true }
);

const allProjectTasks = computed(() => toArray(tasksResource.value?.data));

const wpsResource = ref(null);
watch(
	() => props.projectId,
	(newVal) => {
		if (!newVal) {
			wpsResource.value = null;
			return;
		}
		wpsResource.value = adapter.list("Work Package", {
			fields: ["name", "code", "work_package_name", "project"],
			filters: [["project", "=", newVal]],
			pageLength: 200,
			cache: `stage-picker-wps:${newVal}`,
			transform(rows) {
				return rows.map((row) => ({
					id: row?.name || row?.id,
					code: row?.code || "",
					name: row?.work_package_name || row?.name || "",
					projectId: row?.project || "",
				}));
			},
		});
	},
	{ immediate: true }
);

const allWPs = computed(() => toArray(wpsResource.value?.data));

const stagesResource = ref(null);
watch(
	() => props.projectId,
	(newVal) => {
		if (!newVal) {
			stagesResource.value = null;
			return;
		}
		stagesResource.value = adapter.list("Stage Planning", {
			fields: ["name", "stage_name", "project", "stage_planning_tasks"],
			filters: [["project", "=", newVal]],
			pageLength: 100,
			cache: `stage-picker-stages:${newVal}`,
			transform(rows) {
				return rows.map((row) => ({
					id: row?.name || row?.id,
					stageName: row?.stage_name || row?.name || "",
					project: row?.project || "",
					workflow_state: row?.workflow_state || "",
					stagePlanningTasks: row?.stage_planning_tasks || [],
				}));
			},
		});
	},
	{ immediate: true }
);

const allStages = computed(() => toArray(stagesResource.value?.data));

// ----- Local state ---------------------------------------------------------

// Selection — Set of task IDs. Set is cheaper than array for toggle ops.
const selectedIds = ref(new Set());

// Per-group expanded state (Set of WP IDs that are expanded). The Unassigned
// group uses the literal key '__unassigned__'.
const expandedGroups = ref(new Set());

// Filters
const searchText = ref("");
const filterAssignee = ref("");
const filterStatus = ref("");

// Toast message (date-overlap suggestion feedback)
const toastMessage = ref("");
let toastTimer = null;

// Cache existing child rows by task id so we can preserve overrides on
// rebuild. Recomputes when existingTaskRows changes.
const existingRowsByTask = computed(() => {
	const map = {};
	for (const row of props.existingTaskRows || []) {
		if (row && row.task) map[row.task] = row;
	}
	return map;
});

// ----- Initial state on open ---------------------------------------------

function resetForOpen() {
	selectedIds.value = new Set(props.initialSelectedTaskIds || []);
	searchText.value = "";
	filterAssignee.value = "";
	filterStatus.value = "";
	toastMessage.value = "";
	if (toastTimer) {
		clearTimeout(toastTimer);
		toastTimer = null;
	}

	// Default group expansion: expand if it contains at least one currently
	// selected task; collapse otherwise.
	const wps = allWPs.value;
	const expanded = new Set();
	for (const wp of wps) {
		const tasks = allProjectTasks.value.filter((t) => t.workPackageId === wp.id);
		if (tasks.some((t) => selectedIds.value.has(t.id))) expanded.add(wp.id);
	}
	const unassignedTasks = allProjectTasks.value.filter((t) => !t.workPackageId);
	if (unassignedTasks.some((t) => selectedIds.value.has(t.id))) {
		expanded.add("__unassigned__");
	}
	expandedGroups.value = expanded;
}

// Modal-mode: reset on each open.
watch(
	() => props.open,
	(isOpen) => {
		if (props.mode === "modal" && isOpen) resetForOpen();
	}
);

// Embedded-mode: reset on projectId / initial-selection / existing-rows change
watch(
	() => [props.projectId, props.initialSelectedTaskIds, props.existingTaskRows],
	() => {
		if (props.mode === "embedded") resetForOpen();
	},
	{ immediate: true }
);

// Watch for initial data load to expand groups
watch([allProjectTasks, allWPs], ([newTasks, newWPs], [oldTasks, oldWPs]) => {
	if (newTasks.length > 0 && (!oldTasks || oldTasks.length === 0)) {
		const expanded = new Set(expandedGroups.value);
		for (const wp of newWPs) {
			const tasks = newTasks.filter((t) => t.workPackageId === wp.id);
			if (tasks.some((t) => selectedIds.value.has(t.id))) expanded.add(wp.id);
		}
		const unassignedTasks = newTasks.filter((t) => !t.workPackageId);
		if (unassignedTasks.some((t) => selectedIds.value.has(t.id))) {
			expanded.add("__unassigned__");
		}
		expandedGroups.value = expanded;
	}
});

// ----- Filtering ----------------------------------------------------------

function matchesFilters(task) {
	if (searchText.value.trim()) {
		const q = searchText.value.trim().toLowerCase();
		if (!(task.name || "").toLowerCase().includes(q)) return false;
	}
	if (filterAssignee.value && task.assignee !== filterAssignee.value) return false;
	if (filterStatus.value && task.status !== filterStatus.value) return false;
	return true;
}

const filteredTasks = computed(() => allProjectTasks.value.filter(matchesFilters));

// WP groups — one entry per WP that has at least one VISIBLE task after
// filtering. Tristate logic operates on what's visible.
const wpGroups = computed(() => {
	const wps = allWPs.value;
	const out = [];
	for (const wp of wps) {
		const visibleTasks = filteredTasks.value.filter((t) => t.workPackageId === wp.id);
		if (visibleTasks.length === 0) continue;
		out.push({ key: wp.id, title: wp.name, tasks: visibleTasks });
	}
	return out;
});

const unassignedGroup = computed(() => {
	const visible = filteredTasks.value.filter((t) => !t.workPackageId);
	if (visible.length === 0) return null;
	return { key: "__unassigned__", title: "Unassigned", tasks: visible };
});

const hasAnyProjectTasks = computed(() => allProjectTasks.value.length > 0);
const hasAnyVisibleTasks = computed(() => filteredTasks.value.length > 0);
const selectionCount = computed(() => selectedIds.value.size);

const anyFilterActive = computed(
	() => !!(searchText.value.trim() || filterAssignee.value || filterStatus.value)
);

// ----- Cross-stage co-occurrence ----------------------------------------

const otherStagesByTask = computed(() => {
	const map = {};
	const stages = allStages.value;
	for (const stg of stages) {
		const state = stg.workflow_state;
		if (state && state !== "Approved" && state !== "Pending Approval") continue;
		if (props.stageName && stg.stageName === props.stageName) continue;
		const rows = stg.stagePlanningTasks || [];
		for (const row of rows) {
			if (!row.task) continue;
			if (!map[row.task]) map[row.task] = [];
			map[row.task].push(stg.stageName || stg.id);
		}
	}
	return map;
});

function coOccurrenceLine(taskId) {
	const names = otherStagesByTask.value[taskId];
	if (!names || names.length === 0) return "";
	if (names.length <= 3) return `Also in: ${names.join(", ")}`;
	const head = names.slice(0, 3).join(", ");
	return `Also in: ${head} …+${names.length - 3} more`;
}

// ----- Group-level tristate helpers --------------------------------------

function groupSelectionState(group) {
	let selected = 0;
	for (const t of group.tasks) if (selectedIds.value.has(t.id)) selected++;
	if (selected === 0) return "none";
	if (selected === group.tasks.length) return "all";
	return "some";
}

function toggleGroup(group) {
	const state = groupSelectionState(group);
	const next = new Set(selectedIds.value);
	if (state === "all") {
		for (const t of group.tasks) next.delete(t.id);
	} else {
		for (const t of group.tasks) next.add(t.id);
	}
	selectedIds.value = next;
}

function toggleTask(taskId) {
	const next = new Set(selectedIds.value);
	if (next.has(taskId)) next.delete(taskId);
	else next.add(taskId);
	selectedIds.value = next;
}

function toggleExpand(key) {
	const next = new Set(expandedGroups.value);
	if (next.has(key)) next.delete(key);
	else next.add(key);
	expandedGroups.value = next;
}

function setIndeterminate(el, state) {
	if (el && el.tagName === "INPUT") {
		el.indeterminate = state === "some";
	}
}

// ----- Date-overlap suggestion ------------------------------------------

const suggestionDisabled = computed(() => !props.plannedStart || !props.plannedEnd);

function suggestByDateOverlap() {
	if (suggestionDisabled.value) return;
	const stageStart = props.plannedStart;
	const stageEnd = props.plannedEnd;
	let count = 0;
	const next = new Set(selectedIds.value);
	for (const t of allProjectTasks.value) {
		if (!t.startDate || !t.endDate) continue;
		const overlaps = t.startDate <= stageEnd && t.endDate >= stageStart;
		if (overlaps && !next.has(t.id)) {
			next.add(t.id);
			count++;
		}
	}
	selectedIds.value = next;
	if (count === 0) {
		showToast("No tasks overlap with the stage window.");
	} else {
		showToast(
			`${count} task${
				count === 1 ? "" : "s"
			} suggested based on date overlap. Review and adjust.`
		);
		const expanded = new Set(expandedGroups.value);
		for (const g of wpGroups.value) {
			if (g.tasks.some((t) => selectedIds.value.has(t.id))) expanded.add(g.key);
		}
		if (
			unassignedGroup.value &&
			unassignedGroup.value.tasks.some((t) => selectedIds.value.has(t.id))
		) {
			expanded.add("__unassigned__");
		}
		expandedGroups.value = expanded;
	}
}

function showToast(msg) {
	toastMessage.value = msg;
	if (toastTimer) clearTimeout(toastTimer);
	toastTimer = setTimeout(() => {
		toastMessage.value = "";
		toastTimer = null;
	}, 5000);
}

function clearFilters() {
	searchText.value = "";
	filterAssignee.value = "";
	filterStatus.value = "";
}

// ----- Save / cancel ----------------------------------------------------

function newRowId() {
	const ts = Date.now().toString().slice(-7);
	const rnd = Math.floor(Math.random() * 1000)
		.toString()
		.padStart(3, "0");
	return `SPT-${ts}${rnd}`;
}

function buildPayload() {
	const ids = Array.from(selectedIds.value);
	const newChildRows = ids.map((taskId) => {
		const existing = existingRowsByTask.value[taskId];
		if (existing) {
			return {
				id: existing.id || newRowId(),
				task: taskId,
				plannedStart: existing.plannedStart || "",
				plannedEnd: existing.plannedEnd || "",
				plannedQty: typeof existing.plannedQty === "number" ? existing.plannedQty : 100,
				qtyUnit: existing.qtyUnit || "%",
			};
		}
		const task = allProjectTasks.value.find((t) => t.id === taskId) || {};
		return {
			id: newRowId(),
			task: taskId,
			plannedStart: task.startDate || "",
			plannedEnd: task.endDate || "",
			plannedQty: 100,
			qtyUnit: "%",
		};
	});
	return { selectedTaskIds: ids, newChildRows };
}

function onSave() {
	emit("save", buildPayload());
	if (props.mode === "modal") emit("update:open", false);
}

function onCancel() {
	emit("cancel");
	if (props.mode === "modal") emit("update:open", false);
}

function onBackdropClick() {
	onCancel();
}

defineExpose({
	getCurrentSelection: () => buildPayload(),
});
</script>

<template>
	<!-- ============= MODAL MODE ============================================= -->
	<Teleport v-if="mode === 'modal'" to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
			@click.self="onBackdropClick"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-4xl shadow-fp-lg flex flex-col dark:bg-[#242424] dark:border-ink-700"
				style="border-radius: 12px; max-height: calc(100vh - 3rem)"
				@click.stop
			>
				<!-- Header -->
				<header
					class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white dark:bg-[#242424] dark:border-ink-700"
					style="border-radius: 12px 12px 0 0"
				>
					<div class="min-w-0 flex-1">
						<h2 class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">
							Add tasks to stage
						</h2>
						<p class="text-[11px] text-ink-500 mt-0.5 truncate">
							<template v-if="stageName">{{ stageName }}</template>
							<template v-else>New stage</template>
							<template v-if="plannedStart && plannedEnd">
								&nbsp;·&nbsp;{{ fmtDate(plannedStart) }} –
								{{ fmtDate(plannedEnd) }}
							</template>
						</p>
					</div>
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3 dark:text-ink-400 dark:hover:text-ink-200"
						aria-label="Close"
						@click="onCancel"
					>
						×
					</button>
				</header>

				<!-- Body (scrollable) -->
				<div class="flex-1 overflow-y-auto">
					<!-- Top bar: suggest button + filters + selection count -->
					<div
						class="px-5 pt-4 pb-3 border-b border-ink-100 bg-white sticky top-0 z-10 dark:bg-[#242424] dark:border-ink-700"
					>
						<div class="flex items-center justify-between gap-3 flex-wrap">
							<button
								type="button"
								class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white text-brand-700 hover:bg-brand-50 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-[#242424] dark:border-ink-700 dark:text-[#F5F5F5] dark:hover:bg-ink-800"
								style="border-radius: 6px"
								:disabled="suggestionDisabled"
								:title="
									suggestionDisabled
										? 'Set stage dates to use suggestion.'
										: 'Suggest tasks whose dates overlap the stage window.'
								"
								@click="suggestByDateOverlap"
							>
								Suggest tasks by date overlap
							</button>
							<span class="text-xs text-ink-700 tabular-nums dark:text-[#F5F5F5]">
								{{ selectionCount }} task{{ selectionCount === 1 ? "" : "s" }}
								selected
							</span>
						</div>

						<div class="flex items-center gap-2 mt-3 flex-wrap">
							<div class="w-64">
								<DeskInput v-model="searchText" placeholder="Search tasks" />
							</div>
							<div class="w-48">
								<DeskSelect v-model="filterAssignee">
									<option value="">— Any assignee —</option>
									<option v-for="m in store.team" :key="m.id" :value="m.id">
										{{ m.name }}
									</option>
								</DeskSelect>
							</div>
							<div class="w-44">
								<DeskSelect v-model="filterStatus">
									<option value="">— Any status —</option>
									<option>Yet To Start</option>
									<option>In Progress</option>
									<option>In Delay</option>
									<option>Completed</option>
									<option>Blocked</option>
								</DeskSelect>
							</div>
						</div>

						<!-- Toast -->
						<div
							v-if="toastMessage"
							class="mt-3 text-[11px] px-3 py-2 bg-brand-50 text-brand-700 border border-brand-100 dark:bg-brand-900/20 dark:text-brand-300 dark:border-brand-800"
							style="border-radius: 6px"
						>
							{{ toastMessage }}
						</div>
					</div>

					<!-- Groups -->
					<div class="px-5 py-4 space-y-3">
						<div
							v-if="!hasAnyProjectTasks"
							class="text-center py-12 px-6 text-sm text-ink-500 dark:text-ink-400"
						>
							No tasks created on this project yet. Create tasks in the Tasks tab
							before adding them to a stage.
						</div>

						<div
							v-else-if="!hasAnyVisibleTasks"
							class="text-center py-12 px-6 text-sm text-ink-500 dark:text-ink-400"
						>
							<div>No tasks match your filters.</div>
							<button
								v-if="anyFilterActive"
								type="button"
								class="text-xs text-brand-700 hover:underline mt-2 dark:text-brand-400"
								@click="clearFilters"
							>
								Clear filters
							</button>
						</div>

						<!-- WP groups -->
						<template v-else>
							<div
								v-for="group in wpGroups"
								:key="group.key"
								class="border border-ink-100 dark:border-ink-700"
								style="border-radius: 6px"
							>
								<!-- Group header -->
								<div
									class="flex items-center gap-2 px-3 py-2 bg-white hover:bg-ink-50 cursor-pointer dark:bg-[#242424] dark:hover:bg-ink-800"
									@click="toggleExpand(group.key)"
								>
									<span
										class="inline-block text-ink-500 text-[10px] transition-transform"
										:style="{
											transform: expandedGroups.has(group.key)
												? 'rotate(90deg)'
												: 'rotate(0deg)',
										}"
										>▶</span
									>
									<input
										type="checkbox"
										class="cursor-pointer accent-brand-600"
										:checked="groupSelectionState(group) === 'all'"
										:ref="
											(el) =>
												setIndeterminate(el, groupSelectionState(group))
										"
										@click.stop
										@change="toggleGroup(group)"
									/>
									<span
										class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5]"
										>{{ group.title }}</span
									>
									<span class="text-[11px] text-ink-500 dark:text-ink-400"
										>· {{ group.tasks.length }} task{{
											group.tasks.length === 1 ? "" : "s"
										}}</span
									>
								</div>

								<!-- Task rows -->
								<div
									v-if="expandedGroups.has(group.key)"
									class="border-t border-ink-100 dark:border-ink-700"
								>
									<div
										v-for="task in group.tasks"
										:key="task.id"
										class="flex items-start gap-3 px-3 py-3 border-b border-ink-5 last:border-b-0 hover:bg-brand-50/40 dark:border-ink-800 dark:hover:bg-brand-950/20"
									>
										<input
											type="checkbox"
											class="mt-1 cursor-pointer accent-brand-600"
											:checked="selectedIds.has(task.id)"
											@change="toggleTask(task.id)"
										/>
										<div class="min-w-0 flex-1">
											<div class="flex items-center gap-2 flex-wrap">
												<span
													class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5] truncate"
													>{{ task.name }}</span
												>
												<StatusBadge
													v-if="task.status"
													:status="task.status"
													size="xs"
												/>
												<StatusBadge
													v-if="task.task_type"
													:status="task.task_type"
													size="xs"
												/>
											</div>
											<div
												class="text-[11px] text-ink-500 dark:text-ink-400 mt-1"
											>
												<template v-if="task.startDate || task.endDate">
													{{
														task.startDate
															? fmtDate(task.startDate)
															: "—"
													}}
													–
													{{
														task.endDate ? fmtDate(task.endDate) : "—"
													}}
												</template>
												<template v-else>No dates set</template>
											</div>
											<div
												v-if="coOccurrenceLine(task.id)"
												class="text-[11px] text-ink-500 italic mt-1 dark:text-ink-400"
											>
												{{ coOccurrenceLine(task.id) }}
											</div>
										</div>
										<UserAvatar
											v-if="task.assignee"
											:user-id="task.assignee"
											size="xs"
										/>
									</div>
								</div>
							</div>

							<!-- Unassigned group -->
							<div
								v-if="unassignedGroup"
								class="border border-ink-100 dark:border-ink-700"
								style="border-radius: 6px"
							>
								<div
									class="flex items-center gap-2 px-3 py-2 bg-white hover:bg-ink-50 cursor-pointer dark:bg-[#242424] dark:hover:bg-ink-800"
									@click="toggleExpand(unassignedGroup.key)"
								>
									<span
										class="inline-block text-ink-500 text-[10px] transition-transform"
										:style="{
											transform: expandedGroups.has(unassignedGroup.key)
												? 'rotate(90deg)'
												: 'rotate(0deg)',
										}"
										>▶</span
									>
									<input
										type="checkbox"
										class="cursor-pointer accent-brand-600"
										:checked="groupSelectionState(unassignedGroup) === 'all'"
										:ref="
											(el) =>
												setIndeterminate(
													el,
													groupSelectionState(unassignedGroup)
												)
										"
										@click.stop
										@change="toggleGroup(unassignedGroup)"
									/>
									<span
										class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5]"
										>{{ unassignedGroup.title }}</span
									>
									<span class="text-[11px] text-ink-500 dark:text-ink-400"
										>· {{ unassignedGroup.tasks.length }} task{{
											unassignedGroup.tasks.length === 1 ? "" : "s"
										}}</span
									>
								</div>
								<div
									v-if="expandedGroups.has(unassignedGroup.key)"
									class="border-t border-ink-100 dark:border-ink-700"
								>
									<div
										v-for="task in unassignedGroup.tasks"
										:key="task.id"
										class="flex items-start gap-3 px-3 py-3 border-b border-ink-5 last:border-b-0 hover:bg-brand-50/40 dark:border-ink-800 dark:hover:bg-brand-950/20"
									>
										<input
											type="checkbox"
											class="mt-1 cursor-pointer accent-brand-600"
											:checked="selectedIds.has(task.id)"
											@change="toggleTask(task.id)"
										/>
										<div class="min-w-0 flex-1">
											<div class="flex items-center gap-2 flex-wrap">
												<span
													class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5] truncate"
													>{{ task.name }}</span
												>
												<StatusBadge
													v-if="task.status"
													:status="task.status"
													size="xs"
												/>
												<StatusBadge
													v-if="task.task_type"
													:status="task.task_type"
													size="xs"
												/>
											</div>
											<div
												class="text-[11px] text-ink-500 dark:text-ink-400 mt-1"
											>
												<template v-if="task.startDate || task.endDate">
													{{
														task.startDate
															? fmtDate(task.startDate)
															: "—"
													}}
													–
													{{
														task.endDate ? fmtDate(task.endDate) : "—"
													}}
												</template>
												<template v-else>No dates set</template>
											</div>
											<div
												v-if="coOccurrenceLine(task.id)"
												class="text-[11px] text-ink-500 italic mt-1 dark:text-ink-400"
											>
												{{ coOccurrenceLine(task.id) }}
											</div>
										</div>
										<UserAvatar
											v-if="task.assignee"
											:user-id="task.assignee"
											size="xs"
										/>
									</div>
								</div>
							</div>
						</template>
					</div>
				</div>

				<!-- Footer -->
				<footer
					class="px-5 py-3 border-t border-ink-200 flex items-center justify-between flex-shrink-0 bg-white dark:bg-[#242424] dark:border-ink-700"
					style="border-radius: 0 0 12px 12px"
				>
					<span class="text-xs text-ink-700 tabular-nums dark:text-ink-400">
						{{ selectionCount }} task{{ selectionCount === 1 ? "" : "s" }} selected
					</span>
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-100 dark:hover:bg-ink-700"
							style="border-radius: 6px"
							@click="onCancel"
						>
							Cancel
						</button>
						<button type="button" class="desk-save-btn" @click="onSave">
							Save selection
						</button>
					</div>
				</footer>
			</div>
		</div>
	</Teleport>

	<!-- ============= EMBEDDED MODE ========================================== -->
	<div
		v-else
		class="bg-white border border-ink-200 dark:bg-[#242424] dark:border-ink-700"
		style="border-radius: 8px"
	>
		<!-- Top bar -->
		<div class="px-5 pt-4 pb-3 border-b border-ink-100 dark:border-ink-700">
			<div class="flex items-center justify-between mb-3">
				<div class="min-w-0 flex-1">
					<div class="text-sm font-semibold text-ink-900 dark:text-[#F5F5F5]">
						<template v-if="stageName">{{ stageName }}</template>
						<template v-else>New stage</template>
					</div>
					<p
						v-if="plannedStart && plannedEnd"
						class="text-[11px] text-ink-500 mt-0.5 dark:text-ink-400"
					>
						{{ fmtDate(plannedStart) }} – {{ fmtDate(plannedEnd) }}
					</p>
				</div>
				<span class="text-xs text-ink-700 tabular-nums dark:text-ink-400">
					{{ selectionCount }} task{{ selectionCount === 1 ? "" : "s" }} selected
				</span>
			</div>

			<div class="flex items-center gap-2 flex-wrap">
				<button
					type="button"
					class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white text-brand-700 hover:bg-brand-50 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-ink-800 dark:border-ink-700 dark:text-[#F5F5F5] dark:hover:bg-ink-700"
					style="border-radius: 6px"
					:disabled="suggestionDisabled"
					:title="
						suggestionDisabled
							? 'Set stage dates to use suggestion.'
							: 'Suggest tasks whose dates overlap the stage window.'
					"
					@click="suggestByDateOverlap"
				>
					Suggest tasks by date overlap
				</button>
				<div class="w-64">
					<DeskInput v-model="searchText" placeholder="Search tasks" />
				</div>
				<div class="w-48">
					<DeskSelect v-model="filterAssignee">
						<option value="">— Any assignee —</option>
						<option v-for="m in store.team" :key="m.id" :value="m.id">
							{{ m.name }}
						</option>
					</DeskSelect>
				</div>
				<div class="w-44">
					<DeskSelect v-model="filterStatus">
						<option value="">— Any status —</option>
						<option>Yet To Start</option>
						<option>In Progress</option>
						<option>In Delay</option>
						<option>Completed</option>
						<option>Blocked</option>
					</DeskSelect>
				</div>
			</div>

			<div
				v-if="toastMessage"
				class="mt-3 text-[11px] px-3 py-2 bg-brand-50 text-brand-700 border border-brand-100 dark:bg-brand-900/20 dark:text-brand-300 dark:border-brand-800"
				style="border-radius: 6px"
			>
				{{ toastMessage }}
			</div>
		</div>

		<!-- Body -->
		<div class="px-5 py-4 space-y-3">
			<div
				v-if="!hasAnyProjectTasks"
				class="text-center py-12 px-6 text-sm text-ink-500 dark:text-ink-400"
			>
				No tasks created on this project yet. Create tasks in the Tasks tab before adding
				them to a stage.
			</div>

			<div
				v-else-if="!hasAnyVisibleTasks"
				class="text-center py-12 px-6 text-sm text-ink-500 dark:text-ink-400"
			>
				<div>No tasks match your filters.</div>
				<button
					v-if="anyFilterActive"
					type="button"
					class="text-xs text-brand-700 hover:underline mt-2 dark:text-brand-450"
					@click="clearFilters"
				>
					Clear filters
				</button>
			</div>

			<template v-else>
				<div
					v-for="group in wpGroups"
					:key="group.key"
					class="border border-ink-100 dark:border-ink-700"
					style="border-radius: 6px"
				>
					<div
						class="flex items-center gap-2 px-3 py-2 bg-white hover:bg-ink-50 cursor-pointer dark:bg-[#242424] dark:hover:bg-ink-800"
						@click="toggleExpand(group.key)"
					>
						<span
							class="inline-block text-ink-500 text-[10px] transition-transform"
							:style="{
								transform: expandedGroups.has(group.key)
									? 'rotate(90deg)'
									: 'rotate(0deg)',
							}"
							>▶</span
						>
						<input
							type="checkbox"
							class="cursor-pointer accent-brand-600"
							:checked="groupSelectionState(group) === 'all'"
							:ref="(el) => setIndeterminate(el, groupSelectionState(group))"
							@click.stop
							@change="toggleGroup(group)"
						/>
						<span class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5]">{{
							group.title
						}}</span>
						<span class="text-[11px] text-ink-500 dark:text-ink-400"
							>· {{ group.tasks.length }} task{{
								group.tasks.length === 1 ? "" : "s"
							}}</span
						>
					</div>

					<div
						v-if="expandedGroups.has(group.key)"
						class="border-t border-ink-100 dark:border-ink-700"
					>
						<div
							v-for="task in group.tasks"
							:key="task.id"
							class="flex items-start gap-3 px-3 py-3 border-b border-ink-5 last:border-b-0 hover:bg-brand-50/40 dark:border-ink-800 dark:hover:bg-brand-950/20"
						>
							<input
								type="checkbox"
								class="mt-1 cursor-pointer accent-brand-600"
								:checked="selectedIds.has(task.id)"
								@change="toggleTask(task.id)"
							/>
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2 flex-wrap">
									<span
										class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5] truncate"
										>{{ task.name }}</span
									>
									<StatusBadge
										v-if="task.status"
										:status="task.status"
										size="xs"
									/>
									<StatusBadge
										v-if="task.task_type"
										:status="task.task_type"
										size="xs"
									/>
								</div>
								<div class="text-[11px] text-ink-500 dark:text-ink-400 mt-1">
									<template v-if="task.startDate || task.endDate">
										{{ task.startDate ? fmtDate(task.startDate) : "—" }} –
										{{ task.endDate ? fmtDate(task.endDate) : "—" }}
									</template>
									<template v-else>No dates set</template>
								</div>
								<div
									v-if="coOccurrenceLine(task.id)"
									class="text-[11px] text-ink-500 italic mt-1 dark:text-ink-400"
								>
									{{ coOccurrenceLine(task.id) }}
								</div>
							</div>
							<UserAvatar v-if="task.assignee" :user-id="task.assignee" size="xs" />
						</div>
					</div>
				</div>

				<div
					v-if="unassignedGroup"
					class="border border-ink-100 dark:border-ink-700"
					style="border-radius: 6px"
				>
					<div
						class="flex items-center gap-2 px-3 py-2 bg-white hover:bg-ink-50 cursor-pointer dark:bg-[#242424] dark:hover:bg-ink-800"
						@click="toggleExpand(unassignedGroup.key)"
					>
						<span
							class="inline-block text-ink-500 text-[10px] transition-transform"
							:style="{
								transform: expandedGroups.has(unassignedGroup.key)
									? 'rotate(90deg)'
									: 'rotate(0deg)',
							}"
							>▶</span
						>
						<input
							type="checkbox"
							class="cursor-pointer accent-brand-600"
							:checked="groupSelectionState(unassignedGroup) === 'all'"
							:ref="
								(el) => setIndeterminate(el, groupSelectionState(unassignedGroup))
							"
							@click.stop
							@change="toggleGroup(unassignedGroup)"
						/>
						<span class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5]">{{
							unassignedGroup.title
						}}</span>
						<span class="text-[11px] text-ink-500 dark:text-ink-400"
							>· {{ unassignedGroup.tasks.length }} task{{
								unassignedGroup.tasks.length === 1 ? "" : "s"
							}}</span
						>
					</div>
					<div
						v-if="expandedGroups.has(unassignedGroup.key)"
						class="border-t border-ink-100 dark:border-ink-700"
					>
						<div
							v-for="task in unassignedGroup.tasks"
							:key="task.id"
							class="flex items-start gap-3 px-3 py-3 border-b border-ink-5 last:border-b-0 hover:bg-brand-50/40 dark:border-ink-800 dark:hover:bg-brand-950/20"
						>
							<input
								type="checkbox"
								class="mt-1 cursor-pointer accent-brand-600"
								:checked="selectedIds.has(task.id)"
								@change="toggleTask(task.id)"
							/>
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2 flex-wrap">
									<span
										class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5] truncate"
										>{{ task.name }}</span
									>
									<StatusBadge
										v-if="task.status"
										:status="task.status"
										size="xs"
									/>
									<StatusBadge
										v-if="task.task_type"
										:status="task.task_type"
										size="xs"
									/>
								</div>
								<div class="text-[11px] text-ink-500 dark:text-ink-400 mt-1">
									<template v-if="task.startDate || task.endDate">
										{{ task.startDate ? fmtDate(task.startDate) : "—" }} –
										{{ task.endDate ? fmtDate(task.endDate) : "—" }}
									</template>
									<template v-else>No dates set</template>
								</div>
								<div
									v-if="coOccurrenceLine(task.id)"
									class="text-[11px] text-ink-500 italic mt-1 dark:text-ink-400"
								>
									{{ coOccurrenceLine(task.id) }}
								</div>
							</div>
							<UserAvatar v-if="task.assignee" :user-id="task.assignee" size="xs" />
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>
