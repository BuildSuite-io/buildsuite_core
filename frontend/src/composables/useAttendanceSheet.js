// Shared by both Field Attendance forms: the header-drives-the-rows rule and the
// roster helpers. `getForm` is a getter so the caller can pass a `reactive`
// object (New) or a `ref` replaced wholesale on snapshot (Detail).

import { computed, ref, watch } from "vue";
import { getRoster } from "@/data/fieldAttendanceApi";

export function useAttendanceSheet(getForm) {
	const form = computed(getForm);

	// A header change overrides that field on every row — it is the bulk control.
	//
	// These are explicit handlers, not watchers, on purpose. A watcher cannot tell
	// "the user changed this field" from "the whole form object was replaced
	// underneath me" — the detail view starts with `{}` and swaps in a snapshot on
	// Edit, which fires every watcher and flattens the per-row values. Guarding
	// that by tracking object identity fails the other way: re-entering Edit with
	// unchanged values never fires, the marker goes stale, and the next real edit
	// is discarded. Either way an Absent worker silently becomes Present and gets
	// paid a full day. A handler only runs on real input, so neither can happen.
	function eachRow(fn) {
		(form.value?.employee_list || []).forEach(fn);
	}

	function setHeaderStatus(v) {
		form.value.status = v;
		eachRow((r) => {
			r.status = v;
			// Leaving Absent restores the header's overtime; staying puts it at 0.
			r.overtime_hours = v === "Absent" ? 0 : Number(form.value?.overtime_hours) || 0;
		});
	}

	function setHeaderOvertime(v) {
		form.value.overtime_hours = v;
		eachRow((r) => {
			if (r.status !== "Absent") r.overtime_hours = Number(v) || 0;
		});
	}

	function setHeaderComments(v) {
		form.value.comments = v;
		eachRow((r) => (r.comments = v));
	}

	const inTable = computed(
		() => new Set((form.value?.employee_list || []).map((r) => r.employee).filter(Boolean))
	);

	function headerOt() {
		return form.value?.status === "Absent" ? 0 : Number(form.value?.overtime_hours) || 0;
	}

	function newRow(employee = "", employee_name = "") {
		return {
			employee,
			employee_name,
			status: form.value?.status,
			overtime_hours: headerOt(),
			comments: form.value?.comments,
		};
	}

	function addRow() {
		form.value.employee_list.push(newRow());
	}

	function addWorkers(workers) {
		for (const w of workers) {
			if (inTable.value.has(w.employee)) continue;
			form.value.employee_list.push(newRow(w.employee, w.employee_name));
		}
	}

	const projectRoster = ref([]);
	const rosterError = ref("");
	let rosterToken = 0; // drops a slow response for a project the user left

	watch(
		() => form.value?.project,
		async (project) => {
			const token = ++rosterToken;
			projectRoster.value = [];
			rosterError.value = "";
			if (!project) return;
			try {
				const rows = await getRoster(project);
				if (token !== rosterToken) return;
				projectRoster.value = rows;
			} catch (err) {
				if (token !== rosterToken) return;
				rosterError.value = err.message || "Could not load the project roster.";
			}
		},
		{ immediate: true }
	);

	// Only the ones not already in the table.
	const rosterToAdd = computed(() =>
		projectRoster.value.filter((e) => !inTable.value.has(e.employee))
	);

	function addProjectRoster() {
		addWorkers(rosterToAdd.value);
	}

	const rosterTitle = computed(() => {
		if (rosterError.value) return rosterError.value;
		return projectRoster.value.length
			? `${projectRoster.value.length} worker(s) allocated to this project`
			: "No workers allocated to this project yet";
	});

	return {
		inTable,
		addRow,
		addWorkers,
		setHeaderStatus,
		setHeaderOvertime,
		setHeaderComments,
		rosterToAdd,
		rosterTitle,
		addProjectRoster,
	};
}
