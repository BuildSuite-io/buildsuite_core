<script setup>
// Status pill for the procurement documents (Material Request / Purchase Order /
// Purchase Receipt), matching the prototype's exact PILL colour maps. The shared
// StatusBadge can't be reused here because the same status word (e.g. "Completed")
// carries a different colour in other modules (Task Completed is brand, a completed
// PO is success), so these business statuses live in their own map.
defineProps({
	status: { type: String, default: "" },
});

const PILL = {
	// Shared
	Draft: "bg-ink-100 text-ink-700",
	Cancelled: "bg-ink-100 text-ink-500",
	Closed: "bg-ink-100 text-ink-500",
	// Material Request
	Pending: "bg-warning-50 text-warning-700",
	"Partially Ordered": "bg-info-50 text-info-700",
	Ordered: "bg-success-50 text-success-700",
	Received: "bg-success-50 text-success-700",
	"Partially Received": "bg-info-50 text-info-700",
	Issued: "bg-success-50 text-success-700",
	Transferred: "bg-success-50 text-success-700",
	Stopped: "bg-ink-100 text-ink-500",
	// Purchase Order
	"To Receive and Bill": "bg-warning-50 text-warning-700",
	"To Receive": "bg-info-50 text-info-700",
	"To Bill": "bg-info-50 text-info-700",
	Completed: "bg-success-50 text-success-700",
	"On Hold": "bg-warning-50 text-warning-700",
	Delivered: "bg-success-50 text-success-700",
	// Purchase Receipt
	"Partly Billed": "bg-info-50 text-info-700",
	Return: "bg-danger-50 text-danger-700",
	"Return Issued": "bg-warning-50 text-warning-700",
};
</script>

<template>
	<span
		class="text-[11px] px-2 py-0.5 rounded-full whitespace-nowrap"
		:class="PILL[status] || 'bg-ink-100 text-ink-700'"
		>{{ status }}</span
	>
</template>
