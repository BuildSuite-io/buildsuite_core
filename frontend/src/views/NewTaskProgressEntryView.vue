<script setup>
import { reactive, ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import FileUploadHandler from "frappe-ui-file-upload-handler";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const router = useRouter();
const route = useRoute();
const store = useDataStore();
const { canCreate } = usePermissions();
const adapter = createDataAdapter(store);

const cameFromTaskId = route.query.taskId || null;

const form = reactive({
	projectId: "",
	taskId: cameFromTaskId || "",
	entryDate: new Date().toISOString().slice(0, 10),
	progressPct: 0,
	narrative: "",
	skilledLabour: 0,
	unskilledLabour: 0,
	weather: "",
	blockerFlag: false,
	blockerNote: "",
});
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
	task: "taskId",
	entry_date: "entryDate",
	cumulative_progress: "progressPct",
	blocker_detail: "blockerNote",
});
const saving = ref(false);

// ----- Attachments -------------------------------------------------------
// Matches the "File progress" modal (opened from a Task): files are picked here
// and held locally until save, then uploaded against the new entry via Frappe's
// native File pipeline (File docs attached_to the Task Progress Entry).
const pendingAttachments = ref([]); // [{ fileName, mime, size, url, file }]
const progressFileInput = ref(null);
// Second input wired with `accept="image/*" capture="environment"` so on mobile
// it opens the rear camera directly; on desktop it falls back to an image picker.
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
		// Camera capture on iOS sometimes gives an empty filename — synthesize one.
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

// Project → its whole sub-tree (self + every nested sub-project). The Task picker
// below is scoped with a `project in [...]` filter, so you can only pick a task
// that belongs to the chosen project or one of its sub-projects.
const allProjectsRes = useDocTypeList("Project", {
	fields: ["name", "parent_project"],
	pageLength: 5000,
	cache: "buildsuite-tpe-project-tree",
});
const projectScope = computed(() => {
	const pid = form.projectId;
	if (!pid) return [];
	const byParent = {};
	for (const p of allProjectsRes.data || []) {
		const parent = p.parent_project;
		if (!byParent[parent]) byParent[parent] = [];
		byParent[parent].push(p.name);
	}
	const out = [];
	const stack = [pid];
	while (stack.length) {
		const cur = stack.pop();
		out.push(cur);
		for (const c of byParent[cur] || []) stack.push(c);
	}
	return out;
});
const taskFilters = computed(() =>
	projectScope.value.length ? [["project", "in", projectScope.value]] : []
);
function onProjectChange() {
	// A task from the previously-selected project no longer applies.
	form.taskId = "";
}

// Load the selected task to show the info banner and pre-fill progress.
const taskResource = ref(null);

function loadTaskResource(taskId) {
	if (!taskId) {
		taskResource.value = null;
		return;
	}
	taskResource.value = adapter.read("Task", taskId, {
		nameField: "name",
		fields: ["name", "subject", "status", "progress", "project"],
		transform(rows) {
			return rows.map((row) => ({
				id: row?.name || "",
				name: row?.subject || row?.name || "",
				status: row?.status || "",
				progress: Number(row?.progress) || 0,
				project: row?.project || "",
			}));
		},
	});
}

watch(() => form.taskId, loadTaskResource, { immediate: true });

// Extract the first row from whatever shape the adapter returns — a list
// resource (`.data` array / `{ value: [...] }`) or a document resource (`.doc`).
// Mirrors TaskDetailView's firstResourceRow so progress resolves reliably.
function firstResourceRow(resource) {
	if (resource?.doc) return resource.doc;
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw[0] || null;
	if (Array.isArray(raw?.value)) return raw.value[0] || null;
	if (raw && typeof raw === "object" && "value" in raw) return raw.value || null;
	return raw || null;
}

const selectedTask = computed(() => {
	const row = firstResourceRow(taskResource.value);
	if (!row) return null;
	// Normalise here (not via the adapter transform, which only runs for the
	// list-shaped `.data` path — a `.doc` resource bypasses it).
	return {
		id: row.id || row.name || "",
		name: row.subject || row.name || "",
		status: row.status || "",
		progress: Number(row.progress) || 0,
		project: row.project || "",
	};
});

