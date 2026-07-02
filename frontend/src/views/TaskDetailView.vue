<script setup>
import { usePageTitle } from "@/composables/usePageTitle";
import { endBeforeStartError, outOfParentBoundsError } from "@/utils/dateBounds";
import { fetchProjectBounds } from "@/utils/projectBounds";
// Task Detail. Edit + Delete + quick-status actions live on the title row
// (DeskPage #actions slot). Editing opens a modal so the inline content
// stays readable. Progress block is pinned to the top so the headline number
// is the first thing visible.

import { ref, reactive, computed, watch, nextTick } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { parseFrappeError, isPermissionDenied } from "@/utils/frappeError";
import AccessDenied from "@/components/AccessDenied.vue";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import { useTaskTypes } from "@/composables/useTaskTypes";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { createDataAdapter } from "@/data/adapters";
import {
	getTaskDependencies,
	addTaskPredecessor,
	removeTaskPredecessor,
} from "@/utils/scheduleApi";
import { setTaskAssignee, getTaskAssignee } from "@/data/taskAssignmentApi";
import FileUploadHandler from "frappe-ui-file-upload-handler";
import { fmtDate } from "@/utils/format";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const props = defineProps({ id: String });
const router = useRouter();
const store = useDataStore();
const adapter = createDataAdapter(store);
const { canEdit, canDelete, canCreate, canEditRecord, canDeleteRecord } = usePermissions();
const { taskTypes } = useTaskTypes();

// Assignee is Frappe-native assignment (`_assign`, a JSON list of users). The
// UI is single-assignee, so we surface the first entry.
function parseAssignee(raw) {
	try {
		const list = JSON.parse(raw || "[]");
		return Array.isArray(list) && list.length ? list[0] : "";
	} catch {
		return "";
	}
}

function firstResourceRow(resource) {
	if (resource?.doc) return resource.doc;
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw[0] || null;
	if (Array.isArray(raw?.value)) return raw.value[0] || null;
	if (raw && typeof raw === "object" && "value" in raw) return raw.value || null;
	return raw || null;
}

function resourceRows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

const taskResource = ref(null);
const accessDenied = computed(() => isPermissionDenied(taskResource.value?.error));

function loadTaskResource() {
	if (!props.id) {
		taskResource.value = null;
		return;
	}

	taskResource.value = adapter.read("Task", props.id, {
		nameField: "name",
		fields: [
			"name",
			"subject",
			"project",
			"work_package",
			"task_status",
			"priority",
			"progress",
			"owner",
			"exp_start_date",
			"exp_end_date",
			"type",
			"description",
		],
		cache: `buildsuite-task-detail:${props.id}`,
		transform(rows) {
			return rows.map((row) => ({
				id: row?.name || "",
				name: row?.subject || row?.name || "",
				projectId: row?.project || "",
				workPackageId: row?.work_package || "",
				status: row?.task_status || "Yet To Start",
				priority: row?.priority || "Medium",
				progress: Number(row?.progress) || 0,
				assignee: parseAssignee(row?._assign),
				owner: row?.owner || "",
				startDate: row?.exp_start_date || null,
				endDate: row?.exp_end_date || null,
				task_type: row?.type || "Activity",
				description: row?.description || "",
			}));
		},
	});
}

watch(() => props.id, loadTaskResource, { immediate: true });

const task = computed(() => {
	const backendTask = firstResourceRow(taskResource.value);
	if (backendTask) return backendTask;
	return store.taskById(props.id) || null;
});

// ===== Dependencies — Connections-style cards (prototype S135). Predecessors are
// stored on Task.depends_on; successors are inferred (reverse query). + Add opens
// the modal in pred / succ direction; per-row edit (type + lag) / delete. =====
const deps = ref({ predecessors: [], successors: [] });

