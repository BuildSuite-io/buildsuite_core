<script setup>
// The bell (S390) — Frappe's notification dropdown, ported from the prototype.
//
// A DROPDOWN anchored to the bell, not a centred modal: a notification list is something you glance
// at and dismiss, and a modal with a backdrop makes a glance feel like an interruption. Backed by
// Frappe's Notification Log via api.notification; the badge count lives in the store (mirrors the
// to-do badge). Clicking a row opens the bespoke notification detail page.
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import {
	listNotifications,
	markNotificationRead,
	markAllNotificationsRead,
} from "@/data/notificationApi";
import { notificationType } from "@/data/notificationTypes";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const store = useDataStore();
const router = useRouter();

const open = ref(false);
const rows = ref([]);
const loading = ref(false);

async function refresh() {
	loading.value = true;
	try {
		const res = await listNotifications(20);
		rows.value = res.notifications || [];
	} catch {
		rows.value = [];
	} finally {
		loading.value = false;
	}
}

function toggle() {
	open.value = !open.value;
	if (open.value) refresh();
}

async function openNotification(n) {
	open.value = false;
	if (!n.read) {
		n.read = true; // optimistic — the detail page marks it read server-side too
		markNotificationRead(n.name)
			.then(() => store.loadNotificationCount())
			.catch(() => {});
	}
	router.push({ name: "notification-detail", params: { id: n.name } });
}

async function markAll() {
	try {
		await markAllNotificationsRead();
		store.loadNotificationCount();
		await refresh();
	} catch (err) {
		showToast(err.message || __("Could not mark notifications read"), "error");
	}
}

function seeAll() {
	open.value = false;
	router.push({ name: "notifications" });
}

// Relative for the first fortnight, then an absolute date — "in 63 days" isn't a time anyone reads.
function ago(dt) {
	if (!dt) return "";
	const iso = String(dt).replace(" ", "T");
	const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
	if (mins < 1) return __("just now");
	if (mins < 60) return __("{0}m ago", [mins]);
	const hrs = Math.round(mins / 60);
	if (hrs < 24) return __("{0}h ago", [hrs]);
	const days = Math.round(hrs / 24);
	if (days <= 14) return __("{0}d ago", [days]);
	return fmtDate(iso.slice(0, 10));
}
</script>

<template>
	<div class="relative">
		<button
			type="button"
			class="relative text-ink-500 hover:text-ink-900 hover:bg-ink-50 p-1.5 rounded"
			:aria-label="
				store.unseenNotificationCount
					? __('{0} unread notifications', [store.unseenNotificationCount])
					: __('Notifications')
			"
			:aria-expanded="String(open)"
			:title="__('Notifications')"
			@click="toggle"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
				/>
			</svg>
			<span
				v-if="store.unseenNotificationCount"
				class="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-brand-700 text-white text-[10px] font-semibold leading-4 tabular-nums text-center"
				>{{ store.unseenNotificationCount > 99 ? "99+" : store.unseenNotificationCount }}</span
			>
		</button>

		<!-- Outside-click backdrop, the same idiom the role and company switchers use. -->
		<div v-if="open" class="fixed inset-0 z-30" @click="open = false"></div>

		<div
			v-if="open"
			class="absolute right-0 top-full mt-1 z-40 bg-white border border-ink-200 rounded-lg shadow-fp-lg overflow-hidden"
			style="width: min(24rem, calc(100vw - 1.5rem))"
		>
			<!-- Header -->
			<div class="px-3 py-2.5 flex items-center gap-2 border-b border-ink-100">
				<div class="text-sm font-semibold text-ink-900">{{ __("Notifications") }}</div>
				<button
					v-if="store.unseenNotificationCount"
					type="button"
					class="ml-auto text-[11px] text-brand-700 hover:underline"
					@click="markAll"
				>
					{{ __("Mark all as read") }}
				</button>
			</div>

			<div class="max-h-96 overflow-y-auto">
				<div v-if="loading" class="px-3 py-8 text-center text-xs text-ink-500">{{ __("Loading…") }}</div>

				<button
					v-for="n in rows"
					v-else
					:key="n.name"
					type="button"
					class="w-full text-left px-3 py-2.5 flex items-start gap-2.5 border-b border-ink-100 last:border-b-0 hover:bg-ink-50"
					:class="n.read ? '' : 'bg-brand-50'"
					@click="openNotification(n)"
				>
					<span
						class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
						:class="notificationType(n.type).tint"
						:title="n.type"
					>
						<WorkspaceIcon :slug="notificationType(n.type).icon" :size="14" />
					</span>
					<span class="flex-1 min-w-0">
						<span class="block text-xs text-ink-900 leading-snug">{{ n.subject }}</span>
						<span class="block text-[11px] text-ink-500 mt-0.5">
							<template v-if="n.document_type">{{ n.document_type }} &middot; </template
							>{{ ago(n.creation) }}
						</span>
					</span>
					<UserAvatar
						v-if="n.from_user"
						:user-id="n.from_user"
						size="xs"
						class="flex-shrink-0 mt-0.5"
					/>
					<span
						v-if="!n.read"
						class="w-1.5 h-1.5 rounded-full bg-brand-600 flex-shrink-0 mt-2"
					></span>
				</button>

				<div v-if="!loading && !rows.length" class="px-3 py-8 text-center">
					<div class="text-xs text-ink-500">{{ __("Nothing here yet.") }}</div>
					<div class="text-[11px] text-ink-400 mt-1">
						{{ __("Assignments, mentions, shares and alerts addressed to you land here.") }}
					</div>
				</div>
			</div>

			<!-- Footer — a destination the prototype didn't have (it was dropdown-only); we now have a
			     full list page, so offer it. -->
			<button
				type="button"
				class="w-full px-3 py-2 text-center text-[11px] text-brand-700 hover:bg-ink-50 border-t border-ink-100"
				@click="seeAll"
			>
				{{ __("See all notifications") }}
			</button>
		</div>
	</div>
</template>