// When arriving from a task (route ?taskId=), back-fill the Project picker from
// that task so the picker + the task scope stay consistent.
watch(
	() => selectedTask.value?.project,
	(proj) => {
		if (proj && !form.projectId) form.projectId = proj;
	}
);

// The task's current cumulative progress is the monotonic floor — a new entry
// can never go below it.
const progressFloor = computed(() => Number(selectedTask.value?.progress) || 0);

// Default the entry to the task's current cumulative progress whenever the
// selected task resolves or changes. Mirrors TaskDetailView's openProgress().
watch(
	() => selectedTask.value?.id,
	() => {
		form.progressPct = progressFloor.value;
	}
);

// Live validation — surface the monotonic error the moment the value drops
// below the floor (or out of range), instead of waiting for submit.
watch(
	() => [form.progressPct, progressFloor.value],
	() => {
		const raw = form.progressPct;
		if (raw === "" || raw === null) {
			clearError("progressPct");
			return;
		}
		const pct = Number(raw);
		if (Number.isNaN(pct) || pct > 100) {
			errors.value = { ...errors.value, progressPct: "Progress must be between 0 and 100" };
		} else if (pct <= 0) {
			errors.value = {
				...errors.value,
				progressPct: "A progress entry can't be 0% — record the progress actually made.",
			};
		} else if (pct <= progressFloor.value) {
			errors.value = {
				...errors.value,
				progressPct: `Progress must increase — enter a value above the current ${progressFloor.value}%. Entries are cumulative.`,
			};
		} else {
			clearError("progressPct");
		}
	}
);

// Clamp to the floor on blur/commit so the field can't be left below the task's
// current progress (paste / typing can bypass the input's min attribute).
function clampProgress() {
	let pct = Number(form.progressPct);
	if (Number.isNaN(pct)) pct = progressFloor.value;
	form.progressPct = Math.min(100, Math.max(progressFloor.value, pct));
}

function validate() {
	const e = {};
	if (!form.projectId) e.projectId = "Project is required";
	if (!form.taskId) e.taskId = "Task is required";
	else if (selectedTask.value && Number(selectedTask.value.progress) >= 100)
		e.taskId = "This task is already Completed — no further progress entries can be added.";
	const pct = Number(form.progressPct);
	if (Number.isNaN(pct) || pct > 100) {
		e.progressPct = "Progress must be between 0 and 100";
	} else if (pct <= 0) {
		e.progressPct = "A progress entry can't be 0% — record the progress actually made.";
	} else if (pct <= progressFloor.value) {
		e.progressPct = `Progress must increase — enter a value above the current ${progressFloor.value}%. Entries are cumulative.`;
	}
	if (form.blockerFlag && !form.blockerNote.trim()) {
		e.blockerNote = "Describe the blocker";
	}
	setErrors(e);
	return Object.keys(e).length === 0;
}

