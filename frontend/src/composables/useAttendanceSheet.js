// Shared by both Field Attendance forms: the header-drives-the-rows rule and the
// roster helpers. `getForm` is a getter so the caller can pass a `reactive`
// object (New) or a `ref` replaced wholesale on snapshot (Detail).

import { computed, ref, watch } from "vue";
import { getRoster } from "@/data/fieldAttendanceApi";

export function useAttendanceSheet(getForm) {
	const form = computed(getForm);

	// A header change overrides that field on every row — it is the bulk control.
	//
	// A watcher can't tell "the user changed this field" from "the whole form
	// object was replaced underneath me". The detail view starts with an empty
	// `{}` and swaps in a snapshot on Edit, so without this guard every watcher
	// fires on entering edit mode and flattens the per-row values — an Absent
	// worker silently becomes Present, and gets paid a full day.
	// Each watcher needs its OWN record of the form it last saw — a shared flag
	// would let the first watcher absorb the swap and the other two would then
	// mistake the same tick for a user edit.
	function onHeaderChange(key, apply) {
		let seenForm = form.value;
		watch(
			() => form.value?.[key],
			(v) => {
				const swapped = form.value !== seenForm;
				seenForm = form.value;
				if (swapped) return;
				(form.value?.employee_list || []).forEach((r) => apply(r, v));
			}
		);
	}

	onHeaderChange("status", (r, v) => {
		r.status = v;
		if (v === "Absent") r.overtime_hours = 0;
	});
	onHeaderChange("overtime_hours", (r, v) => {
		if (r.status !== "Absent") r.overtime_hours = Number(v) || 0;
	});
	onHeaderChange("comments", (r, v) => (r.comments = v));

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
		projectRoster,
		rosterToAdd,
		rosterTitle,
		addProjectRoster,
	};
}
