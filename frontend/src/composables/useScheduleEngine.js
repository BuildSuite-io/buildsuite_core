// Client mirror of the server-side scheduling engine
// (buildsuite_core/api/schedule_engine.py). PURE functions over plain task/edge
// objects so the two implementations stay in lock-step against the shared test
// vectors in tests/test_schedule_engine.py. The client runs these for instant
// Gantt feedback (conflict highlighting, cascade preview); the server is
// authoritative on commit.
//
// task: { name, type, start, end, status }  (start/end = "YYYY-MM-DD" or Date or null)
// edge: { predecessor, successor, type, lag }

const DAY_MS = 86400000;

function parseDate(d) {
	if (!d) return null;
	if (d instanceof Date) return d;
	const s = String(d).slice(0, 10);
	const x = new Date(s + "T00:00:00");
	return isNaN(x.getTime()) ? null : x;
}

export function addDays(d, n) {
	const p = parseDate(d);
	if (!p) return null;
	const x = new Date(p);
	x.setDate(x.getDate() + Number(n || 0));
	return x;
}

export function diffDays(from, to) {
	const a = parseDate(from);
	const b = parseDate(to);
	if (!a || !b) return 0;
	return Math.round((b - a) / DAY_MS);
}

export function iso(d) {
	const p = parseDate(d);
	if (!p) return null;
	const y = p.getFullYear();
	const m = String(p.getMonth() + 1).padStart(2, "0");
	const day = String(p.getDate()).padStart(2, "0");
	return `${y}-${m}-${day}`;
}

// --- pure graph algorithm (mirror schedule_engine.py) -------------------------

function earliestStartForEdge(pred, succ, dep, succDurationOverride = null) {
	if (!pred || !succ || !dep) return null;
	const lag = Number(dep.lag || 0);
	const type = dep.type;
	const predIsMs = pred.type === "Milestone";
	const succIsMs = succ.type === "Milestone";
	const succDur = succIsMs
		? 0
		: succDurationOverride != null
		? succDurationOverride
		: diffDays(succ.start, succ.end);

	if (type === "FS") {
		if (!pred.end) return null;
		return addDays(pred.end, lag);
	}
	if (type === "SS") {
		const anchor = predIsMs ? pred.end : pred.start;
		if (!anchor) return null;
		return addDays(anchor, lag);
	}
	if (type === "FF") {
		if (!pred.end) return null;
		const earliestSuccEnd = addDays(pred.end, lag);
		return addDays(earliestSuccEnd, -succDur);
	}
	return null;
}

export function computeEarliestStart(taskId, tasksById, edges) {
	const succ = tasksById[taskId];
	if (!succ) return { date: null, reason: null };
	let bestDate = null;
	let bestReason = null;
	for (const dep of edges) {
		if (dep.successor !== taskId) continue;
		const pred = tasksById[dep.predecessor];
		if (!pred) continue;
		const earliest = earliestStartForEdge(pred, succ, dep);
		if (!earliest) continue;
		if (!bestDate || diffDays(bestDate, earliest) > 0) {
			bestDate = earliest;
			bestReason = `${dep.type}, lag ${dep.lag || 0} from ${dep.predecessor}`;
		}
	}
	return { date: bestDate, reason: bestReason };
}

// Per-task conflict (date violation + inspection gate). Shared by the
// downstream and whole-graph variants below.
function taskConflict(tid, tasksById, edges) {
	const task = tasksById[tid];
	if (!task) return { conflict: false, reason: "" };
	const isMs = task.type === "Milestone";
	const anchor = isMs ? task.end : task.start;
	const { date: earliest, reason } = computeEarliestStart(tid, tasksById, edges);
	let conflict = false;
	let conflictReason = "";
	if (earliest && anchor && diffDays(anchor, earliest) > 0) {
		conflict = true;
		const days = diffDays(anchor, earliest);
		const which = isMs ? "Due" : "Starts";
		conflictReason = `${which} ${days} day${
			days === 1 ? "" : "s"
		} earlier than allowed (${reason}).`;
	}
	for (const d of edges) {
		if (d.successor !== tid) continue;
		const pred = tasksById[d.predecessor];
		if (pred && pred.type === "Inspection" && pred.status !== "Completed") {
			conflict = true;
			const ins = `Waiting on inspection ${pred.name} (${pred.status}).`;
			conflictReason = conflictReason ? `${ins} ${conflictReason}` : ins;
			break;
		}
	}
	return { conflict, reason: conflictReason };
}

function downstreamSubgraph(rootId, edges) {
	const subgraph = new Set([rootId]);
	const stack = [rootId];
	while (stack.length) {
		const node = stack.pop();
		for (const e of edges) {
			if (e.predecessor === node && !subgraph.has(e.successor)) {
				subgraph.add(e.successor);
				stack.push(e.successor);
			}
		}
	}
	return subgraph;
}

