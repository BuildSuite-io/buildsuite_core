export const STATUS_LABELS = {
	Open: "Sent",
	Ordered: "Accepted",
	"Partially Ordered": "Partially accepted",
	Lost: "Rejected",
};

export const statusLabel = (status) => STATUS_LABELS[status] || status || "—";
