<script setup>
import { computed } from "vue";

const props = defineProps({
	status: { type: String, required: true },
	size: { type: String, default: "sm" },
});

const classes = computed(() => {
	const map = {
		Active: "bg-success-50 text-success-700",
		// Task status (custom task_status field): Yet To Start / In Progress / In Delay / Completed / Blocked
		"Yet To Start": "bg-ink-100 text-ink-600",
		"In Progress": "bg-info-50 text-info-700",
		"In Delay": "bg-danger-50 text-danger-700",
		Completed: "bg-brand-50 text-brand-700",
		Blocked: "bg-warning-50 text-warning-700",
		"On Hold": "bg-warning-50 text-warning-700",
		Planned: "bg-ink-100 text-ink-600",
		New: "bg-ink-100 text-ink-600",
		Ongoing: "bg-success-50 text-success-700",
		Delayed: "bg-danger-50 text-danger-700",
		Open: "bg-ink-100 text-ink-600",
		Draft: "bg-ink-100 text-ink-600",
		"Pending Approval": "bg-warning-50 text-warning-700",
		Approved: "bg-success-50 text-success-700",
		Rejected: "bg-danger-50 text-danger-700",
		Cancelled: "bg-ink-100 text-ink-500",
		High: "bg-danger-50 text-danger-700",
		Medium: "bg-warning-50 text-warning-700",
		Low: "bg-info-50 text-info-700",
		// Task Type values per proposal §M2 (Session 31). Slightly bolder fill (100
		// not 50) to differentiate from status/priority pills in the same row.
		Activity: "bg-ink-100 text-ink-700",
		Milestone: "bg-warning-100 text-warning-700",
		Inspection: "bg-info-100 text-info-700",
	};
	// Session 37 — pill shape (rounded-full + bumped horizontal padding) matching
	// the Frappe Cloud reference. Used on both Desk and Vue pages; both look
	// consistent with the new visual standard.
	const base = props.size === "xs" ? "text-[10px] px-2 py-0.5" : "text-xs px-2 py-0.5";
	return `${base} rounded-full font-medium inline-flex items-center ${
		map[props.status] || "bg-ink-100 text-ink-600"
	}`;
});
</script>

<template>
	<span :class="classes">{{ status }}</span>
</template>
