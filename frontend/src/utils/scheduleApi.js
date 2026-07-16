// Thin wrappers over the buildsuite_core.api.schedule.* whitelisted methods.
// Used by the Task Detail "Dependencies" section and (later) the Gantt. Reads are
// GET; mutations are POST with the CSRF token. Throws Error(<server message>) so
// callers can surface the cycle-guard message etc.

const BASE = "/api/method/buildsuite_core.api.schedule.";
const ENGINE_BASE = "/api/method/buildsuite_core.api.schedule_engine.";

function serverMessage(payload, status) {
	// Frappe puts thrown messages in _server_messages: a JSON array of JSON strings.
	try {
		const sm = payload?._server_messages;
		if (sm) {
			const first = JSON.parse(JSON.parse(sm)[0]);
			if (first?.message) return first.message;
		}
	} catch (_) {
		/* fall through to generic */
	}
	return payload?.exception || `Request failed (${status})`;
}

async function request(method, { params, body, base = BASE } = {}) {
	const qs = params ? "?" + new URLSearchParams(params).toString() : "";
	const res = await fetch(base + method + qs, {
		method: body ? "POST" : "GET",
		credentials: "include",
		headers: {
			Accept: "application/json",
			...(body
				? {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": window.csrf_token || "",
					}
				: {}),
		},
		...(body ? { body: JSON.stringify(body) } : {}),
	});
	const payload = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(payload, res.status));
	return payload.message;
}

export const getProjectSchedule = (project) =>
	request("get_project_schedule", { params: { project } });

export const getTaskDependencies = (task) =>
	request("get_task_dependencies", { params: { task } });

export const addTaskPredecessor = (task, predecessor, dependency_type = "FS", lag_days = 0) =>
	request("add_task_predecessor", { body: { task, predecessor, dependency_type, lag_days } });

export const removeTaskPredecessor = (task, predecessor) =>
	request("remove_task_predecessor", { body: { task, predecessor } });

// Preview (dryRun=1) or commit (dryRun=0) a duration-preserving downstream cascade
// after moving `task` to newStart/newEnd. Returns { moves: [...] }. The client engine
// computes the same preview instantly; this is the authoritative commit.
export const rescheduleDownstream = (task, newStart = null, newEnd = null, dryRun = 1) =>
	request("reschedule_downstream", {
		base: ENGINE_BASE,
		body: { task, new_start: newStart, new_end: newEnd, dry_run: dryRun },
	});

// --- schedule snapshots: undo + revisions --------------------------------
const SNAPSHOT_BASE = "/api/method/buildsuite_core.api.schedule_snapshot.";

// Pop + restore the newest auto-captured Undo snapshot (walks the stack back).
export const undoLast = (project) =>
	request("undo_last", { base: SNAPSHOT_BASE, body: { project } });

// Snapshots for a project; pass kind ("Undo" | "Revision") to filter.
export const listSnapshots = (project, kind = null) =>
	request("list_snapshots", {
		base: SNAPSHOT_BASE,
		params: kind ? { project, kind } : { project },
	});

// Save the current schedule as a named Revision restore point.
export const saveRevision = (project, label) =>
	request("save_revision", { base: SNAPSHOT_BASE, body: { project, label } });

// Restore a snapshot by name (captures an Undo first unless captureUndo=0).
export const restoreSnapshot = (name, captureUndo = 1) =>
	request("restore_snapshot", {
		base: SNAPSHOT_BASE,
		body: { name, capture_undo: captureUndo },
	});

export const deleteSnapshot = (name) =>
	request("delete_snapshot", { base: SNAPSHOT_BASE, body: { name } });
