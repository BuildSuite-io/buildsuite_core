<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from "vue";
import { RouterLink } from "vue-router";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import TaskFormModal from "@/components/TaskFormModal.vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { usePermissions } from "@/composables/usePermissions";
import { getProjectSchedule } from "@/utils/scheduleApi";

const store = useDataStore();
const adapter = createDataAdapter(store);
const { canCreate, canEditRecord } = usePermissions();

// === State ============================================================
const selectedProject = ref("");
const viewMode = ref("week"); // day | week | month | quarter (zoom)
const groupBy = ref("none"); // none | stage | wp
const collapsedGroups = ref(new Set());
const search = ref("");
const allTasks = ref([]); // view-model: {id,name,task_type,status,startDate,endDate,progress,workPackageId,owner,schedule_conflict,conflict_reason}
const allDeps = ref([]); // {id,predecessor,successor,dependency_type,lag}
const wpData = ref([]); // {name, work_package_name} — By-WP group labels
const stageData = ref([]); // {name, stage_name, planned_start, planned_end, tasks[]} — By-Stage grouping
const projectMeta = ref(null); // {name, startDate, endDate} — project boundary band (S164)
const loading = ref(false);
const errorMsg = ref("");
let errorTimer = null;

const newTaskOpen = ref(false);

const timelineRef = ref(null);
const containerRef = ref(null);

// === Time scale =======================================================
const PX_PER_DAY = { day: 36, week: 12, month: 4, quarter: 2 };
const pxPerDay = computed(() => PX_PER_DAY[viewMode.value]);

const LEFT_PANE_WIDTH = 280;
const ROW_HEIGHT = 52;
const BAR_HEIGHT = 24;
const SUMMARY_BAR_HEIGHT = 12;
const SUMMARY_PAD_Y = (ROW_HEIGHT - SUMMARY_BAR_HEIGHT) / 2;
const HEADER_HEIGHT = 70; // months 24 + sub-ticks 32 + project-boundary band 14
const MIN_BODY_HEIGHT = 312;
const DIAMOND_W = 18;
const ROW_PAD_Y = (ROW_HEIGHT - BAR_HEIGHT) / 2;
const SCROLLBAR_CLEARANCE = 16;

const isDarkMode = computed(
	() => typeof document !== "undefined" && document.documentElement.classList.contains("dark")
);
const diamondBaseFill = computed(() => (isDarkMode.value ? "#F1F5F9" : "#0F172A"));
const diamondBaseStroke = computed(() => (isDarkMode.value ? "#94A3B8" : "#0F172A"));
const diamondTextClass = computed(() => (isDarkMode.value ? "text-ink-100" : "text-ink-900"));