async function loadDeps() {
	if (!props.id) {
		deps.value = { predecessors: [], successors: [] };
		return;
	}
	try {
		deps.value = await getTaskDependencies(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load dependencies", "error");
	}
}
watch(() => props.id, loadDeps, { immediate: true });

// Assignee lives in Frappe's native `_assign`, which frappe.client.get (the
// detail read path) does NOT return — so fetch it separately and keep it in
// sync. This is the source of truth for the read display and the edit form.
const currentAssignee = ref("");
async function loadAssignee() {
	if (!props.id) {
		currentAssignee.value = "";
		return;
	}
	try {
		currentAssignee.value = (await getTaskAssignee(props.id)) || "";
	} catch {
		currentAssignee.value = "";
	}
}
watch(() => props.id, loadAssignee, { immediate: true });

const canEditDeps = computed(() => canEditRecord("task", task.value));

function lagLabel(d) {
	const n = Number(d) || 0;
	return n === 0 ? "" : n > 0 ? `+${n}d` : `${n}d`;
}
function depTypeTitle(t) {
	return t === "FS" ? "Finish to Start" : t === "SS" ? "Start to Start" : "Finish to Finish";
}

// Add/edit modal. role: 'pred' (other task is the predecessor of this one) or
// 'succ' (other task is the successor — i.e. this task is ITS predecessor).
const depModalOpen = ref(false);
const depSaving = ref(false);
const depForm = reactive({
	mode: "add-pred",
	role: "pred",
	otherTaskId: "",
	otherSubject: "",
	dependency_type: "FS",
	lag: 0,
	error: "",
});

function openAddPredecessor() {
	Object.assign(depForm, {
		mode: "add-pred",
		role: "pred",
		otherTaskId: "",
		otherSubject: "",
		dependency_type: "FS",
		lag: 0,
		error: "",
	});
	depModalOpen.value = true;
}
function openAddSuccessor() {
	Object.assign(depForm, {
		mode: "add-succ",
		role: "succ",
		otherTaskId: "",
		otherSubject: "",
		dependency_type: "FS",
		lag: 0,
		error: "",
	});
	depModalOpen.value = true;
}
function openEditDep(dep, role) {
	Object.assign(depForm, {
		mode: "edit",
		role,
		otherTaskId: dep.task,
		otherSubject: dep.subject || dep.task,
		dependency_type: dep.dependency_type || "FS",
		lag: Number(dep.lag_days) || 0,
		error: "",
	});
	depModalOpen.value = true;
}
async function saveDep() {
	depForm.error = "";
	if (!depForm.otherTaskId) {
		depForm.error = "Pick a task.";
		return;
	}
	depSaving.value = true;
	try {
		// pred: this depends on other -> edge other -> this  => add_task_predecessor(this, other)
		// succ: other depends on this  -> edge this -> other  => add_task_predecessor(other, this)
		if (depForm.role === "pred") {
			await addTaskPredecessor(
				props.id,
				depForm.otherTaskId,
				depForm.dependency_type,
				Number(depForm.lag) || 0
			);
		} else {
			await addTaskPredecessor(
				depForm.otherTaskId,
				props.id,
				depForm.dependency_type,
				Number(depForm.lag) || 0
			);
		}
		await loadDeps();
		depModalOpen.value = false;
		showToast("Dependency saved");
	} catch (err) {
		depForm.error = err.message || "Failed to save dependency";
	} finally {
		depSaving.value = false;
	}
}
async function deleteDep(dep, role) {
	try {
		if (role === "pred") await removeTaskPredecessor(props.id, dep.task);
		else await removeTaskPredecessor(dep.task, props.id);
		await loadDeps();
		showToast("Dependency removed");
	} catch (err) {
		showToast(err.message || "Failed to remove dependency", "error");
	}
}

const depPickerFilters = computed(() =>
	task.value?.projectId
		? [
				["project", "=", task.value.projectId],
				["name", "!=", props.id],
		  ]
		: [["name", "!=", props.id]]
);

const projectResource = ref(null);

function loadProjectResource(projectId) {
	if (!projectId) {
		projectResource.value = null;
		return;
	}

	projectResource.value = adapter.read("Project", projectId, {
		fields: ["name", "project_name"],
		transform(rows) {
			return rows.map((row) => ({
				id: row?.name || "",
				name: row?.project_name || row?.name || "",
			}));
		},
	});
}

watch(() => task.value?.projectId, loadProjectResource, { immediate: true });

const project = computed(() => firstResourceRow(projectResource.value));

const wpResource = ref(null);

function loadWpResource(workPackageId) {
	if (!workPackageId) {
		wpResource.value = null;
		return;
	}

	wpResource.value = adapter.read("Work Package", workPackageId, {
		fields: ["name", "work_package_name"],
		transform(rows) {
			return rows.map((row) => ({
				id: row?.name || "",
				name: row?.work_package_name || row?.name || "",
			}));
		},
	});
}

watch(() => task.value?.workPackageId, loadWpResource, { immediate: true });

const wp = computed(() => firstResourceRow(wpResource.value));

const entriesResource = adapter.list("Task Progress Entry", {
	fields: [
		"name",
		"task",
		"entry_date",
		"cumulative_progress",
		"narrative",
		"skilled",
		"unskilled",
		"weather",
		"blocker",
		"blocker_detail",
		"owner",
	],
	filters: [["task", "=", props.id]],
	orderBy: "entry_date desc",
	transform(rows) {
		return rows.map((row) => ({
			id: row?.name || "",
			task: row?.task || "",
			entryDate: row?.entry_date || null,
			progressPct: Number(row?.cumulative_progress) || 0,
			narrative: row?.narrative || "",
			skilledLabour: Number(row?.skilled) || 0,
			unskilledLabour: Number(row?.unskilled) || 0,
			weather: row?.weather || "",
			blockerFlag: !!row?.blocker,
			blockerNote: row?.blocker_detail || "",
			enteredBy: row?.owner || "",
			owner: row?.owner || "",
		}));
	},
});
const entryRows = computed(() => resourceRows(entriesResource));
const recentEntries = computed(() => entryRows.value.slice(0, 3));
const entryCount = computed(() => entryRows.value.length);
const latestEntry = computed(() => entryRows.value[0] || null);

// ----- File Progress Entry modal -----------------------------------------
// Replaces the previous route-jump to /app/progress-entries/new. Keeps the
// user on the task home; saves via store.addTaskProgressEntry which fires
// the recompute hook so the page's progress card updates immediately.

const WEATHER_OPTIONS = ["Clear", "Rainy", "Hot", "Cold", "Storm"];
const filingProgress = ref(false);
const savingProgress = ref(false);
const progressForm = reactive({
	entryDate: "",
	enteredBy: "",
	progressPct: 0,
	narrative: "",
	skilledLabour: 0,
	unskilledLabour: 0,
	weather: "",
	blockerFlag: false,
	blockerNote: "",
});
// --- Edit modal error handling ---
const {
	errors: editErrors,
	applyServerErrors: applyEditErrors,
	setErrors: setEditErrors,
	clearError: clearEditError,
	reset: resetEditErrors,
} = useFormErrors({
	subject: "name",
	work_package: "workPackageId",
	task_status: "status",
	priority: "priority",
	type: "task_type",
	owner: "assignee",
	exp_start_date: "startDate",
	exp_end_date: "endDate",
});

// --- Progress entry modal error handling ---
const {
	errors: progressErrors,
	applyServerErrors: applyProgressErrors,
	setErrors: setProgressErrors,
	clearError: clearProgressError,
} = useFormErrors({
	cumulative_progress: "progressPct",
	entry_date: "entryDate",
	blocker_detail: "blockerNote",
});

// Pending attachments — files the user picked but haven't been persisted yet
// (the entry record doesn't exist until save). On save we mint the entry
// first, then dispatch store.addAttachment for each pending file with
// parentDoctype = 'Task Progress Entry' and the new entry's id.
const pendingAttachments = ref([]); // [{ fileName, mime, size, url }]
const progressFileInput = ref(null);
// Second input wired with `accept="image/*" capture="environment"` so on
// mobile it opens the rear camera directly (web Capture API). On desktop the
// browser falls back to a file picker filtered to images.
const progressCameraInput = ref(null);

function fmtBytes(n) {
	if (!n) return "0 B";
	if (n < 1024) return `${n} B`;
	if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
	return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function openProgressFilePicker() {
	if (progressFileInput.value) progressFileInput.value.click();
}
function openProgressCamera() {
	if (progressCameraInput.value) progressCameraInput.value.click();
}
function onProgressFilesPicked(ev) {
	const files = Array.from(ev.target.files || []);
	for (const f of files) {
		// Camera capture on iOS sometimes gives an empty filename — synthesize
		// one keyed by timestamp so the row still reads sensibly.
		const fileName =
			f.name && f.name.trim()
				? f.name
				: `photo-${new Date().toISOString().replace(/[:.]/g, "-")}.jpg`;
		pendingAttachments.value.push({
			fileName,
			mime: f.type || "application/octet-stream",
			size: f.size,
			url: URL.createObjectURL(f), // local preview only
			file: f, // the real File — uploaded via Frappe on save
		});
	}
	// Reset the input so picking the same file twice in a row still fires.
	if (ev.target) ev.target.value = "";
}
function removePendingAttachment(idx) {
	const att = pendingAttachments.value[idx];
	if (att?.url) {
		try {
			URL.revokeObjectURL(att.url);
		} catch (_) {
			/* tolerate non-blob */
		}
	}
	pendingAttachments.value.splice(idx, 1);
}
function clearPendingAttachments() {
	for (const a of pendingAttachments.value) {
		if (a?.url) {
			try {
				URL.revokeObjectURL(a.url);
			} catch (_) {
				/* tolerate non-blob */
			}
		}
	}
	pendingAttachments.value = [];
}

function resetProgressForm() {
	progressForm.entryDate = new Date().toISOString().slice(0, 10);
	progressForm.enteredBy = store.user?.id || store.team[0]?.id || "";
	progressForm.progressPct = task.value?.progress ?? 0;
	progressForm.narrative = "";
	progressForm.skilledLabour = 0;
	progressForm.unskilledLabour = 0;
	progressForm.weather = "";
	progressForm.blockerFlag = false;
	progressForm.blockerNote = "";
	setProgressErrors({});
	clearPendingAttachments();
}

function fileProgressEntry() {
	if (!task.value) return;
	resetProgressForm();
	filingProgress.value = true;
}
function cancelProgressEntry() {
	clearPendingAttachments();
	filingProgress.value = false;
}
function validateProgressEntry() {
	const e = {};
	const pct = Number(progressForm.progressPct);
	const floor = Number(task.value?.progress) || 0;
	if (Number.isNaN(pct) || pct > 100) {
		e.progressPct = "Progress must be between 0 and 100";
	} else if (pct <= 0) {
		e.progressPct = "A progress entry can't be 0% — record the progress actually made.";
	} else if (pct <= floor) {
		// Progress is cumulative + strictly increasing — it must exceed the current value.
		e.progressPct = `Progress must increase — enter a value above the current ${floor}%. Entries are cumulative.`;
	}
	if (progressForm.blockerFlag && !progressForm.blockerNote.trim()) {
		e.blockerNote = "Describe the blocker";
	}
	setProgressErrors(e);
	return Object.keys(e).length === 0;
}
async function saveProgressEntry() {
	if (!validateProgressEntry()) return;
	savingProgress.value = true;
	try {
		const entry = await adapter.create("Task Progress Entry", {
			task: props.id,
			entry_date: progressForm.entryDate,
			cumulative_progress: progressForm.progressPct,
			narrative: progressForm.narrative,
			skilled: progressForm.skilledLabour,
			unskilled: progressForm.unskilledLabour,
			weather: progressForm.weather,
			blocker: progressForm.blockerFlag ? 1 : 0,
			blocker_detail: progressForm.blockerNote,
		});

		// Upload any pending attachments against the new entry via Frappe's
		// native File pipeline (creates File docs attached_to the TPE). A failed
		// upload is reported per-file but doesn't unwind the already-filed entry.
		for (const f of pendingAttachments.value) {
			if (!f.file) continue;
			try {
				await new FileUploadHandler().upload(f.file, {
					doctype: "Task Progress Entry",
					docname: entry.name,
					private: true,
				});
			} catch (uploadErr) {
				showToast(`Filed entry, but failed to attach ${f.fileName}`, "error");
				console.error("attachment upload failed:", uploadErr);
			}
		}
		// Clear local ref WITHOUT revoking blob URLs
		pendingAttachments.value = [];
		filingProgress.value = false;

		// Refresh task and entries list
		await Promise.all([taskResource.value?.reload?.(), entriesResource.fetch()]);
		showToast("Progress entry filed");
	} catch (err) {
		const summary = applyProgressErrors(err);
		showToast(summary ?? "Failed to file progress entry", "error");
		console.error("saveProgressEntry failed:", err);
	} finally {
		savingProgress.value = false;
	}
}

// Edit modal state. `editing` controls visibility; `form` is the working copy
// that gets reset on cancel so the store record isn't touched mid-edit.
const editing = ref(false);
const form = ref({});

// Normalize task fields for the edit modal so native date inputs receive a
// browser-compatible YYYY-MM-DD value instead of a full datetime string.
function toDateInputValue(value) {
	if (!value) return "";
	if (typeof value === "string") return value.slice(0, 10);

	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return "";
	return date.toISOString().slice(0, 10);
}

function buildEditForm(source) {
	if (!source) return {};

	return {
		...source,
		assignee: currentAssignee.value, // `_assign` isn't on the doc read; use the fetched value
		startDate: toDateInputValue(source.startDate),
		endDate: toDateInputValue(source.endDate),
	};
}

// Rebuild the form when the task loads OR the (async) assignee resolves.
watch(
	[task, currentAssignee],
	() => {
		if (task.value && !editing.value) form.value = buildEditForm(task.value);
	},
	{ immediate: true }
);

function startEdit() {
	if (!task.value) return;
	form.value = buildEditForm(task.value);
	resetEditErrors();
	editing.value = true;
}
async function saveEdit() {
	const endErr = endBeforeStartError(form.value.startDate, form.value.endDate);
	const b = await fetchProjectBounds(task.value?.projectId);
	const boundsErr =
		endErr ||
		outOfParentBoundsError(
			form.value.startDate,
			form.value.endDate,
			b.start,
			b.end,
			"project"
		);
	if (boundsErr) {
		setEditErrors(
			boundsErr.startsWith("Start") ? { startDate: boundsErr } : { endDate: boundsErr }
		);
		showToast(boundsErr, "error");
		return;
	}
	try {
		await adapter.update("Task", props.id, {
			subject: form.value.name,
			work_package: form.value.workPackageId || null,
			task_status: form.value.status,
			priority: form.value.priority,
			type: form.value.task_type,
			exp_start_date: form.value.startDate,
			exp_end_date: form.value.endDate,
			description: form.value.description,
		});
		// Assignee is Frappe-native `_assign` — reassign only when it changed.
		if ((form.value.assignee || "") !== (currentAssignee.value || "")) {
			await setTaskAssignee(props.id, form.value.assignee);
			await loadAssignee();
		}
		editing.value = false;
		taskResource.value?.reload?.();
		showToast("Task updated");
	} catch (err) {
		showToast(applyEditErrors(err) ?? "Failed to save task", "error");
	}
}
function cancelEdit() {
	form.value = buildEditForm(task.value);
	resetEditErrors();
	editing.value = false;
}

async function quickStatus(status) {
	const patch = { task_status: status };
	if (status === "Completed") patch.progress = 100;
	if (status === "Yet To Start") patch.progress = 0;

	try {
		await adapter.update("Task", props.id, patch);
		taskResource.value?.reload?.();
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to update task status", "error");
	}
}

const showDeleteConfirm = ref(false);
const deleteLoading = ref(false);

function deleteTask() {
	showDeleteConfirm.value = true;
}

async function confirmDelete() {
	deleteLoading.value = true;
	try {
		await adapter.remove("Task", props.id);
		showDeleteConfirm.value = false;
		await router.push("/tasks");
		await nextTick();
		showToast("Task deleted");
	} catch (err) {
		showToast("Failed to delete task", "error");
		console.error("confirmDelete failed:", err);
	} finally {
		deleteLoading.value = false;
	}
}

const breadcrumbs = computed(() => {
	const out = [
		{ label: "BuildSuite Core", to: "/" },
		{ label: "Task", to: "/tasks" },
	];
	if (project.value)
		out.push({ label: project.value.name, to: `/projects/${project.value.id}` });
	return out;
});

// Title-strip badges. task_type sits alongside status + priority.
const titleStatuses = computed(() => {
	if (!task.value) return [];
	const out = [task.value.status, task.value.priority];
	if (task.value.task_type) out.push(task.value.task_type);
	return out;
});

const progressColor = computed(() => {
	if (!task.value) return "bg-ink-300";
	if (task.value.progress === 100) return "bg-success-500";
	if (task.value.progress > 0) return "bg-brand-500";
	return "bg-ink-300";
});

usePageTitle(() => task.value?.name);
</script>

<template>
	<DeskPage
		v-if="task"
		:title="task.name"
		:subtitle="task.id"
		:breadcrumbs="breadcrumbs"
		:status="titleStatuses"
	>
		<!-- Edit / Delete / quick-status actions share the title row -->
		<template #actions>
			<button
				v-if="task.status === 'Yet To Start' && canEditRecord('task', task)"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="quickStatus('In Progress')"
			>
				Start
			</button>
			<button
				v-if="task.status !== 'Completed' && canEditRecord('task', task)"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50"
				style="border-radius: 6px; color: #15803d"
				@click="quickStatus('Completed')"
			>
				Mark complete
			</button>
			<button
				v-if="canEditRecord('task', task)"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<button
				v-if="canDeleteRecord('task', task)"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				:disabled="deleteLoading"
				@click="deleteTask"
			>
				Delete
			</button>
		</template>

		<!-- ===== Two-column body: progress + details on left, connections
         panel on right (S82 — progress block moved inside the left column). ===== -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
			<div class="lg:col-span-2 space-y-4">
				<!-- Progress block -->
				<section
					class="bg-white border border-ink-200 overflow-hidden"
					style="border-radius: 10px"
				>
					<header
						class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between"
					>
						<div class="flex items-center gap-2">
							<svg
								class="w-4 h-4 text-brand-700"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath('chart-bar')"
							/>
							<h3 class="text-sm font-semibold text-ink-900">Progress</h3>
						</div>
						<button
							v-if="
								canCreate('taskProgressEntry') &&
								task.progress < 100 &&
								task.status !== 'Completed'
							"
							type="button"
							data-test="file-progress-entry"
							class="desk-save-btn text-xs"
							@click="fileProgressEntry"
						>
							+ File Progress Entry
						</button>
					</header>
					<div class="p-5">
						<div class="flex items-center gap-4">
							<div
								class="flex-1 h-2.5 bg-ink-100 overflow-hidden"
								style="border-radius: 999px"
							>
								<div
									class="h-full transition-all"
									:class="progressColor"
									:style="{ width: `${task.progress}%` }"
								/>
							</div>
							<span
								class="text-2xl font-semibold text-ink-900 tabular-nums w-16 text-right"
								>{{ task.progress }}%</span
							>
						</div>
						<div class="text-[11px] text-ink-500 mt-3">
							<template v-if="latestEntry">
								Latest:
								<DeskLink :to="`/progress-entries/${latestEntry.id}`"
									>{{ latestEntry.progressPct }}% on
									{{ fmtDate(latestEntry.entryDate) }}</DeskLink
								>
								by <UserAvatar :user-id="latestEntry.enteredBy" size="xs" /> ·
								{{ entryCount }} {{ entryCount === 1 ? "entry" : "entries" }} total
							</template>
							<template v-else>
								No progress entries filed yet — progress derives from the latest
								entry.
							</template>
						</div>
					</div>
				</section>

				<DeskSection title="Details">
					<DeskField label="Name">
						<div class="text-sm text-ink-900 py-1">{{ task.name }}</div>
					</DeskField>
					<DeskField label="Task Type" hint="Drives workflow.">
						<div class="py-1">
							<StatusBadge :status="task.task_type || 'Activity'" />
						</div>
					</DeskField>
					<DeskField label="Description">
						<div class="text-sm text-ink-700 py-1 whitespace-pre-line">
							{{ task.description || "—" }}
						</div>
					</DeskField>
					<DeskField label="Start">
						<div class="text-sm text-ink-900 py-1">{{ fmtDate(task.startDate) }}</div>
					</DeskField>
					<DeskField label="Due">
						<div class="text-sm text-ink-900 py-1">{{ fmtDate(task.endDate) }}</div>
					</DeskField>
				</DeskSection>
			</div>

			<!-- Connections panel — related records on the right -->
			<aside class="lg:col-span-1 space-y-2">
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div
						class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
					>
						Project
					</div>
					<DeskLink
						v-if="project"
						:to="`/projects/${project.id}`"
						class="text-sm font-medium"
						>{{ project.name }}</DeskLink
					>
					<span v-else class="text-sm text-ink-500">—</span>
				</div>
				<div
					v-if="wp"
					class="bg-white border border-ink-200 px-3 py-2"
					style="border-radius: 6px"
				>
					<div
						class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
					>
						Work Package
					</div>
					<DeskLink :to="`/work-packages/${wp.id}`" class="text-sm font-medium">{{
						wp.name
					}}</DeskLink>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div
						class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
					>
						Assignee
					</div>
					<UserAvatar
						v-if="currentAssignee"
						:user-id="currentAssignee"
						:show-name="true"
					/>
					<span v-else class="text-sm text-ink-400">Unassigned</span>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div
						class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
					>
						Timeline
					</div>
					<div class="text-sm text-ink-700">
						{{ fmtDate(task.startDate) }} → {{ fmtDate(task.endDate) }}
					</div>
				</div>

				<!-- Dependencies — predecessors (stored) + successors (inferred). Per the prototype. -->
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="flex items-center justify-between mb-1.5">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Dependencies
						</div>
						<RouterLink
							to="/schedule"
							class="text-[10px] text-brand-700 hover:underline"
							>Open Gantt →</RouterLink
						>
					</div>

					<!-- Predecessors -->
					<div class="mb-2">
						<div
							class="flex items-center justify-between text-[10px] text-ink-500 mb-1"
						>
							<span>Predecessors ({{ deps.predecessors.length }})</span>
							<button
								v-if="canEditDeps"
								@click="openAddPredecessor"
								class="text-brand-700 hover:underline"
								title="Add a task this one depends on"
							>
								+ Add
							</button>
						</div>
						<ul v-if="deps.predecessors.length" class="space-y-1">
							<li
								v-for="dep in deps.predecessors"
								:key="dep.task"
								class="group flex items-center gap-1.5 text-xs"
							>
								<span
									class="text-[10px] font-mono px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded-full flex-shrink-0"
									:title="depTypeTitle(dep.dependency_type)"
									>{{ dep.dependency_type }}</span
								>
								<RouterLink
									:to="`/tasks/${dep.task}`"
									class="flex-1 min-w-0 truncate text-ink-900 hover:text-brand-700"
									>{{ dep.subject }}</RouterLink
								>
								<span
									v-if="lagLabel(dep.lag_days)"
									class="text-[10px] text-ink-500 tabular-nums flex-shrink-0"
									>{{ lagLabel(dep.lag_days) }}</span
								>
								<div
									v-if="canEditDeps"
									class="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 flex-shrink-0"
								>
									<button
										@click="openEditDep(dep, 'pred')"
										class="px-1 py-0.5 text-ink-500 hover:text-ink-900"
										title="Edit"
									>
										✎
									</button>
									<button
										@click="deleteDep(dep, 'pred')"
										class="px-1 py-0.5 text-danger-700 hover:bg-danger-50 rounded"
										title="Delete"
									>
										🗑
									</button>
								</div>
							</li>
						</ul>
						<div v-else class="text-[11px] text-ink-400 italic">None</div>
					</div>

					<!-- Successors (inferred) -->
					<div>
						<div
							class="flex items-center justify-between text-[10px] text-ink-500 mb-1"
						>
							<span>Successors ({{ deps.successors.length }})</span>
							<button
								v-if="canEditDeps"
								@click="openAddSuccessor"
								class="text-brand-700 hover:underline"
								title="Add a task that depends on this one"
							>
								+ Add
							</button>
						</div>
						<ul v-if="deps.successors.length" class="space-y-1">
							<li
								v-for="dep in deps.successors"
								:key="dep.task"
								class="group flex items-center gap-1.5 text-xs"
							>
								<span
									class="text-[10px] font-mono px-1.5 py-0.5 bg-ink-100 text-ink-700 rounded-full flex-shrink-0"
									:title="depTypeTitle(dep.dependency_type)"
									>{{ dep.dependency_type }}</span
								>
								<RouterLink
									:to="`/tasks/${dep.task}`"
									class="flex-1 min-w-0 truncate text-ink-900 hover:text-brand-700"
									>{{ dep.subject }}</RouterLink
								>
								<span
									v-if="lagLabel(dep.lag_days)"
									class="text-[10px] text-ink-500 tabular-nums flex-shrink-0"
									>{{ lagLabel(dep.lag_days) }}</span
								>
								<div
									v-if="canEditDeps"
									class="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 flex-shrink-0"
								>
									<button
										@click="openEditDep(dep, 'succ')"
										class="px-1 py-0.5 text-ink-500 hover:text-ink-900"
										title="Edit"
									>
										✎
									</button>
									<button
										@click="deleteDep(dep, 'succ')"
										class="px-1 py-0.5 text-danger-700 hover:bg-danger-50 rounded"
										title="Delete"
									>
										🗑
									</button>
								</div>
							</li>
						</ul>
						<div v-else class="text-[11px] text-ink-400 italic">None</div>
					</div>
				</div>
				<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
					<div class="flex items-center justify-between mb-1.5">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Recent entries
						</div>
						<DeskLink
							v-if="entryCount > 3"
							:to="{ path: '/progress-entries', query: { task: task.id } }"
							class="text-[10px]"
							>View all {{ entryCount }} →</DeskLink
						>
					</div>
					<ul v-if="recentEntries.length" class="space-y-1.5">
						<li
							v-for="e in recentEntries"
							:key="e.id"
							class="flex items-center justify-between gap-2 text-xs"
						>
							<DeskLink
								:to="`/progress-entries/${e.id}`"
								class="font-medium tabular-nums"
								>{{ e.progressPct }}%</DeskLink
							>
							<span class="text-ink-500 flex-1 truncate">{{
								fmtDate(e.entryDate)
							}}</span>
							<span
								v-if="e.blockerFlag"
								class="text-danger-700 flex-shrink-0"
								title="Blocker flagged"
								>🚩</span
							>
							<UserAvatar :user-id="e.enteredBy" size="xs" />
						</li>
					</ul>
					<div v-else class="text-xs text-ink-400 italic">None yet</div>
				</div>
			</aside>
		</div>

		<!-- ===== Edit modal — opens via the title-row Edit button ===== -->
		<Teleport to="body">
			<div
				v-if="editing"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="cancelEdit"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
					style="border-radius: 12px; max-height: calc(100vh - 3rem)"
					@click.stop
				>
					<!-- Modal header (pinned) -->
					<header
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white"
						style="border-radius: 12px 12px 0 0"
					>
						<div class="min-w-0 flex-1">
							<h2 class="text-sm font-semibold text-ink-900">Edit task</h2>
							<p class="text-[11px] text-ink-500 mt-0.5 truncate">{{ task.name }}</p>
						</div>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
							aria-label="Close"
							@click="cancelEdit"
						>
							×
						</button>
					</header>

					<!-- Modal body — the only scrolling region -->
					<div class="p-5 overflow-y-auto flex-1">
						<DeskSection title="Details">
							<DeskField label="Name" required :error="editErrors.name">
								<DeskInput v-model="form.name" @input="clearEditError('name')" />
							</DeskField>
							<DeskField
								label="Task Type"
								required
								hint="Activity = standard work with progress entries; Milestone = checkpoint with no qty progress; Inspection = pass/fail gate."
							>
								<DeskSelect
									v-model="form.task_type"
									@change="clearEditError('task_type')"
								>
									<option v-for="tt in taskTypes" :key="tt" :value="tt">
										{{ tt }}
									</option>
								</DeskSelect>
							</DeskField>
							<DeskField
								label="Work Package"
								hint="Optional — leave blank for a direct project task."
							>
								<DeskLinkPicker
									v-model="form.workPackageId"
									doctype="Work Package"
									label-field="work_package_name"
									value-field="name"
									:search-fields="['work_package_name', 'code', 'name']"
									:filters="
										task.projectId ? [['project', '=', task.projectId]] : []
									"
									:page-length="20"
									placeholder="— None · Direct project task —"
								/>
							</DeskField>
							<DeskField label="Description">
								<DeskTextarea v-model="form.description" :rows="4" />
							</DeskField>
							<DeskField label="Start" :error="editErrors.startDate">
								<DeskInput
									v-model="form.startDate"
									type="date"
									@change="clearEditError('startDate')"
								/>
							</DeskField>
							<DeskField label="Due" :error="editErrors.endDate">
								<DeskInput
									v-model="form.endDate"
									type="date"
									@change="clearEditError('endDate')"
								/>
							</DeskField>
						</DeskSection>

						<DeskSection title="Assignment & status">
							<DeskField label="Assignee" :error="editErrors.assignee">
								<DeskLinkPicker
									v-model="form.assignee"
									doctype="User"
									placeholder="Select assignee"
									label-field="full_name"
									value-field="name"
									:search-fields="['full_name', 'name', 'email']"
									:filters="[['enabled', '=', 1]]"
									order-by="full_name asc"
									:page-length="20"
									@change="clearEditError('assignee')"
								/>
							</DeskField>
							<DeskField label="Status" :error="editErrors.status">
								<DeskSelect
									v-model="form.status"
									@change="clearEditError('status')"
								>
									<option>Yet To Start</option>
									<option>In Progress</option>
									<option>In Delay</option>
									<option>Completed</option>
									<option>Blocked</option>
								</DeskSelect>
							</DeskField>
							<DeskField label="Priority" :error="editErrors.priority">
								<DeskSelect
									v-model="form.priority"
									@change="clearEditError('priority')"
								>
									<option>Low</option>
									<option>Medium</option>
									<option>High</option>
								</DeskSelect>
							</DeskField>
						</DeskSection>
					</div>

					<!-- Modal footer (pinned) -->
					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white"
						style="border-radius: 0 0 12px 12px"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							@click="cancelEdit"
						>
							Cancel
						</button>
						<button type="button" class="desk-save-btn" @click="saveEdit">Save</button>
					</footer>
				</div>
			</div>
		</Teleport>

		<!-- ===== File Progress Entry modal — opens via the "+ File Progress
         Entry" button in the Progress card header. Saves via
         store.addTaskProgressEntry which fires the recompute hook so the
         task home's Progress card updates immediately. ===== -->
		<Teleport to="body">
			<div
				v-if="filingProgress"
				data-test="tpe-modal"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="cancelProgressEntry"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
					style="border-radius: 12px; max-height: calc(100vh - 3rem)"
					@click.stop
				>
					<!-- Modal header (pinned) -->
					<header
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white"
						style="border-radius: 12px 12px 0 0"
					>
						<div class="min-w-0 flex-1">
							<h2 class="text-sm font-semibold text-ink-900">File progress entry</h2>
							<p class="text-[11px] text-ink-500 mt-0.5 truncate">
								{{ task.name }} · currently {{ task.progress }}% ·
								{{ task.status }}
							</p>
						</div>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none flex-shrink-0 ml-3"
							aria-label="Close"
							@click="cancelProgressEntry"
						>
							×
						</button>
					</header>

					<!-- Modal body — the only scrolling region -->
					<div class="p-5 overflow-y-auto flex-1">
						<DeskSection title="Progress" :cols="2">
							<DeskField
								label="Cumulative progress (%)"
								required
								:hint="`The NEW cumulative % after this entry — not a delta. Can't go below the current ${
									task.progress || 0
								}%.`"
								:error="progressErrors.progressPct"
							>
								<DeskInput
									v-model="progressForm.progressPct"
									data-test="field-progress"
									type="number"
									:min="task.progress || 0"
									max="100"
									step="1"
									@input="clearProgressError('progressPct')"
								/>
							</DeskField>
							<DeskField label="Entry date" :error="progressErrors.entryDate">
								<DeskInput
									v-model="progressForm.entryDate"
									type="date"
									@change="clearProgressError('entryDate')"
								/>
							</DeskField>
							<DeskField
								label="Entered by"
								hint="Stamped automatically from the signed-in user."
							>
								<div class="flex items-center gap-2 py-1">
									<UserAvatar :user-id="progressForm.enteredBy" size="xs" />
									<span class="text-sm text-ink-800">{{
										store.teamMember(progressForm.enteredBy)?.name || "—"
									}}</span>
									<span
										v-if="store.teamMember(progressForm.enteredBy)?.role"
										class="text-[11px] text-ink-500"
										>·
										{{ store.teamMember(progressForm.enteredBy).role }}</span
									>
								</div>
							</DeskField>
							<div class="md:col-span-2">
								<DeskField
									label="Narrative"
									hint="What was completed today? Any context worth recording?"
								>
									<DeskTextarea
										v-model="progressForm.narrative"
										:rows="3"
										placeholder="e.g. Bays 3-4 complete; 285 of 380 m² done. Cube test taken."
									/>
								</DeskField>
							</div>
						</DeskSection>

						<DeskSection title="Labour deployed today" :cols="2">
							<DeskField
								label="Skilled labour"
								hint="Count of skilled workers on site today"
							>
								<DeskInput v-model="progressForm.skilledLabour" type="number" />
							</DeskField>
							<DeskField
								label="Unskilled labour"
								hint="Count of unskilled workers / helpers"
							>
								<DeskInput v-model="progressForm.unskilledLabour" type="number" />
							</DeskField>
						</DeskSection>

						<DeskSection title="Site conditions" :cols="2">
							<DeskField
								label="Weather"
								hint="Optional — only if it's worth recording."
							>
								<DeskSelect v-model="progressForm.weather">
									<option value="">— No record —</option>
									<option v-for="w in WEATHER_OPTIONS" :key="w" :value="w">
										{{ w }}
									</option>
								</DeskSelect>
							</DeskField>
							<DeskField label="Blocker">
								<label
									class="flex items-center gap-2 py-1 text-sm text-ink-700 cursor-pointer"
								>
									<input
										v-model="progressForm.blockerFlag"
										type="checkbox"
										class="h-3.5 w-3.5"
									/>
									Flag a blocker on this entry
								</label>
							</DeskField>
							<div v-if="progressForm.blockerFlag" class="md:col-span-2">
								<DeskField
									label="Blocker detail"
									required
									hint="What blocked progress today?"
									:error="progressErrors.blockerNote"
								>
									<DeskTextarea
										v-model="progressForm.blockerNote"
										:rows="2"
										placeholder="e.g. Afternoon shower delayed final bay by 2 hours"
										@input="clearProgressError('blockerNote')"
									/>
								</DeskField>
							</div>
						</DeskSection>

						<DeskSection title="Attachments" :cols="1">
							<input
								ref="progressFileInput"
								type="file"
								multiple
								class="hidden"
								@change="onProgressFilesPicked"
							/>
							<input
								ref="progressCameraInput"
								type="file"
								accept="image/*"
								capture="environment"
								class="hidden"
								@change="onProgressFilesPicked"
							/>
							<DeskField
								label="Files"
								hint="Site photos, QC reports, drawings — picked here and saved with the entry."
							>
								<div class="space-y-2 py-1">
									<ul v-if="pendingAttachments.length" class="space-y-1.5">
										<li
											v-for="(att, idx) in pendingAttachments"
											:key="idx"
											class="flex items-center gap-2 px-2.5 py-1.5 bg-ink-50 border border-ink-200 text-xs"
											style="border-radius: 6px"
										>
											<img
												v-if="att.mime?.startsWith('image/') && att.url"
												:src="att.url"
												class="w-8 h-8 object-cover flex-shrink-0"
												style="border-radius: 4px"
												alt=""
											/>
											<svg
												v-else
												class="w-4 h-4 text-ink-500"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.8"
												stroke-linecap="round"
												stroke-linejoin="round"
												aria-hidden="true"
												v-html="getWorkspaceIconPath('paperclip')"
											/>
											<span class="flex-1 min-w-0 truncate text-ink-800">{{
												att.fileName
											}}</span>
											<span class="text-[11px] text-ink-500 tabular-nums">{{
												fmtBytes(att.size)
											}}</span>
											<button
												type="button"
												class="text-ink-400 hover:text-danger-700 text-base leading-none"
												aria-label="Remove"
												@click="removePendingAttachment(idx)"
											>
												×
											</button>
										</li>
									</ul>
									<div class="flex items-center gap-2 flex-wrap">
										<button
											type="button"
											class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 inline-flex items-center gap-1"
											style="border-radius: 6px"
											@click="openProgressFilePicker"
										>
											<span class="text-sm leading-none">+</span>
											<span
												>Attach file{{
													pendingAttachments.length ? "s" : ""
												}}</span
											>
										</button>
										<button
											type="button"
											class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 inline-flex items-center gap-1.5"
											style="border-radius: 6px"
											@click="openProgressCamera"
										>
											<svg
												class="w-3.5 h-3.5"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="1.8"
												stroke-linecap="round"
												stroke-linejoin="round"
												aria-hidden="true"
												v-html="getWorkspaceIconPath('camera')"
											/>
											<span>Capture photo</span>
										</button>
									</div>
								</div>
							</DeskField>
						</DeskSection>
					</div>

					<!-- Modal footer (pinned) -->
					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white"
						style="border-radius: 0 0 12px 12px"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							@click="cancelProgressEntry"
						>
							Cancel
						</button>
						<button
							type="button"
							data-test="save-btn"
							class="desk-save-btn"
							:disabled="savingProgress"
							@click="saveProgressEntry"
						>
							{{ savingProgress ? "Filing…" : "File entry" }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>

		<ConfirmDialog
			v-model:open="showDeleteConfirm"
			title="Delete task"
			:message="`Delete '${task?.name}'? This cannot be undone.`"
			confirm-label="Delete"
			:destructive="true"
			:loading="deleteLoading"
			@confirm="confirmDelete"
		/>

		<!-- Add / edit dependency modal -->
		<Teleport to="body">
			<div
				v-if="depModalOpen"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="depModalOpen = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-md shadow-fp-lg"
					style="border-radius: 12px"
					@click.stop
				>
					<header
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between"
					>
						<h2 class="text-sm font-semibold text-ink-900">
							{{
								depForm.mode === "edit"
									? "Edit dependency"
									: depForm.mode === "add-pred"
									? "Add predecessor"
									: "Add successor"
							}}
						</h2>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none"
							aria-label="Close"
							@click="depModalOpen = false"
						>
							×
						</button>
					</header>
					<div class="p-5 space-y-3">
						<DeskField
							:label="
								depForm.role === 'pred' ? 'Predecessor task' : 'Successor task'
							"
							:hint="
								depForm.role === 'pred'
									? 'Must finish/start before this task.'
									: 'Waits on this task.'
							"
						>
							<div v-if="depForm.mode === 'edit'" class="text-sm text-ink-900 py-1">
								{{ depForm.otherSubject }}
							</div>
							<DeskLinkPicker
								v-else
								v-model="depForm.otherTaskId"
								doctype="Task"
								label-field="subject"
								value-field="name"
								:search-fields="['subject', 'name']"
								:filters="depPickerFilters"
								placeholder="Pick a task"
							/>
						</DeskField>
						<div class="grid grid-cols-2 gap-3">
							<DeskField label="Type" hint="FS / SS / FF">
								<DeskSelect v-model="depForm.dependency_type">
									<option>FS</option>
									<option>SS</option>
									<option>FF</option>
								</DeskSelect>
							</DeskField>
							<DeskField label="Lag (days)" hint="− = lead / overlap">
								<DeskInput v-model="depForm.lag" type="number" />
							</DeskField>
						</div>
						<p v-if="depForm.error" class="text-xs text-danger-700">
							{{ depForm.error }}
						</p>
					</div>
					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							@click="depModalOpen = false"
						>
							Cancel
						</button>
						<button
							type="button"
							class="desk-save-btn"
							:disabled="depSaving"
							@click="saveDep"
						>
							{{ depSaving ? "Saving…" : "Save" }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>

	<AccessDenied
		v-else-if="accessDenied"
		title="You don't have access to this task"
		back-to="/tasks"
		back-label="Back to Tasks"
	/>

	<div v-else class="px-6 py-20 text-center text-sm text-ink-400">Task not found</div>
</template>