async function save() {
	if (!validate()) return;
	saving.value = true;
	try {
		const created = await adapter.create("Task Progress Entry", {
			task: form.taskId,
			entry_date: form.entryDate,
			cumulative_progress: Number(form.progressPct),
			narrative: form.narrative,
			skilled: Number(form.skilledLabour) || 0,
			unskilled: Number(form.unskilledLabour) || 0,
			weather: form.weather,
			blocker: form.blockerFlag ? 1 : 0,
			blocker_detail: form.blockerNote,
		});

		// Upload any pending attachments against the new entry via Frappe's native
		// File pipeline. A failed upload is reported per-file but doesn't unwind the
		// already-filed entry.
		for (const f of pendingAttachments.value) {
			if (!f.file) continue;
			try {
				await new FileUploadHandler().upload(f.file, {
					doctype: "Task Progress Entry",
					docname: created.name || created.id,
					private: true,
				});
			} catch (uploadErr) {
				showToast(`Filed entry, but failed to attach ${f.fileName}`, "error");
				console.error("attachment upload failed:", uploadErr);
			}
		}
		pendingAttachments.value = []; // clear ref without revoking blob URLs

		if (cameFromTaskId) {
			router.push(`/tasks/${cameFromTaskId}`);
		} else {
			router.push(`/progress-entries/${created.name || created.id}`);
		}
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to file progress entry", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.back();
}

const WEATHER_OPTIONS = ["Clear", "Rainy", "Hot", "Cold", "Storm"];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Task Progress Entry", to: "/progress-entries" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage
		title="New Progress Entry"
		subtitle="File today's progress against a task — labour, weather, blockers"
		:breadcrumbs="breadcrumbs"
	>
		<div
			v-if="!canCreate('taskProgressEntry')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to file a progress entry.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Filing…' : 'File entry'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Project, task &amp; date" :cols="2">
					<DeskField label="Project" required :error="errors.projectId">
						<DeskLinkPicker
							v-model="form.projectId"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							:search-fields="['project_name', 'custom_project_id', 'name']"
							:page-length="20"
							placeholder="— Select project —"
							@change="onProjectChange"
						/>
					</DeskField>
					<DeskField label="Task" required :error="errors.taskId">
						<DeskLinkPicker
							v-model="form.taskId"
							doctype="Task"
							label-field="subject"
							value-field="name"
							:search-fields="['subject', 'name']"
							:filters="taskFilters"
							:disabled="!form.projectId"
							:page-length="20"
							:placeholder="
								form.projectId ? '— Select task —' : '— Select a project first —'
							"
						/>
					</DeskField>
					<DeskField label="Entry date">
						<DeskInput v-model="form.entryDate" type="date" />
					</DeskField>
					<div
						v-if="selectedTask"
						class="md:col-span-2 text-xs text-ink-500 bg-ink-50 border border-ink-200 px-3 py-2"
						style="border-radius: 2px"
					>
						Selected task
						<strong class="text-ink-800">{{ selectedTask.name }}</strong> is currently
						at
						<strong class="text-ink-800 tabular-nums"
							>{{ selectedTask.progress }}% · {{ selectedTask.status }}</strong
						>. The Cumulative progress % you enter below will become the task's new
						state on save.
					</div>
				</DeskSection>

				<DeskSection title="Progress" :cols="2">
					<DeskField
						label="Cumulative progress (%)"
						required
						:hint="`The NEW cumulative % after this entry — not a delta. Can't go below the current ${progressFloor}%.`"
						:error="errors.progressPct"
					>
						<DeskInput
							v-model="form.progressPct"
							type="number"
							:min="progressFloor"
							max="100"
							step="1"
							@change="clampProgress"
							@blur="clampProgress"
						/>
					</DeskField>
					<div class="md:col-span-2">
						<DeskField
							label="Narrative"
							hint="What was completed today? Any context worth recording?"
						>
							<DeskTextarea
								v-model="form.narrative"
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
						<DeskInput v-model="form.skilledLabour" type="number" />
					</DeskField>
					<DeskField
						label="Unskilled labour"
						hint="Count of unskilled workers / helpers"
					>
						<DeskInput v-model="form.unskilledLabour" type="number" />
					</DeskField>
				</DeskSection>

				<DeskSection title="Site conditions" :cols="2">
					<DeskField label="Weather" hint="Optional · only if it's worth recording">
						<DeskSelect v-model="form.weather">
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
								v-model="form.blockerFlag"
								type="checkbox"
								class="h-3.5 w-3.5"
							/>
							Flag a blocker on this entry
						</label>
					</DeskField>
					<div v-if="form.blockerFlag" class="md:col-span-2">
						<DeskField
							label="Blocker detail"
							required
							hint="What blocked progress today?"
							:error="errors.blockerNote"
						>
							<DeskTextarea
								v-model="form.blockerNote"
								:rows="2"
								placeholder="e.g. Afternoon shower delayed final bay by 2 hours"
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
		</DeskForm>
	</DeskPage>
</template>
