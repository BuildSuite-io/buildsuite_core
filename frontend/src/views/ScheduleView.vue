<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import TaskFormModal from "@/components/TaskFormModal.vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { usePermissions } from "@/composables/usePermissions";
import {
	getProjectSchedule,
	addTaskPredecessor,
	removeTaskPredecessor,
	rescheduleDownstream,
} from "@/utils/scheduleApi";
import { dateBoundsError } from "@/utils/dateBounds";
import { parseFrappeError } from "@/utils/frappeError";
import { computeAllConflicts, hasCycle, computeCascade } from "@/composables/useScheduleEngine";

const store = useDataStore();
const adapter = createDataAdapter(store);
const { canCreate, canEditRecord } = usePermissions();
const route = useRoute();
const router = useRouter();

// === State ============================================================
const selectedProject = ref(route.query.project || "");
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
const draggedDep = ref(null);
const popoverDep = ref(null);
const draggedBar = ref(null);
const previewState = ref(null);
const undatedHover = ref(null);

const timelineRef = ref(null);
const containerRef = ref(null);

// === Time scale =======================================================
const PX_PER_DAY = { day: 36, week: 12, month: 4, quarter: 2 };
const pxPerDay = computed(() => PX_PER_DAY[viewMode.value]);
const STRIDE_DAYS = { day: 1, week: 7, month: 30, quarter: 90 };
const strideDays = computed(() => STRIDE_DAYS[viewMode.value]);
const strideWidth = computed(() => strideDays.value * pxPerDay.value);

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
function addDays(iso, days) {
	if (!iso) return iso;
	const d = parseISO(iso);
	d.setDate(d.getDate() + Number(days || 0));
	return msToISO(d.getTime());
}
function xToISO(x) {
	if (!dateRange.value) return null;
	const days = Math.round(x / pxPerDay.value);
	return msToISO(dateRange.value.minMs + days * 86400000);
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
		recomputeLocalConflicts();
	} catch (err) {
		flashError(parseFrappeError(err).summary || "Failed to load the schedule.");
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
// Keep the selected project in the URL (?project=) so the schedule is bookmarkable
// and the browser back button restores the last project after visiting a task.
watch(selectedProject, (val) => {
	if ((route.query.project || "") !== (val || "")) {
		router.push({ query: { ...route.query, project: val || undefined } });
	}
});
watch(
	() => route.query.project,
	(val) => {
		if ((val || "") !== (selectedProject.value || "")) selectedProject.value = val || "";
	}
);
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
	// In Delay uses .gantt-in-delay-track (same rgba(245,158,11,0.48) in light
	// and dark mode) + the saturated -600 progress fill on top.
	if (task.status === "In Delay") return "gantt-in-delay-track border-warning-700";
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
		if (!undated && draggedBar.value && draggedBar.value.taskId === t.id) {
			const dx = draggedBar.value.deltaDays * pxPerDay.value;
			if (draggedBar.value.mode === "move") {
				bx += dx;
			} else if (!isMilestone && draggedBar.value.mode === "resize-start") {
				const right = bx + bw;
				bx = Math.min(bx + dx, right - 2);
				bw = right - bx;
			} else if (!isMilestone && draggedBar.value.mode === "resize-end") {
				bw = Math.max(2, bw + dx);
			}
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
	const boundsErr = dateBoundsError({
		start: newStart,
		end: newEnd,
		parentStart: projectMeta.value?.startDate,
		parentEnd: projectMeta.value?.endDate,
		parentLabel: "project",
	});
	if (boundsErr) {
		flashError(boundsErr);
		allTasks.value = [...allTasks.value]; // re-render to reset the rejected input
		return;
	}
	await commitDates(task, newStart, newEnd, {
		startDate: task.startDate,
		endDate: task.endDate,
	});
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
// === Bar drag (move / resize) =========================================
function onBarMouseDown(task, e, mode) {
	if (e.button !== 0) return;
	if (e.target.dataset?.linkArrow) return;
	if (!canEditTask(task) && mode !== "move") return;
	e.preventDefault();
	e.stopPropagation();
	draggedBar.value = {
		taskId: task.id,
		mode,
		startClientX: e.clientX,
		originalStart: task.startDate,
		originalEnd: task.endDate,
		deltaDays: 0,
		canEdit: canEditTask(task),
	};
	window.addEventListener("mousemove", onBarMouseMove);
	window.addEventListener("mouseup", onBarMouseUp);
}
function onBarMouseMove(e) {
	if (!draggedBar.value) return;
	draggedBar.value.deltaDays = Math.round(
		(e.clientX - draggedBar.value.startClientX) / pxPerDay.value
	);
}
function onBarMouseUp() {
	window.removeEventListener("mousemove", onBarMouseMove);
	window.removeEventListener("mouseup", onBarMouseUp);
	const drag = draggedBar.value;
	draggedBar.value = null;
	if (!drag || drag.deltaDays === 0 || !drag.canEdit) return;
	applyBarDrop(drag);
}
async function applyBarDrop(drag) {
	const task = allTasks.value.find((t) => t.id === drag.taskId);
	if (!task) return;
	const isMs = task.task_type === "Milestone";
	let newStart = drag.originalStart;
	let newEnd = drag.originalEnd;
	if (drag.mode === "move") {
		if (isMs) {
			newStart = "";
			newEnd = addDays(drag.originalEnd, drag.deltaDays);
		} else {
			newStart = addDays(drag.originalStart, drag.deltaDays);
			newEnd = addDays(drag.originalEnd, drag.deltaDays);
		}
	} else if (drag.mode === "resize-start") {
		if (isMs) return;
		newStart = addDays(drag.originalStart, drag.deltaDays);
		if (diffDays(newStart, drag.originalEnd) < 0) newStart = drag.originalEnd;
	} else if (drag.mode === "resize-end") {
		if (isMs) return;
		newEnd = addDays(drag.originalEnd, drag.deltaDays);
		if (diffDays(drag.originalStart, newEnd) < 0) newEnd = drag.originalStart;
	}
	await commitDates(task, newStart, newEnd, {
		startDate: drag.originalStart,
		endDate: drag.originalEnd,
	});
}

// Optimistically move the task (instant), preview the cascade (client), persist the
// root (server flags downstream), then open the cascade modal if anything shifts.
async function commitDates(task, newStart, newEnd, before) {
	const isMs = task.task_type === "Milestone";
	task.startDate = isMs ? "" : newStart;
	task.endDate = newEnd;
	recomputeLocalConflicts();
	const { byId, edges } = engineInputs();
	const moves = computeCascade(task.id, byId, edges, { start: newStart, end: newEnd });
	try {
		await adapter.update("Task", task.id, {
			exp_start_date: isMs ? null : newStart || null,
			exp_end_date: newEnd || null,
		});
	} catch (err) {
		// Revert the optimistic change to this one task; no full reload.
		task.startDate = before?.startDate ?? task.startDate;
		task.endDate = before?.endDate ?? task.endDate;
		recomputeLocalConflicts();
		flashError(parseFrappeError(err).summary || "Could not reschedule.");
		return;
	}
	// A single-task move is already reflected locally (the client conflict engine
	// mirrors the server) — no reload. Only a downstream cascade reloads, and only
	// after the user confirms it.
	if (moves && moves.length > 0) {
		previewState.value = {
			rootTaskId: task.id,
			rootAfter: { startDate: newStart, endDate: newEnd },
			moves,
		};
	}
}

// === Cascade modal ====================================================
async function confirmCascade() {
	if (!previewState.value) return;
	const ps = previewState.value;
	previewState.value = null;
	try {
		await rescheduleDownstream(
			ps.rootTaskId,
			ps.rootAfter.startDate || null,
			ps.rootAfter.endDate || null,
			0
		);
	} catch (err) {
		flashError(parseFrappeError(err).summary || "Cascade failed.");
	}
	await loadSchedule();
}
async function cancelCascade() {
	previewState.value = null;
	await loadSchedule();
}
function taskName(id) {
	return (allTasks.value.find((t) => t.id === id) || {}).name || id;
}

// === Undated row hover-to-place =======================================
function onUndatedRowMouseMove(task, e) {
	if (!canEditTask(task) || !dateRange.value) return;
	const rect = timelineRef.value?.getBoundingClientRect();
	if (!rect) return;
	const innerX = e.clientX - rect.left + (timelineRef.value?.scrollLeft || 0);
	const blockIdx = Math.max(0, Math.floor(innerX / strideWidth.value));
	const ghostX = blockIdx * strideWidth.value;
	undatedHover.value = { taskId: task.id, ghostX, ghostStartISO: xToISO(ghostX) };
}
function onUndatedRowMouseLeave() {
	undatedHover.value = null;
}
async function onUndatedRowClick(task) {
	if (!undatedHover.value || undatedHover.value.taskId !== task.id || !canEditTask(task)) return;
	const start = undatedHover.value.ghostStartISO;
	const end = addDays(start, strideDays.value);
	undatedHover.value = null;
	await commitDates(task, start, end, { startDate: task.startDate, endDate: task.endDate });
}

// === Conflict engine (client mirror; server stores the authoritative flags) ===
function engineInputs() {
	const byId = {};
	for (const t of allTasks.value) {
		byId[t.id] = {
			name: t.id,
			type: t.task_type,
			start: t.startDate || null,
			end: t.endDate || null,
			status: t.status,
		};
	}
	const edges = allDeps.value.map((d) => ({
		predecessor: d.predecessor,
		successor: d.successor,
		type: d.dependency_type,
		lag: d.lag,
	}));
	return { byId, edges };
}
function recomputeLocalConflicts() {
	const { byId, edges } = engineInputs();
	const c = computeAllConflicts(byId, edges);
	for (const t of allTasks.value) {
		const r = c[t.id];
		t.schedule_conflict = !!r?.conflict;
		t.conflict_reason = r?.reason || "";
	}
	allTasks.value = [...allTasks.value];
}

// === Dependency creation drag (drag the handle from one bar onto another) ===
function onArrowHandleMouseDown(task, e) {
	if (!canEditTask(task) || e.button !== 0) return;
	e.preventDefault();
	e.stopPropagation();
	draggedDep.value = {
		fromTaskId: task.id,
		mouseX: e.clientX,
		mouseY: e.clientY,
		hoverTargetId: null,
	};
	window.addEventListener("mousemove", onDepDragMove);
	window.addEventListener("mouseup", onDepDragUp);
}
function hitTestTaskAt(clientX, clientY) {
	let node = document.elementFromPoint(clientX, clientY);
	while (node && !node.dataset?.barTaskId) node = node.parentElement;
	if (node?.dataset?.barTaskId) return node.dataset.barTaskId;
	const rect = timelineRef.value?.getBoundingClientRect();
	if (!rect) return null;
	const innerY = clientY - rect.top - HEADER_HEIGHT;
	if (innerY < 0) return null;
	const row = layoutRows.value[Math.floor(innerY / ROW_HEIGHT)];
	return row && row.kind === "task" ? row.task.id : null;
}
function onDepDragMove(e) {
	if (!draggedDep.value) return;
	draggedDep.value.mouseX = e.clientX;
	draggedDep.value.mouseY = e.clientY;
	draggedDep.value.hoverTargetId = hitTestTaskAt(e.clientX, e.clientY);
}
async function onDepDragUp(e) {
	window.removeEventListener("mousemove", onDepDragMove);
	window.removeEventListener("mouseup", onDepDragUp);
	const drag = draggedDep.value;
	draggedDep.value = null;
	if (!drag) return;
	const targetId = hitTestTaskAt(e.clientX, e.clientY) || drag.hoverTargetId;
	if (!targetId || targetId === drag.fromTaskId) return;
	const { edges } = engineInputs();
	if (hasCycle(drag.fromTaskId, targetId, edges)) {
		flashError("Creating this dependency would close a cycle.");
		return;
	}
	// Optimistic: draw the edge + reflag conflicts immediately, persist in background.
	const edge = {
		id: `${targetId}<-${drag.fromTaskId}`,
		predecessor: drag.fromTaskId,
		successor: targetId,
		dependency_type: "FS",
		lag: 0,
	};
	if (allDeps.value.some((d) => d.id === edge.id)) return;
	allDeps.value = [...allDeps.value, edge];
	recomputeLocalConflicts();
	try {
		await addTaskPredecessor(targetId, drag.fromTaskId, "FS", 0);
	} catch (err) {
		allDeps.value = allDeps.value.filter((d) => d.id !== edge.id);
		recomputeLocalConflicts();
		flashError(parseFrappeError(err).summary || "Could not create dependency.");
	}
}
const depGhost = computed(() => {
	if (!draggedDep.value) return null;
	const fromBar = barById.value.get(draggedDep.value.fromTaskId);
	if (!fromBar) return null;
	const rect = timelineRef.value?.getBoundingClientRect();
	const scrollLeft = timelineRef.value?.scrollLeft || 0;
	const innerX = rect ? draggedDep.value.mouseX - rect.left + scrollLeft : 0;
	const innerY = rect ? draggedDep.value.mouseY - rect.top - HEADER_HEIGHT : 0;
	return {
		x1: fromBar.x + fromBar.width,
		y1: fromBar.y + BAR_HEIGHT / 2,
		x2: innerX,
		y2: innerY,
	};
});

// === Dependency popover (click an arrow to edit type / lag / delete) ===
const POPOVER_W = 256;
const POPOVER_H = 280;
function onArrowClick(arrow, e) {
	e.stopPropagation();
	let x = Math.min(e.clientX, window.innerWidth - POPOVER_W - 12);
	let y = e.clientY + 12;
	if (y + POPOVER_H > window.innerHeight - 12) y = Math.max(12, e.clientY - POPOVER_H - 12);
	popoverDep.value = { dep: { ...arrow.dep }, x, y };
}
async function applyPopover() {
	if (!popoverDep.value) return;
	const d = popoverDep.value.dep;
	popoverDep.value = null;
	const idx = allDeps.value.findIndex((x) => x.id === d.id);
	const prev = idx >= 0 ? { ...allDeps.value[idx] } : null;
	if (idx >= 0) {
		allDeps.value[idx] = {
			...allDeps.value[idx],
			dependency_type: d.dependency_type,
			lag: Number(d.lag) || 0,
		};
		allDeps.value = [...allDeps.value];
		recomputeLocalConflicts();
	}
	try {
		await addTaskPredecessor(
			d.successor,
			d.predecessor,
			d.dependency_type,
			Number(d.lag) || 0
		);
	} catch (err) {
		if (prev && idx >= 0) {
			allDeps.value[idx] = prev;
			allDeps.value = [...allDeps.value];
			recomputeLocalConflicts();
		}
		flashError(parseFrappeError(err).summary || "Could not update dependency.");
	}
}
async function deleteFromPopover() {
	if (!popoverDep.value) return;
	const d = popoverDep.value.dep;
	popoverDep.value = null;
	const prev = allDeps.value;
	allDeps.value = allDeps.value.filter((x) => x.id !== d.id);
	recomputeLocalConflicts();
	try {
		await removeTaskPredecessor(d.successor, d.predecessor);
	} catch (err) {
		allDeps.value = prev;
		recomputeLocalConflicts();
		flashError(parseFrappeError(err).summary || "Could not delete dependency.");
	}
}

onBeforeUnmount(() => {
	if (errorTimer) clearTimeout(errorTimer);
	window.removeEventListener("mousemove", onBarMouseMove);
	window.removeEventListener("mouseup", onBarMouseUp);
	window.removeEventListener("mousemove", onDepDragMove);
	window.removeEventListener("mouseup", onDepDragUp);
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
										stroke="transparent"
										stroke-width="14"
										class="pointer-events-auto cursor-pointer hit-fat"
										@click="onArrowClick(arrow, $event)"
									/>
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

							<!-- Undated row hit-areas -->
							<div
								v-for="b in bars.filter((x) => x.undated)"
								:key="'undated-' + b.task.id"
								:style="{
									position: 'absolute',
									top: b.rowY + 'px',
									left: 0,
									width: timelineWidth + 'px',
									height: ROW_HEIGHT + 'px',
								}"
								:class="canEditTask(b.task) ? 'cursor-pointer' : 'cursor-default'"
								@mousemove="onUndatedRowMouseMove(b.task, $event)"
								@mouseleave="onUndatedRowMouseLeave"
								@click="onUndatedRowClick(b.task)"
							>
								<span
									v-if="!undatedHover || undatedHover.taskId !== b.task.id"
									class="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-ink-400 italic select-none pointer-events-none"
									>{{
										canEditTask(b.task)
											? "Hover and click to place a 1-" +
											  viewMode +
											  " block · drag the edges after to extend"
											: "No timeline set"
									}}</span
								>
								<div
									v-if="undatedHover && undatedHover.taskId === b.task.id"
									class="absolute border-2 border-dashed border-brand-700 bg-brand-500/50 rounded flex items-center text-[10px] text-white font-medium px-1 pointer-events-none"
									:style="{
										left: undatedHover.ghostX + 'px',
										top: ROW_PAD_Y + 'px',
										width: strideWidth + 'px',
										height: BAR_HEIGHT + 'px',
									}"
								>
									<span class="truncate"
										>+ {{ fmtShort(undatedHover.ghostStartISO) }}</span
									>
								</div>
							</div>
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
									b.isOverdue &&
									!b.task.schedule_conflict &&
									b.task.status !== 'In Delay'
										? 'ring-1 ring-warning-500 ring-offset-1'
										: '',
									canEditTask(b.task) ? 'cursor-move' : 'cursor-default',
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
								@mousedown="onBarMouseDown(b.task, $event, 'move')"
							>
								<div
									v-if="b.task.progress > 0"
									:class="[
										'absolute top-0 bottom-0 left-0 rounded-l pointer-events-none',
										barFillClass(b.task),
									]"
									:style="{ width: Math.min(100, b.task.progress) + '%' }"
								></div>
								<div
									v-if="canEditTask(b.task)"
									class="absolute left-0 top-0 bottom-0 w-2 cursor-w-resize hover:bg-white/30 z-10"
									@mousedown.stop="
										onBarMouseDown(b.task, $event, 'resize-start')
									"
								></div>
								<div
									v-if="canEditTask(b.task)"
									class="absolute right-0 top-0 bottom-0 w-2 cursor-e-resize hover:bg-white/30 z-10"
									@mousedown.stop="onBarMouseDown(b.task, $event, 'resize-end')"
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
									v-if="
										b.isOverdue &&
										!b.task.schedule_conflict &&
										b.task.status !== 'In Delay' &&
										b.width > 18
									"
									class="relative ml-auto text-[11px] leading-none text-white z-[5]"
									title="Overdue"
									>⏱</span
								>
								<div
									v-if="canEditTask(b.task)"
									data-link-arrow="true"
									class="absolute -right-4 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-white border-2 border-brand-700 cursor-crosshair opacity-50 group-hover:opacity-100 z-20 shadow transition-opacity"
									title="Drag to another task to create a Finish-to-Start dependency"
									@mousedown.stop="onArrowHandleMouseDown(b.task, $event)"
								></div>
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
										:class="
											canEditTask(b.task) ? 'cursor-move' : 'cursor-default'
										"
										style="pointer-events: auto"
										@mousedown="onBarMouseDown(b.task, $event, 'move')"
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
								<div
									v-if="canEditTask(b.task)"
									data-link-arrow="true"
									class="absolute w-4 h-4 rounded-full bg-white border-2 border-brand-700 cursor-crosshair opacity-50 group-hover:opacity-100 z-20 shadow transition-opacity"
									:style="{
										left: DIAMOND_W - 2 + 'px',
										top: (ROW_HEIGHT - 16) / 2 + 'px',
										pointerEvents: 'auto',
									}"
									title="Drag to another task to create a Finish-to-Start dependency"
									@mousedown.stop="onArrowHandleMouseDown(b.task, $event)"
								></div>
							</div>

							<!-- Ghost dependency arrow (drag-to-create preview) -->
							<svg
								v-if="depGhost"
								class="absolute top-0 left-0 pointer-events-none z-30"
								:width="timelineWidth"
								:height="timelineHeight"
							>
								<line
									:x1="depGhost.x1"
									:y1="depGhost.y1"
									:x2="depGhost.x2"
									:y2="depGhost.y2"
									stroke="#16A34A"
									stroke-width="2"
									stroke-dasharray="4 4"
								/>
							</svg>

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

		<!-- Dependency popover (edit type / lag / delete) -->
		<Teleport to="body">
			<div
				v-if="popoverDep"
				class="fixed bg-white border border-ink-200 rounded-lg shadow-fp-lg p-3 z-[65] w-64"
				:style="{ left: popoverDep.x + 'px', top: popoverDep.y + 'px' }"
				@click.stop
			>
				<div class="text-[11px] uppercase tracking-wider text-ink-500 mb-2 font-medium">
					Dependency
				</div>
				<div class="text-xs text-ink-700 mb-2 font-mono">
					{{ popoverDep.dep.predecessor }} → {{ popoverDep.dep.successor }}
				</div>
				<div class="flex items-center gap-2 mb-2">
					<label class="text-[11px] text-ink-500 w-12">Type</label>
					<select
						v-model="popoverDep.dep.dependency_type"
						:disabled="!canEditAny"
						class="text-xs px-2 py-1 border border-ink-200 rounded bg-white flex-1"
					>
						<option value="FS">FS — Finish to Start</option>
						<option value="SS">SS — Start to Start</option>
						<option value="FF">FF — Finish to Finish</option>
					</select>
				</div>
				<div class="flex items-center gap-2 mb-3">
					<label class="text-[11px] text-ink-500 w-12">Lag</label>
					<input
						type="number"
						v-model.number="popoverDep.dep.lag"
						:disabled="!canEditAny"
						class="text-xs px-2 py-1 border border-ink-200 rounded bg-white flex-1"
					/>
					<span class="text-[11px] text-ink-500">days</span>
				</div>
				<p class="text-[10px] text-ink-400 mb-3 italic">
					Negative lag = lead (overlap allowed).
				</p>
				<div class="flex items-center justify-between gap-2">
					<button
						v-if="canEditAny"
						class="text-xs px-2 py-1 text-danger-700 hover:bg-danger-50 rounded"
						@click="deleteFromPopover"
					>
						Delete
					</button>
					<div class="ml-auto flex items-center gap-2">
						<button
							class="text-xs px-2 py-1 border border-ink-200 rounded hover:bg-ink-50"
							@click="popoverDep = null"
						>
							Close
						</button>
						<button
							v-if="canEditAny"
							class="text-xs px-2.5 py-1 bg-ink-900 text-white rounded hover:bg-ink-800"
							@click="applyPopover"
						>
							Save
						</button>
					</div>
				</div>
			</div>
			<div v-if="popoverDep" class="fixed inset-0 z-[64]" @click="popoverDep = null"></div>
		</Teleport>

		<!-- Cascade preview modal -->
		<Teleport to="body">
			<div
				v-if="previewState"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
				@click="cancelCascade"
			>
				<div class="bg-white rounded-lg shadow-fp-lg max-w-xl w-full" @click.stop>
					<div
						class="px-5 py-3 border-b border-ink-100 bg-gradient-to-r from-warning-50 to-white rounded-t-lg flex items-center justify-between"
					>
						<div>
							<div class="text-sm font-semibold text-ink-900">
								Reschedule downstream?
							</div>
							<div class="text-[11px] text-ink-500 mt-0.5">
								{{ previewState.moves.length }} downstream task{{
									previewState.moves.length === 1 ? "" : "s"
								}}
								would shift forward
							</div>
						</div>
						<button
							class="text-ink-400 hover:text-ink-700 text-lg leading-none"
							@click="cancelCascade"
						>
							×
						</button>
					</div>
					<div class="px-5 py-4 max-h-[60vh] overflow-y-auto">
						<div
							class="grid gap-2 text-xs"
							style="grid-template-columns: minmax(140px, 1.4fr) 1fr 1fr"
						>
							<div class="text-[10px] uppercase tracking-wider text-ink-500">
								Task
							</div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500">
								From
							</div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500">To</div>
							<template v-for="m in previewState.moves" :key="m.task">
								<div class="text-ink-900 truncate" :title="taskName(m.task)">
									{{ taskName(m.task) }}
								</div>
								<div class="text-ink-700">
									{{ fmtShort(m.old_start || m.old_end) }} →
									{{ fmtShort(m.old_end) }}
								</div>
								<div class="text-brand-700 font-medium">
									{{ fmtShort(m.new_start || m.new_end) }} →
									{{ fmtShort(m.new_end) }}
								</div>
							</template>
						</div>
						<p class="text-[11px] text-ink-500 mt-4 italic">
							Cancel keeps your dragged task at its new dates but leaves dependents
							flagged for conflict — you can resolve them manually or reschedule
							again later.
						</p>
					</div>
					<div
						class="px-5 py-3 border-t border-ink-100 flex items-center justify-end gap-2 bg-ink-50/40 rounded-b-lg"
					>
						<button
							class="text-xs px-3 py-1.5 border border-ink-200 rounded hover:bg-white"
							@click="cancelCascade"
						>
							Cancel
						</button>
						<button
							class="text-xs px-3 py-1.5 bg-ink-900 text-white rounded hover:bg-ink-800"
							@click="confirmCascade"
						>
							Apply cascade
						</button>
					</div>
				</div>
			</div>
		</Teleport>

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
						class="inline-block w-5 h-2.5 rounded gantt-in-delay-track border border-warning-700 relative overflow-hidden"
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
.hit-fat:hover + path[stroke] {
	stroke: #15803d !important;
}
/* Inline date inputs in the left-pane row. Transparent track + color: inherit so
   the row's theme text shows through, and color-scheme flips on html.dark so the
   native date-picker chrome (text, dropdown) adapts to the active theme — otherwise
   the input renders as a white box in dark mode. Unscoped so html.dark works. */
.schedule-date-input {
	font-size: 10px;
	height: 18px;
	padding: 0 4px;
	border: 1px solid #e2e8f0;
	border-radius: 4px;
	background-color: transparent;
	color: inherit;
	color-scheme: light;
	width: 95px;
	flex-shrink: 0;
}
.schedule-date-input:focus {
	outline: none;
	border-color: #16a34a;
	box-shadow: 0 0 0 1px rgba(22, 163, 74, 0.2);
}
.schedule-date-input:disabled {
	opacity: 0.55;
	cursor: not-allowed;
}
html.dark .schedule-date-input {
	border-color: #333333;
	color-scheme: dark;
}
html.dark .schedule-date-input:focus {
	border-color: #4ade80;
	box-shadow: 0 0 0 1px rgba(74, 222, 128, 0.25);
}
/* S175 — In Delay track: the same amber wash in both light and dark mode
   (peach over white, muted amber over the dark canvas). The saturated
   warning-600 progress fill layers on top. */
.gantt-in-delay-track {
	background-color: rgba(245, 158, 11, 0.48);
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