// === Date helpers (inline, view-side) =================================
function parseISO(iso) {
	if (!iso) return null;
	return new Date(String(iso).slice(0, 10) + "T00:00:00");
}
function msToISO(ms) {
	const d = new Date(ms);
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, "0");
	const day = String(d.getDate()).padStart(2, "0");
	return `${y}-${m}-${day}`;
}
function diffDays(a, b) {
	if (!a || !b) return 0;
	return Math.round((parseISO(b).getTime() - parseISO(a).getTime()) / 86400000);
}
function fmtShort(iso) {
	if (!iso) return "";
	return parseISO(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

// === Data load ========================================================
const day = (d) => (d ? String(d).slice(0, 10) : null);

function mapTask(t) {
	return {
		id: t.name,
		name: t.subject || t.name,
		task_type: t.task_type || "Activity",
		status: t.task_status || "Yet To Start",
		startDate: day(t.exp_start_date) || "",
		endDate: day(t.exp_end_date) || "",
		progress: Number(t.progress) || 0,
		workPackageId: t.work_package || null,
		owner: t.owner || null,
		schedule_conflict: false,
		conflict_reason: "",
	};
}
function buildDeps(list) {
	const out = [];
	for (const t of list) {
		for (const p of t.predecessors || []) {
			out.push({
				id: `${t.name}<-${p.task}`,
				predecessor: p.task,
				successor: t.name,
				dependency_type: p.dependency_type || "FS",
				lag: p.lag_days || 0,
			});
		}
	}
	return out;
}
async function loadSchedule() {
	if (!selectedProject.value) {
		allTasks.value = [];
		allDeps.value = [];
		wpData.value = [];
		stageData.value = [];
		projectMeta.value = null;
		return;
	}
	loading.value = true;
	try {
		const res = await getProjectSchedule(selectedProject.value);
		const list = res?.tasks || [];
		allTasks.value = list.map(mapTask);
		allDeps.value = buildDeps(list);
		wpData.value = res?.work_packages || [];
		stageData.value = res?.stages || [];
		projectMeta.value = {
			name: res?.project_name || selectedProject.value,
			startDate: day(res?.project_start),
			endDate: day(res?.project_end),
		};
	} catch (err) {
		flashError(err?.message || "Failed to load the schedule.");
		allTasks.value = [];
		allDeps.value = [];
		wpData.value = [];
		stageData.value = [];
		projectMeta.value = null;
	} finally {
		loading.value = false;
		nextTick(jumpToToday);
	}
}
watch(selectedProject, loadSchedule, { immediate: true });

// === Permissions ======================================================
const canEditAny = computed(() => allTasks.value.some((t) => canEditRecord("task", t)));
function canEditTask(task) {
	return canEditRecord("task", task);
}
const canCreateHere = computed(() => !!selectedProject.value && canCreate("task"));

// === Data computeds ===================================================
const allSorted = computed(() =>
	allTasks.value.slice().sort((a, b) => {
		const aDated = !!(a.startDate && a.endDate);
		const bDated = !!(b.startDate && b.endDate);
		if (aDated && !bDated) return -1;
		if (!aDated && bDated) return 1;
		if (aDated) {
			return (
				(a.startDate || "").localeCompare(b.startDate || "") ||
				(a.endDate || "").localeCompare(b.endDate || "")
			);
		}
		return (a.name || "").localeCompare(b.name || "");
	})
);
// Search filters the rows (client-side); the axis uses the unfiltered set so it doesn't shift.
const tasks = computed(() => {
	const q = search.value.trim().toLowerCase();
	if (!q) return allSorted.value;
	return allSorted.value.filter(
		(t) => t.name.toLowerCase().includes(q) || t.id.toLowerCase().includes(q)
	);
});

const dateRange = computed(() => {
	if (!allSorted.value.length) return null;
	const dated = allSorted.value.filter((t) => t.startDate && t.endDate);
	if (!dated.length) {
		const now = Date.now();
		const minD = new Date(now - 30 * 86400000);
		minD.setDate(1);
		const maxD = new Date(now + 90 * 86400000);
		maxD.setMonth(maxD.getMonth() + 1);
		maxD.setDate(0);
		return { minMs: minD.getTime(), maxMs: maxD.getTime() };
	}
	let minMs = Infinity;
	let maxMs = -Infinity;
	for (const t of dated) {
		const s = parseISO(t.startDate).getTime();
		const e = parseISO(t.endDate).getTime();
		if (s < minMs) minMs = s;
		if (e > maxMs) maxMs = e;
	}
	const minD = new Date(minMs - 86400000 * 7);
	minD.setDate(1);
	const maxD = new Date(maxMs + 86400000 * 14);
	maxD.setMonth(maxD.getMonth() + 1);
	maxD.setDate(0);
	return { minMs: minD.getTime(), maxMs: maxD.getTime() };
});

function dateToX(iso) {
	if (!iso || !dateRange.value) return 0;
	const ms = parseISO(iso).getTime();
	return ((ms - dateRange.value.minMs) / 86400000) * pxPerDay.value;
}
const timelineWidth = computed(() => {
	if (!dateRange.value) return 1000;
	const days = (dateRange.value.maxMs - dateRange.value.minMs) / 86400000;
	return Math.max(800, days * pxPerDay.value);
});
const timelineHeight = computed(() => Math.max(layoutRows.value.length, 1) * ROW_HEIGHT);
const effectiveBodyHeight = computed(
	() => Math.max(timelineHeight.value, MIN_BODY_HEIGHT) + SCROLLBAR_CLEARANCE
);
const todayX = computed(() => dateToX(new Date().toISOString().slice(0, 10)));

// S164 — project boundary band: dashed markers at project start/end + a soft
// in-bounds tint + a header pill. Hidden when the project lacks either date.
const projectBand = computed(() => {
	const p = projectMeta.value;
	if (!p || !p.startDate || !p.endDate) return null;
	const startX = dateToX(p.startDate);
	const endX = dateToX(p.endDate);
	if (endX < startX) return null;
	return { startX, endX, startISO: p.startDate, endISO: p.endDate, name: p.name };
});

// === Type / status helpers ===========================================
function isOverdueTask(t) {
	if (!t || t.status === "Completed" || !t.endDate) return false;
	return t.endDate < new Date().toISOString().slice(0, 10);
}
function isUndatedTask(t) {
	if (t.task_type === "Milestone") return !t.endDate;
	return !t.startDate || !t.endDate;
}
// S163 — high contrast: the bar is a LIGHT track (status-tinted -100 bg + -700
// border); the inner progress div carries the SATURATED -600 fill sized to
// progress%. Reads instantly in both light + dark mode.
function barClass(task) {
	if (task.schedule_conflict) return "bg-danger-100 border-danger-700";
	if (task.status === "Completed") return "bg-success-100 border-success-700";
	if (task.status === "In Progress") return "bg-brand-100 border-brand-700";
	if (task.status === "In Delay") return "bg-warning-100 border-warning-700";
	if (task.status === "Blocked") return "bg-ink-200 border-ink-600";
	return "bg-ink-100 border-ink-400";
}
function barFillClass(task) {
	if (task.schedule_conflict) return "bg-danger-600";
	if (task.status === "Completed") return "bg-success-600";
	if (task.status === "In Progress") return "bg-brand-600";
	if (task.status === "In Delay") return "bg-warning-600";
	if (task.status === "Blocked") return "bg-ink-500";
	return "bg-ink-300";
}

// === Summary roll-ups (computed) ======================================
function weightedProgress(members) {
	let totalDur = 0;
	let weightedSum = 0;
	let fallbackCount = 0;
	let fallbackSum = 0;
	for (const t of members) {
		const pct = Number(t.progress) || 0;
		fallbackCount++;
		fallbackSum += pct;
		if (t.task_type === "Milestone") continue;
		if (!t.startDate || !t.endDate) continue;
		const dur = diffDays(t.startDate, t.endDate) + 1;
		if (dur > 0) {
			totalDur += dur;
			weightedSum += pct * dur;
		}
	}
	if (totalDur > 0) return Math.round(weightedSum / totalDur);
	if (fallbackCount > 0) return Math.round(fallbackSum / fallbackCount);
	return 0;
}
function computeRollup(members, plannedStart = null, plannedEnd = null) {
	let computedStart = null;
	let computedFinish = null;
	for (const t of members) {
		if (t.task_type === "Milestone") continue;
		if (!t.startDate || !t.endDate) continue;
		if (!computedStart || t.startDate < computedStart) computedStart = t.startDate;
		if (!computedFinish || t.endDate > computedFinish) computedFinish = t.endDate;
	}
	for (const t of members) {
		if (t.task_type !== "Milestone" || !t.endDate) continue;
		if (!computedFinish || t.endDate > computedFinish) computedFinish = t.endDate;
	}
	const pct = weightedProgress(members);
	const slipDays =
		computedFinish && plannedEnd && computedFinish > plannedEnd
			? diffDays(plannedEnd, computedFinish)
			: 0;
	return {
		computedStart,
		computedFinish,
		pct,
		plannedStart,
		plannedEnd,
		slipDays,
		memberCount: members.length,
	};
}

const wpNameMap = computed(() => {
	const m = {};
	for (const w of wpData.value) m[w.name] = w.work_package_name || w.name;
	return m;
});

// groupedRows — flat sequence of group headers + task rows (search-filtered tasks).
const groupedRows = computed(() => {
	if (!selectedProject.value) return [];
	const rows = [];
	const all = tasks.value;
	if (groupBy.value === "none") {
		for (const t of all) rows.push({ kind: "task", task: t, groupKey: null });
		return rows;
	}
	if (groupBy.value === "stage") {
		// Schedule structure: membership + planned baseline → "+Nd LATE" slip badge.
		const seen = new Set();
		for (const stage of stageData.value) {
			const memberIds = stage.tasks || [];
			const members = all.filter((t) => memberIds.includes(t.id));
			members.forEach((t) => seen.add(t.id));
			const ru = computeRollup(members, day(stage.planned_start), day(stage.planned_end));
			const collapsed = collapsedGroups.value.has(stage.name);
			rows.push({
				kind: "group",
				key: stage.name,
				axis: "stage",
				name: stage.stage_name || stage.name,
				members,
				collapsed,
				...ru,
			});
			if (!collapsed)
				for (const t of members)
					rows.push({ kind: "task", task: t, groupKey: stage.name });
		}
		const unstaged = all.filter((t) => !seen.has(t.id));
		if (unstaged.length) {
			const ru = computeRollup(unstaged);
			const collapsed = collapsedGroups.value.has("__unstaged__");
			rows.push({
				kind: "group",
				key: "__unstaged__",
				axis: "stage",
				name: "Not in a stage",
				members: unstaged,
				collapsed,
				...ru,
			});
			if (!collapsed)
				for (const t of unstaged)
					rows.push({ kind: "task", task: t, groupKey: "__unstaged__" });
		}
		return rows;
	}
	// By Work Package (cost/control axis — no baseline).
	const wpIds = [];
	for (const t of all)
		if (t.workPackageId && !wpIds.includes(t.workPackageId)) wpIds.push(t.workPackageId);
	for (const wpId of wpIds) {
		const members = all.filter((t) => t.workPackageId === wpId);
		const ru = computeRollup(members);
		const collapsed = collapsedGroups.value.has(wpId);
		rows.push({
			kind: "group",
			key: wpId,
			axis: "wp",
			name: wpNameMap.value[wpId] || wpId,
			members,
			collapsed,
			...ru,
		});
		if (!collapsed)
			for (const t of members) rows.push({ kind: "task", task: t, groupKey: wpId });
	}
	const noWP = all.filter((t) => !t.workPackageId);
	if (noWP.length) {
		const ru = computeRollup(noWP);
		const collapsed = collapsedGroups.value.has("__nowp__");
		rows.push({
			kind: "group",
			key: "__nowp__",
			axis: "wp",
			name: "Direct project tasks",
			members: noWP,
			collapsed,
			...ru,
		});
		if (!collapsed)
			for (const t of noWP) rows.push({ kind: "task", task: t, groupKey: "__nowp__" });
	}
	return rows;
});
const layoutRows = computed(() =>
	groupedRows.value.map((r, i) => ({ ...r, rowIndex: i, rowY: i * ROW_HEIGHT }))
);

const summaryBars = computed(() => {
	const out = [];
	for (const r of layoutRows.value) {
		if (r.kind !== "group") continue;
		if (!r.computedStart || !r.computedFinish) {
			out.push({ group: r, rowY: r.rowY, hasBar: false });
			continue;
		}
		const barStart = r.axis === "stage" && r.plannedStart ? r.plannedStart : r.computedStart;
		const x = dateToX(barStart);
		const width = Math.max(4, dateToX(r.computedFinish) - x);
		const plannedTickX = r.axis === "stage" && r.plannedEnd ? dateToX(r.plannedEnd) : null;
		let lateStartX = null;
		let lateWidth = 0;
		if (r.slipDays > 0 && r.plannedEnd) {
			lateStartX = dateToX(r.plannedEnd);
			lateWidth = Math.max(2, dateToX(r.computedFinish) - lateStartX);
		}
		const fillPx = (width * Math.min(100, r.pct)) / 100;
		out.push({
			group: r,
			rowY: r.rowY,
			x,
			width,
			fillPx,
			plannedTickX,
			lateStartX,
			lateWidth,
			hasBar: true,
		});
	}
	return out;
});

// === Bars =============================================================
const bars = computed(() => {
	const out = [];
	for (const r of layoutRows.value) {
		if (r.kind !== "task") continue;
		const t = r.task;
		const isMilestone = t.task_type === "Milestone";
		const isInspection = t.task_type === "Inspection";
		const undated = isUndatedTask(t);
		let bx, bw;
		if (undated) {
			bx = 0;
			bw = 0;
		} else if (isMilestone) {
			bx = dateToX(t.endDate);
			bw = 0;
		} else {
			bx = dateToX(t.startDate);
			bw = Math.max(2, dateToX(t.endDate) - bx);
		}
		out.push({
			task: t,
			x: bx,
			y: r.rowY + ROW_PAD_Y,
			width: bw,
			rowY: r.rowY,
			undated,
			isMilestone,
			isInspection,
			isOverdue: isOverdueTask(t),
		});
	}
	return out;
});
const barById = computed(() => {
	const m = new Map();
	for (const b of bars.value) m.set(b.task.id, b);
	return m;
});

// === Dependencies + arrows ============================================
const dependencies = computed(() => {
	const visibleIds = new Set(tasks.value.map((t) => t.id));
	return allDeps.value.filter(
		(d) => visibleIds.has(d.predecessor) && visibleIds.has(d.successor)
	);
});
function arrowPath(fromX, fromY, toX, toY, type) {
	const stub = 12;
	if (type === "FS") {
		const midX = Math.max(fromX + stub, toX - stub);
		return `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`;
	}
	if (type === "SS") {
		const midX = Math.min(fromX, toX) - stub;
		return `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`;
	}
	const midX = Math.max(fromX, toX) + stub;
	return `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`;
}
const arrows = computed(() => {
	const out = [];
	for (const dep of dependencies.value) {
		const fromBar = barById.value.get(dep.predecessor);
		const toBar = barById.value.get(dep.successor);
		if (!fromBar || !toBar || fromBar.undated || toBar.undated) continue;
		let fromX, toX;
		if (dep.dependency_type === "FS") {
			fromX = fromBar.x + fromBar.width;
			toX = toBar.x;
		} else if (dep.dependency_type === "SS") {
			fromX = fromBar.x;
			toX = toBar.x;
		} else {
			fromX = fromBar.x + fromBar.width;
			toX = toBar.x + toBar.width;
		}
		const fromY = fromBar.y + BAR_HEIGHT / 2;
		const toY = toBar.y + BAR_HEIGHT / 2;
		out.push({
			dep,
			path: arrowPath(fromX, fromY, toX, toY, dep.dependency_type),
			isViolated: !!toBar.task.schedule_conflict,
		});
	}
	return out;
});

// === Header ticks =====================================================
const monthTicks = computed(() => {
	if (!dateRange.value) return [];
	const out = [];
	const cursor = new Date(dateRange.value.minMs);
	cursor.setDate(1);
	while (cursor.getTime() < dateRange.value.maxMs) {
		out.push({
			label: cursor.toLocaleDateString("en-IN", { month: "short", year: "2-digit" }),
			x: dateToX(msToISO(cursor.getTime())),
		});
		cursor.setMonth(cursor.getMonth() + 1);
	}
	return out;
});
function weekOf(d) {
	const start = new Date(d.getFullYear(), 0, 1);
	const days = Math.floor((d - start) / 86400000);
	return Math.ceil((days + start.getDay() + 1) / 7);
}
const subTicks = computed(() => {
	if (!dateRange.value) return [];
	const out = [];
	const cursor = new Date(dateRange.value.minMs);
	const stride =
		viewMode.value === "day"
			? 1
			: viewMode.value === "week"
			? 7
			: viewMode.value === "month"
			? 30
			: 90;
	while (cursor.getTime() < dateRange.value.maxMs) {
		let label = "";
		if (viewMode.value === "day") label = String(cursor.getDate());
		else if (viewMode.value === "week") label = `W${weekOf(cursor)}`;
		else if (viewMode.value === "month")
			label = cursor.toLocaleDateString("en-IN", { month: "short" });
		else label = `Q${Math.floor(cursor.getMonth() / 3) + 1}`;
		out.push({ label, x: dateToX(msToISO(cursor.getTime())) });
		cursor.setDate(cursor.getDate() + stride);
	}
	return out;
});

// === Grouping controls ================================================
function setViewMode(m) {
	viewMode.value = m;
}
function setGroupBy(g) {
	groupBy.value = g;
}
function toggleGroup(key) {
	const next = new Set(collapsedGroups.value);
	if (next.has(key)) next.delete(key);
	else next.add(key);
	collapsedGroups.value = next;
}
function expandAllGroups() {
	collapsedGroups.value = new Set();
}
function collapseAllGroups() {
	const keys = new Set();
	for (const r of groupedRows.value) if (r.kind === "group") keys.add(r.key);
	collapsedGroups.value = keys;
}

// === Inline date inputs ===============================================
// Manual date edit from the task list — persists this task's own dates only
// (no downstream cascade in this read-only-first increment).
async function onScheduleInput(task, field, evt) {
	if (!canEditTask(task)) return;
	const newDate = evt.target?.value || "";
	const isMs = task.task_type === "Milestone";
	const newStart = isMs ? null : field === "startDate" ? newDate : task.startDate;
	const newEnd = field === "endDate" ? newDate : task.endDate;
	try {
		await adapter.update("Task", task.id, {
			exp_start_date: newStart || null,
			exp_end_date: newEnd || null,
		});
	} catch (err) {
		flashError(err?.message || "Failed to update the task dates.");
	}
	await loadSchedule();
}

// === Zoom (Ctrl+wheel) + Today ========================================
function onTimelineWheel(e) {
	if (!(e.ctrlKey || e.metaKey)) return;
	e.preventDefault();
	const order = ["quarter", "month", "week", "day"];
	const i = order.indexOf(viewMode.value);
	if (e.deltaY < 0 && i < order.length - 1) viewMode.value = order[i + 1];
	else if (e.deltaY > 0 && i > 0) viewMode.value = order[i - 1];
}
function jumpToToday() {
	if (!timelineRef.value) return;
	timelineRef.value.scrollLeft = Math.max(0, todayX.value - timelineRef.value.clientWidth / 2);
}

// === Misc =============================================================
function flashError(msg) {
	if (!msg) return;
	errorMsg.value = msg;
	if (errorTimer) clearTimeout(errorTimer);
	errorTimer = setTimeout(() => (errorMsg.value = ""), 4000);
}
function onTaskCreated() {
	loadSchedule();
}
onBeforeUnmount(() => {
	if (errorTimer) clearTimeout(errorTimer);
});
</script>

<template>
	<div class="px-6 py-4">
		<div class="flex items-center justify-between mb-4">
			<div>
				<h1 class="text-lg font-semibold text-ink-900">Schedule</h1>
				<p class="text-xs text-ink-500 mt-0.5">
					Gantt timeline — view the schedule and adjust task dates from the list
				</p>
			</div>
			<div
				v-if="!canEditAny && allTasks.length"
				class="text-[11px] px-2 py-1 bg-ink-100 text-ink-600 rounded-full"
			>
				Read-only — your role cannot edit tasks
			</div>
		</div>

		<!-- Edit hint -->
		<div
			v-if="canEditAny && allTasks.length"
			class="mb-2 text-[11px] text-ink-500 flex items-center gap-2 flex-wrap"
		>
			<span>Edit a task's start / due dates inline in the list on the left.</span>
		</div>

		<!-- Toolbar -->
		<div
			class="bg-white border border-ink-200 rounded-t-lg px-3 py-2 flex items-center gap-3 flex-wrap"
		>
			<div class="flex items-center gap-2">
				<label class="text-xs text-ink-500">Project</label>
				<DeskLinkPicker
					v-model="selectedProject"
					class="!w-56"
					doctype="Project"
					label-field="project_name"
					value-field="name"
					:search-fields="['project_name', 'custom_project_id', 'name']"
					placeholder="— Pick a project —"
				/>
			</div>

			<div class="flex border border-ink-200 rounded overflow-hidden">
				<button
					v-for="m in ['day', 'week', 'month', 'quarter']"
					:key="m"
					class="px-3 py-1 text-xs capitalize border-l border-ink-200 first:border-l-0"
					:class="
						viewMode === m ? 'bg-brand-50 text-brand-700' : 'bg-white text-ink-600'
					"
					@click="setViewMode(m)"
				>
					{{ m }}
				</button>
			</div>

			<div class="flex border border-ink-200 rounded overflow-hidden">
				<button
					class="px-3 py-1 text-xs"
					:class="
						groupBy === 'none' ? 'bg-brand-50 text-brand-700' : 'bg-white text-ink-600'
					"
					@click="setGroupBy('none')"
				>
					None
				</button>
				<button
					class="px-3 py-1 text-xs border-l border-ink-200"
					:class="
						groupBy === 'stage'
							? 'bg-brand-50 text-brand-700'
							: 'bg-white text-ink-600'
					"
					@click="setGroupBy('stage')"
				>
					By Stage
				</button>
				<button
					class="px-3 py-1 text-xs border-l border-ink-200"
					:class="
						groupBy === 'wp' ? 'bg-brand-50 text-brand-700' : 'bg-white text-ink-600'
					"
					@click="setGroupBy('wp')"
				>
					By WP
				</button>
			</div>

			<button
				class="text-xs px-2.5 py-1 border border-ink-200 rounded bg-white hover:bg-ink-50"
				@click="jumpToToday"
			>
				Today
			</button>

			<button v-if="canCreateHere" class="desk-save-btn" @click="newTaskOpen = true">
				+ New Task
			</button>

			<div class="ml-auto text-xs text-ink-500 flex items-center gap-3">
				<span>{{ allTasks.length }} tasks</span>
				<span v-if="allDeps.length">· {{ allDeps.length }} dependencies</span>
				<span class="text-ink-400 italic hidden md:inline">Ctrl + scroll to zoom</span>
			</div>
		</div>

		<!-- Gantt container -->
		<div
			ref="containerRef"
			class="bg-white border border-ink-200 border-t-0 rounded-b-lg overflow-hidden relative"
		>
			<div v-if="!selectedProject" class="p-10 text-center text-sm text-ink-400">
				Select a project to view its schedule.
			</div>
			<div v-else-if="loading" class="p-10 text-center text-sm text-ink-400">
				Loading schedule…
			</div>
			<div v-else-if="!allTasks.length" class="p-10 text-center text-sm text-ink-400">
				No tasks in this project yet.
			</div>

			<div
				v-else
				class="flex"
				:style="{ height: HEADER_HEIGHT + effectiveBodyHeight + 'px' }"
			>
				<!-- Left pane -->
				<div
					class="flex-shrink-0 border-r border-ink-200 overflow-hidden"
					:style="{ width: LEFT_PANE_WIDTH + 'px' }"
				>
					<div
						class="bg-ink-50 border-b border-ink-200 flex items-center justify-between gap-2 px-2"
						:style="{ height: HEADER_HEIGHT + 'px' }"
					>
						<!-- S162 — task search is the left-pane column header (icon + clear). -->
						<div class="relative flex-1 min-w-0">
							<svg
								class="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-400 pointer-events-none"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
								/>
							</svg>
							<input
								v-model="search"
								type="text"
								placeholder="Search tasks…"
								class="w-full text-xs pl-7 pr-7 py-1 border border-ink-200 rounded bg-white text-ink-800 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
							<button
								v-if="search"
								type="button"
								class="absolute right-1.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400 hover:text-ink-700"
								title="Clear search"
								aria-label="Clear search"
								@click="search = ''"
							>
								<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M6 18L18 6M6 6l12 12"
									/>
								</svg>
							</button>
						</div>
						<div
							v-if="groupBy !== 'none'"
							class="flex items-center gap-1.5 flex-shrink-0"
						>
							<button
								class="text-[10px] text-brand-700 hover:underline"
								title="Expand all groups"
								@click="expandAllGroups"
							>
								Expand
							</button>
							<span class="text-ink-300 text-[10px]">·</span>
							<button
								class="text-[10px] text-brand-700 hover:underline"
								title="Collapse all groups"
								@click="collapseAllGroups"
							>
								Collapse
							</button>
						</div>
					</div>
					<div>
						<template
							v-for="(r, idx) in layoutRows"
							:key="r.kind + '-' + (r.task?.id || r.key) + '-' + idx"
						>
							<!-- Group header -->
							<div
								v-if="r.kind === 'group'"
								:style="{ height: ROW_HEIGHT + 'px' }"
								class="flex items-center px-2 border-b border-ink-200 bg-ink-50/60 cursor-pointer hover:bg-brand-50/40"
								@click="toggleGroup(r.key)"
							>
								<span class="text-[10px] text-ink-500 w-4 flex-shrink-0">{{
									r.collapsed ? "▸" : "▾"
								}}</span>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-1.5">
										<span
											class="text-xs text-ink-900 truncate font-semibold"
											>{{ r.name }}</span
										>
										<span class="text-[10px] text-ink-500 flex-shrink-0"
											>· {{ r.memberCount }}</span
										>
									</div>
									<div class="flex items-center gap-1.5 mt-0.5">
										<span class="text-[10px] text-ink-500 tabular-nums">
											{{
												r.computedFinish
													? "finish " + fmtShort(r.computedFinish)
													: "no dates"
											}}
										</span>
										<span class="text-[10px] text-ink-500 tabular-nums"
											>· {{ r.pct }}%</span
										>
										<span
											v-if="r.axis === 'stage' && r.slipDays > 0"
											class="text-[9px] px-1.5 py-0 bg-warning-50 text-warning-700 rounded-full font-medium tabular-nums"
											>+{{ r.slipDays }}d LATE</span
										>
									</div>
								</div>
							</div>

							<!-- Task row -->
							<RouterLink
								v-else
								:to="`/tasks/${r.task.id}`"
								:style="{ height: ROW_HEIGHT + 'px' }"
								class="flex items-center px-3 border-b border-ink-100 hover:bg-brand-50"
								:class="idx % 2 ? 'bg-ink-50/20' : ''"
							>
								<div class="flex-1 min-w-0">
									<div class="text-xs text-ink-900 truncate font-medium">
										{{ r.task.name }}
									</div>
									<div
										class="flex items-center gap-1 mt-0.5"
										@click.stop
										@mousedown.stop
									>
										<template v-if="r.task.task_type === 'Milestone'">
											<input
												type="date"
												class="schedule-date-input"
												:value="r.task.endDate || ''"
												:disabled="!canEditTask(r.task)"
												title="Milestone date (due)"
												@click.stop
												@mousedown.stop
												@change="
													onScheduleInput(r.task, 'endDate', $event)
												"
											/>
											<span class="text-[9px] text-ink-400 ml-1"
												>milestone</span
											>
										</template>
										<template v-else>
											<input
												type="date"
												class="schedule-date-input"
												:value="r.task.startDate || ''"
												:disabled="!canEditTask(r.task)"
												title="Start date"
												@click.stop
												@mousedown.stop
												@change="
													onScheduleInput(r.task, 'startDate', $event)
												"
											/>
											<span class="text-[10px] text-ink-400">→</span>
											<input
												type="date"
												class="schedule-date-input"
												:value="r.task.endDate || ''"
												:disabled="!canEditTask(r.task)"
												title="Due date"
												@click.stop
												@mousedown.stop
												@change="
													onScheduleInput(r.task, 'endDate', $event)
												"
											/>
										</template>
									</div>
								</div>
								<div
									v-if="r.task.schedule_conflict"
									class="ml-1 text-[10px] px-1.5 py-0.5 bg-danger-50 text-danger-700 rounded-full whitespace-nowrap"
									:title="r.task.conflict_reason"
								>
									!
								</div>
							</RouterLink>
						</template>
					</div>
				</div>

				<!-- Right pane — timeline -->
				<div
					ref="timelineRef"
					class="flex-1 overflow-x-auto overflow-y-hidden relative"
					@wheel="onTimelineWheel"
				>
					<div
						:style="{
							width: timelineWidth + 'px',
							height: HEADER_HEIGHT + effectiveBodyHeight + 'px',
						}"
						class="relative"
					>
						<!-- Header strip -->
						<div
							class="absolute top-0 left-0 right-0 bg-ink-50 border-b border-ink-200"
							:style="{ height: HEADER_HEIGHT + 'px' }"
						>
							<div class="relative border-b border-ink-200" style="height: 24px">
								<div
									v-for="(m, i) in monthTicks"
									:key="'m-' + i"
									class="absolute top-0 px-2 py-1 text-[11px] text-ink-700 font-medium whitespace-nowrap border-l border-ink-200"
									:style="{ left: m.x + 'px', height: '24px' }"
								>
									{{ m.label }}
								</div>
							</div>
							<div class="relative" style="height: 32px">
								<div
									v-for="(s, i) in subTicks"
									:key="'s-' + i"
									class="absolute top-0 px-1 py-1 text-[10px] text-ink-500 whitespace-nowrap border-l border-ink-100"
									:style="{ left: s.x + 'px', height: '32px' }"
								>
									{{ s.label }}
								</div>
							</div>
							<!-- S164 — project boundary band row (months 24 + sub-ticks 32 + this 14) -->
							<div class="relative bg-white" style="height: 14px">
								<div
									v-if="projectBand"
									class="absolute flex items-center px-2 font-medium text-brand-700 truncate"
									:style="{
										left: projectBand.startX + 'px',
										width:
											Math.max(40, projectBand.endX - projectBand.startX) +
											'px',
										top: '2px',
										height: '10px',
										background: 'rgba(22, 163, 74, 0.18)',
										border: '1px solid rgba(22, 163, 74, 0.55)',
										borderRadius: '2px',
									}"
									:title="
										projectBand.name +
										' · ' +
										fmtShort(projectBand.startISO) +
										' → ' +
										fmtShort(projectBand.endISO)
									"
								>
									<span class="truncate text-[9px] leading-none"
										>{{ fmtShort(projectBand.startISO) }} →
										{{ fmtShort(projectBand.endISO) }}</span
									>
								</div>
							</div>
						</div>

						<!-- Body -->
						<div
							:style="{
								position: 'absolute',
								top: HEADER_HEIGHT + 'px',
								left: 0,
								right: 0,
								height: timelineHeight + 'px',
							}"
						>
							<!-- Row backgrounds -->
							<div
								v-for="(r, idx) in layoutRows"
								:key="'row-' + r.kind + '-' + (r.task?.id || r.key) + '-' + idx"
								:style="{
									position: 'absolute',
									top: r.rowY + 'px',
									left: 0,
									width: '100%',
									height: ROW_HEIGHT + 'px',
								}"
								:class="[
									r.kind === 'group'
										? 'bg-ink-50/60 border-b border-ink-200'
										: idx % 2
										? 'bg-ink-50/20'
										: '',
								]"
							></div>

							<!-- Summary bars -->
							<div
								v-for="sb in summaryBars"
								:key="'sum-' + sb.group.key"
								:style="{
									position: 'absolute',
									top: sb.rowY + SUMMARY_PAD_Y + 'px',
									left: sb.hasBar ? sb.x + 'px' : '0px',
									width: sb.hasBar ? sb.width + 'px' : '0',
									height: SUMMARY_BAR_HEIGHT + 'px',
								}"
							>
								<template v-if="sb.hasBar">
									<div
										class="absolute inset-0 bg-ink-200/60 rounded-sm pointer-events-none"
									></div>
									<div
										v-if="sb.fillPx > 0"
										class="absolute left-0 top-0 bottom-0 bg-brand-500/70 rounded-l-sm pointer-events-none"
										:style="{ width: sb.fillPx + 'px' }"
									></div>
								</template>
							</div>
							<div
								v-for="sb in summaryBars"
								:key="'late-' + sb.group.key"
								v-show="sb.hasBar && sb.lateStartX !== null"
								:style="{
									position: 'absolute',
									top: sb.rowY + SUMMARY_PAD_Y + 'px',
									left: sb.lateStartX + 'px',
									width: sb.lateWidth + 'px',
									height: SUMMARY_BAR_HEIGHT + 'px',
								}"
								class="bg-warning-500/60 border border-warning-700 rounded-sm pointer-events-none"
							></div>
							<template v-for="sb in summaryBars" :key="'tick-' + sb.group.key">
								<div
									v-if="sb.hasBar && sb.plannedTickX !== null"
									:style="{
										position: 'absolute',
										top: sb.rowY + 'px',
										left: sb.plannedTickX - 1 + 'px',
										width: '2px',
										height: ROW_HEIGHT + 'px',
									}"
									class="bg-ink-900 pointer-events-none"
								></div>
							</template>

							<!-- Arrows -->
							<svg
								:width="timelineWidth"
								:height="timelineHeight"
								class="absolute top-0 left-0 pointer-events-none"
							>
								<defs>
									<marker
										id="arrowhead-grey"
										viewBox="0 0 10 10"
										refX="9"
										refY="5"
										markerWidth="6"
										markerHeight="6"
										orient="auto-start-reverse"
									>
										<path d="M 0 0 L 10 5 L 0 10 z" fill="#737373" />
									</marker>
									<marker
										id="arrowhead-red"
										viewBox="0 0 10 10"
										refX="9"
										refY="5"
										markerWidth="6"
										markerHeight="6"
										orient="auto-start-reverse"
									>
										<path d="M 0 0 L 10 5 L 0 10 z" fill="#DC2626" />
									</marker>
								</defs>
								<g v-for="arrow in arrows" :key="arrow.dep.id">
									<path
										:d="arrow.path"
										fill="none"
										:stroke="arrow.isViolated ? '#DC2626' : '#737373'"
										stroke-width="1.5"
										:marker-end="
											arrow.isViolated
												? 'url(#arrowhead-red)'
												: 'url(#arrowhead-grey)'
										"
										class="pointer-events-none"
									/>
								</g>
							</svg>

							<!-- Activity / Inspection bars -->
							<div
								v-for="b in bars.filter((x) => !x.undated && !x.isMilestone)"
								:key="'bar-' + b.task.id"
								:data-bar-task-id="b.task.id"
								:style="{
									position: 'absolute',
									top: b.y + 'px',
									left: b.x + 'px',
									width: b.width + 'px',
									height: BAR_HEIGHT + 'px',
								}"
								:class="[
									'rounded flex items-center text-[10px] text-ink-900 px-1 group select-none transition-shadow hover:shadow-md relative',
									barClass(b.task),
									b.isInspection ? 'border border-dashed' : 'border',
									b.isOverdue && !b.task.schedule_conflict
										? 'ring-1 ring-warning-500 ring-offset-1'
										: '',
									'cursor-default',
								]"
								:title="
									b.task.schedule_conflict
										? b.task.name + ' — ' + b.task.conflict_reason
										: b.task.name +
										  ' · ' +
										  fmtShort(b.task.startDate) +
										  ' → ' +
										  fmtShort(b.task.endDate) +
										  ' · ' +
										  b.task.progress +
										  '%' +
										  (b.isOverdue ? ' · OVERDUE' : '') +
										  (b.isInspection ? ' · Inspection' : '')
								"
							>
								<div
									v-if="b.task.progress > 0"
									:class="[
										'absolute top-0 bottom-0 left-0 rounded-l pointer-events-none',
										barFillClass(b.task),
									]"
									:style="{ width: Math.min(100, b.task.progress) + '%' }"
								></div>
								<span
									v-if="b.width > 60"
									class="relative truncate flex-1 font-medium z-[5] gantt-bar-label"
								>
									{{ b.task.name }}
								</span>
								<span
									v-else-if="b.width > 24"
									class="relative truncate z-[5] gantt-bar-label"
									>{{ b.task.progress }}%</span
								>
								<span
									v-if="b.isOverdue && !b.task.schedule_conflict && b.width > 18"
									class="relative ml-auto text-[11px] leading-none text-white z-[5]"
									title="Overdue"
									>⏱</span
								>
							</div>

							<!-- Milestone diamonds -->
							<div
								v-for="b in bars.filter((x) => !x.undated && x.isMilestone)"
								:key="'ms-' + b.task.id"
								:data-bar-task-id="b.task.id"
								:style="{
									position: 'absolute',
									top: b.rowY + 'px',
									left: b.x - DIAMOND_W / 2 + 'px',
									height: ROW_HEIGHT + 'px',
									pointerEvents: 'none',
								}"
								class="group select-none flex items-center"
								:title="
									b.task.schedule_conflict
										? b.task.name + ' — ' + b.task.conflict_reason
										: b.task.name +
										  ' · Milestone · ' +
										  fmtShort(b.task.endDate) +
										  (b.isOverdue ? ' · OVERDUE' : '')
								"
							>
								<svg :width="DIAMOND_W" :height="ROW_HEIGHT" class="flex-shrink-0">
									<polygon
										:points="`${DIAMOND_W / 2},${(ROW_HEIGHT - 14) / 2} ${
											DIAMOND_W - 1
										},${ROW_HEIGHT / 2} ${DIAMOND_W / 2},${
											(ROW_HEIGHT + 14) / 2
										} 1,${ROW_HEIGHT / 2}`"
										:fill="
											b.task.progress === 100 ||
											b.task.status === 'Completed'
												? '#16A34A'
												: b.task.schedule_conflict
												? '#DC2626'
												: diamondBaseFill
										"
										:stroke="
											b.task.schedule_conflict
												? '#7F1D1D'
												: b.isOverdue
												? '#D97706'
												: diamondBaseStroke
										"
										:stroke-width="
											b.task.schedule_conflict || b.isOverdue ? '2' : '1'
										"
										:class="'cursor-default'"
										style="pointer-events: auto"
									/>
								</svg>
								<span
									class="ml-1 truncate text-[10px] font-medium max-w-[140px]"
									:class="
										b.isOverdue && !b.task.schedule_conflict
											? 'text-warning-700'
											: diamondTextClass
									"
									style="pointer-events: none"
									>{{ b.task.name
									}}<span
										v-if="b.isOverdue && !b.task.schedule_conflict"
										class="ml-1"
										>⏱</span
									></span
								>
							</div>

							<!-- Today marker -->
							<div
								v-if="todayX > 0 && todayX < timelineWidth"
								class="absolute top-0 bottom-0 w-px bg-danger-500/60 pointer-events-none z-10"
								:style="{ left: todayX + 'px' }"
							></div>

							<!-- S164 — project boundary band: soft in-bounds tint + dashed start/end markers -->
							<template v-if="projectBand">
								<div
									class="absolute pointer-events-none"
									:style="{
										left: Math.max(0, projectBand.startX) + 'px',
										width:
											Math.max(
												0,
												Math.min(timelineWidth, projectBand.endX) -
													Math.max(0, projectBand.startX)
											) + 'px',
										top: '0px',
										bottom: '0px',
										background: 'rgba(34, 197, 94, 0.04)',
										zIndex: 1,
									}"
								></div>
								<div
									class="absolute pointer-events-none"
									:style="{
										left: projectBand.startX + 'px',
										top: '0px',
										bottom: '0px',
										width: '0',
										borderLeft: '2px dashed rgba(22, 163, 74, 0.7)',
										zIndex: 3,
									}"
								></div>
								<div
									class="absolute pointer-events-none"
									:style="{
										left: projectBand.endX + 'px',
										top: '0px',
										bottom: '0px',
										width: '0',
										borderLeft: '2px dashed rgba(22, 163, 74, 0.7)',
										zIndex: 3,
									}"
								></div>
							</template>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Legend -->
		<div
			class="mt-3 px-3 py-2 bg-white border border-ink-200 rounded-lg space-y-1.5 text-xs text-ink-600"
		>
			<div class="flex items-center gap-4 flex-wrap">
				<span class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
					>Type</span
				>
				<div class="flex items-center gap-1.5">
					<span class="inline-block w-5 h-2.5 rounded bg-brand-500"></span
					><span>Activity</span>
				</div>
				<div class="flex items-center gap-1.5">
					<svg width="14" height="14" viewBox="0 0 14 14">
						<polygon
							points="7,1 13,7 7,13 1,7"
							:fill="diamondBaseFill"
							:stroke="diamondBaseStroke"
						/>
					</svg>
					<span>Milestone</span>
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-info-500"
						style="border: 1.5px dashed #1e293b"
					></span
					><span>Inspection</span>
				</div>
			</div>
			<div class="flex items-center gap-4 flex-wrap">
				<span class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
					>Status</span
				>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-success-100 border border-success-700 relative overflow-hidden"
						><span
							class="absolute inset-y-0 left-0 w-full bg-success-600"
						></span></span
					>Completed
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-brand-100 border border-brand-700 relative overflow-hidden"
						><span class="absolute inset-y-0 left-0 w-3/5 bg-brand-600"></span></span
					>In Progress
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-ink-100 border border-ink-400"
					></span
					>Yet To Start
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-warning-100 border border-warning-700 relative overflow-hidden"
						><span class="absolute inset-y-0 left-0 w-2/5 bg-warning-600"></span></span
					>In Delay
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-ink-200 border border-ink-600"
					></span
					>Blocked
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-danger-100 border border-danger-700 relative overflow-hidden"
						><span class="absolute inset-y-0 left-0 w-3/5 bg-danger-600"></span></span
					>Schedule conflict
				</div>
				<div class="flex items-center gap-1.5">
					<span
						class="inline-block w-5 h-2.5 rounded bg-brand-100 border border-brand-700 ring-2 ring-warning-500 ring-offset-1 relative overflow-hidden"
						><span class="absolute inset-y-0 left-0 w-3/5 bg-brand-600"></span></span
					>Overdue <span class="text-ink-500">⏱</span>
				</div>
				<div class="ml-auto flex items-center gap-1.5">
					<span class="w-px h-3 bg-danger-500/60"></span>Today
				</div>
			</div>
		</div>

		<!-- Error toast -->
		<Teleport to="body">
			<div
				v-if="errorMsg"
				class="fixed bottom-6 right-6 bg-danger-50 border border-danger-200 text-danger-700 text-sm px-3 py-2 rounded-lg shadow-fp-lg z-[70] max-w-md"
			>
				{{ errorMsg }}
			</div>
		</Teleport>

		<!-- New-task modal -->
		<TaskFormModal
			v-model:open="newTaskOpen"
			:project-id="selectedProject"
			@created="onTaskCreated"
		/>
	</div>
</template>

<style>
.schedule-date-input {
	font-size: 10px;
	line-height: 1.2;
	padding: 1px 3px;
	border: 1px solid #e5e5e5;
	border-radius: 3px;
	background: #fff;
	color: #404040;
	max-width: 108px;
}
.schedule-date-input:disabled {
	background: #fafafa;
	color: #a3a3a3;
}
/* S163 — bars are LIGHT-track + SATURATED-fill; the label is text-ink-900
   (near-black light / near-white dark). A same-mode halo lifts it off the
   fill in either theme. */
.gantt-bar-label {
	text-shadow: 0 0 3px rgba(255, 255, 255, 0.85), 0 1px 1px rgba(255, 255, 255, 0.55);
}
html.dark .gantt-bar-label {
	text-shadow: 0 0 3px rgba(0, 0, 0, 0.65), 0 1px 1px rgba(0, 0, 0, 0.45);
}
</style>
