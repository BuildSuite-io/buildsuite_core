<script setup>
// Status pill for the procurement documents (Material Request / Purchase Order /
// Purchase Receipt), matching the prototype's exact PILL colour maps. The shared
// StatusBadge can't be reused here because the same status word (e.g. "Completed")
// carries a different colour in other modules (Task Completed is brand, a completed
// PO is success), so these business statuses live in their own map.
import { computed } from "vue";
import { __ } from "@/utils/translate";

const props = defineProps({
	status: { type: String, default: "" },
	// "quotation": a Supplier Quotation, whose live Submitted state reads green (the prototype's
	// SQ_PILL); a Request for Quotation's Submitted stays blue (RFQ_PILL).
	kind: { type: String, default: "" },
});

const PILL = {
	// Shared
	Draft: "bg-ink-100 text-ink-700",
	Cancelled: "bg-ink-100 text-ink-500",
	Closed: "bg-ink-100 text-ink-500",
	// Request for Quotation / Supplier Quotation — Submitted is their live state (a supplier's
	// quote on a request reads Pending / Received, below); a quotation past its validity is Expired.
	Submitted: "bg-info-50 text-info-700",
	Expired: "bg-warning-50 text-warning-700",
	// Material Request — approval axis (workflow_state), matching the prototype's StatusBadge map
	"Pending Approval": "bg-warning-50 text-warning-700",
	Approved: "bg-success-50 text-success-700",
	Rejected: "bg-danger-50 text-danger-700",
	// Material Request — ordering axis (native status)
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
const QUOTATION_PILL = { Submitted: "bg-success-50 text-success-700" };
const pillClass = computed(
	() =>
		(props.kind === "quotation" && QUOTATION_PILL[props.status]) ||
		PILL[props.status] ||
		"bg-ink-100 text-ink-700"
);
</script>

<template>
	<span class="text-[11px] px-2 py-0.5 rounded-full whitespace-nowrap" :class="pillClass">{{
		__(status)
	}}</span>
</template>
