import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.notification.* — the current user's notifications
// (Frappe Notification Log). Mirrors data/todoApi.js.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.notification.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// { me, notifications: [...] } — the current user's notifications, newest first, enriched with the
// sender name, the referenced record's label, and a bool `read`.
export const listNotifications = (limit = 20) => call("list_notifications", { limit });
// Unread notifications for me — the top-nav bell badge.
export const myUnseenNotificationCount = () => call("my_unseen_count");
// One notification (enriched) — marks it read as a side effect.
export const getNotification = (name) => call("get_notification", { name });
// Mark one / all of my notifications read.
export const markNotificationRead = (name) => call("mark_notification_read", { name });
export const markAllNotificationsRead = () => call("mark_all_notifications_read");