function topologicalDownstream(rootId, edges) {
	const subgraph = downstreamSubgraph(rootId, edges);
	const indeg = new Map();
	for (const id of subgraph) indeg.set(id, 0);
	for (const d of edges) {
		if (subgraph.has(d.predecessor) && subgraph.has(d.successor)) {
			indeg.set(d.successor, (indeg.get(d.successor) || 0) + 1);
		}
	}
	const queue = [];
	for (const [id, deg] of indeg) if (deg === 0) queue.push(id);
	const order = [];
	while (queue.length) {
		const node = queue.shift();
		order.push(node);
		for (const e of edges) {
			if (e.predecessor === node && subgraph.has(e.successor)) {
				const next = indeg.get(e.successor) - 1;
				indeg.set(e.successor, next);
				if (next === 0) queue.push(e.successor);
			}
		}
	}
	return { order, subgraphSize: subgraph.size };
}

// FLAG-ONLY downstream from rootId — matches schedule_engine.compute_conflicts.
export function computeConflicts(rootId, tasksById, edges) {
	const out = {};
	for (const tid of downstreamSubgraph(rootId, edges))
		out[tid] = taskConflict(tid, tasksById, edges);
	return out;
}

// Whole-graph variant for the full Gantt render — every task's own conflict.
export function computeAllConflicts(tasksById, edges) {
	const out = {};
	for (const tid of Object.keys(tasksById)) out[tid] = taskConflict(tid, tasksById, edges);
	return out;
}

export function hasCycle(predId, succId, edges, excludeId = null) {
	if (predId === succId) return true;
	const seen = new Set();
	const stack = [succId];
	while (stack.length) {
		const node = stack.pop();
		if (seen.has(node)) continue;
		seen.add(node);
		if (node === predId) return true;
		for (const e of edges) {
			if (e.predecessor === node && e.id !== excludeId) stack.push(e.successor);
		}
	}
	return false;
}

// CASCADE — matches schedule_engine.compute_cascade. rootOverride = {start,end}
// (Date or ISO) sets the root's working dates without persisting. Returns moves[]
// (dates as ISO strings) or null on a cycle.
export function computeCascade(rootId, tasksById, edges, rootOverride = null) {
	const { order, subgraphSize } = topologicalDownstream(rootId, edges);
	if (order.length !== subgraphSize) return null;

	const working = new Map();
	for (const tid of order) {
		const t = tasksById[tid];
		if (!t) continue;
		const isMs = t.type === "Milestone";
		let start = t.start;
		let end = t.end;
		if (tid === rootId && rootOverride) {
			start = rootOverride.start;
			end = rootOverride.end;
		}
		working.set(tid, {
			start,
			end,
			dur: isMs ? 0 : diffDays(start, end),
			isMs,
			type: t.type,
		});
	}

	const moves = [];
	for (const tid of order) {
		if (tid === rootId) continue;
		const cur = working.get(tid);
		if (!cur) continue;
		if (cur.isMs ? !cur.end : !cur.start || !cur.end) continue;

		let binding = null;
		let bindingReason = null;
		for (const dep of edges) {
			if (dep.successor !== tid) continue;
			let pd = working.get(dep.predecessor);
			if (!pd) {
				const t = tasksById[dep.predecessor];
				pd = t ? { start: t.start, end: t.end, type: t.type } : null;
			}
			if (!pd || !pd.end) continue;
			const earliest = earliestStartForEdge(
				{ start: pd.start, end: pd.end, type: pd.type },
				{ start: cur.start, end: cur.end, type: cur.type },
				dep,
				cur.dur
			);
			if (!earliest) continue;
			if (!binding || diffDays(binding, earliest) > 0) {
				binding = earliest;
				bindingReason = `${dep.type}, lag ${dep.lag || 0} from ${dep.predecessor}`;
			}
		}
		if (!binding) continue;
		const anchor = cur.isMs ? cur.end : cur.start;
		if (diffDays(anchor, binding) > 0) {
			if (cur.isMs) {
				moves.push({
					task: tid,
					old_start: null,
					old_end: iso(cur.end),
					new_start: null,
					new_end: iso(binding),
					reason: bindingReason,
					is_milestone: true,
				});
				working.set(tid, { ...cur, end: binding });
			} else {
				const newEnd = addDays(binding, cur.dur);
				moves.push({
					task: tid,
					old_start: iso(cur.start),
					old_end: iso(cur.end),
					new_start: iso(binding),
					new_end: iso(newEnd),
					reason: bindingReason,
				});
				working.set(tid, { ...cur, start: binding, end: newEnd });
			}
		}
	}
	return moves;
}
