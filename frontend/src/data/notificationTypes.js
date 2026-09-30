// Notification vocabulary — Frappe's Notification Log types, 1:1 with the prototype (S390).
//
// Frappe ships five types; four are here. Energy Point is deliberately absent — it belongs to
// Frappe's gamification module, which this app doesn't have, so it can never fire. Unknown types
// (including Energy Point, should one arrive) fall back to Alert.

export const NOTIFICATION_TYPES = [
	{
		id: "Assignment",
		label: "Assignment",
		desc: "Somebody put a record in your hands — a to-do, an approval, a bill to certify.",
		icon: "users-2",
		tint: "bg-brand-50 text-brand-700",
	},
	{
		id: "Mention",
		label: "Mention",
		desc: "You were named in a comment or a note on a record.",
		icon: "message-circle",
		tint: "bg-info-50 text-info-700",
	},
	{
		id: "Share",
		label: "Share",
		desc: "Somebody gave you access to a record you would not otherwise see.",
		icon: "paperclip",
		tint: "bg-ink-100 text-ink-600",
	},
	{
		id: "Alert",
		label: "Alert",
		desc: "Raised by a rule rather than a person — a deadline, an overrun, a rejection.",
		icon: "bell",
		tint: "bg-warning-50 text-warning-700",
	},
];

export const NOTIFICATION_TYPE_IDS = NOTIFICATION_TYPES.map((t) => t.id);

/** The type descriptor for a Notification Log `type`, falling back to Alert for anything unknown. */
export function notificationType(id) {
	return NOTIFICATION_TYPES.find((t) => t.id === id) || NOTIFICATION_TYPES[3];
}
