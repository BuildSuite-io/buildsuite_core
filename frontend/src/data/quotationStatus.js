export const STATUS_LABELS = {
	Open: "Sent",
	Ordered: "Accepted",
	"Partially Ordered": "Partially accepted",
	Lost: "Rejected",
};

export const statusLabel = (status) => STATUS_LABELS[status] || status || "—";

// Out with the customer and still unanswered — the only state where a decision is ours to
// record, and the only one where a passed validity date is worth chasing.
export const awaitsAnswer = (status) => ["Open", "Replied"].includes(status);
