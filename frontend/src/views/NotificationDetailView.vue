<script setup>
// Notification — one notification, as a page (the prototype had only the dropdown; this is the
// bespoke detail view). Shows the type, subject, body, sender and the referenced record, and marks
// the notification read on open (refreshing the top-nav bell badge).
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { getNotification } from "@/data/notificationApi";
import { notificationType } from "@/data/notificationTypes";
import { useDataStore } from "@/stores";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { fmtDate } from "@/utils/format";

const props = defineProps({ id: { type: String, required: true } });

const router = useRouter();
const store = useDataStore();

const note = ref(null);
const loading = ref(true);
const notFound = ref(false);

const kind = computed(() => notificationType(note.value?.type));

// document_type -> in-app SPA route for the referenced record. Anything not here opens in Desk.
const SPA_ROUTES = {
	Task: (n) => `/tasks/${n}`,
	Project: (n) => `/projects/${n}`,
	"Work Package": (n) => `/work-packages/${n}`,
	"Stage Planning": (n) => `/stage-plannings/${n}`,
	BOQ: (n) => `/boq/${n}`,
	"Scope Change Order": (n) => `/sco/${n}`,
	"Purchase Order": (n) => `/procurement/purchase-orders/${n}`,
	"Material Request": (n) => `/procurement/material-requests/${n}`,
	"Subcontractor Work Order": (n) => `/subcontractor-work-orders/${n}`,
	ToDo: (n) => `/todo/${n}`,
};

const reference = computed(() => {
	const n = note.value;
	if (!n?.document_type || !n?.document_name) return null;
	const spa = SPA_ROUTES[n.document_type];
	return {
		type: n.document_type,
		name: n.document_name,
		label: n.reference_label || n.document_name,
		to: spa ? spa(n.document_name) : null,
		// Fall back to the Desk form for doctypes the SPA has no route for.
		desk: `/app/${n.document_type.toLowerCase().replaceAll(" ", "-")}/${encodeURIComponent(n.document_name)}`,
	};
});

function when(dt) {
	return dt ? fmtDate(String(dt).replace(" ", "T").slice(0, 10)) : "";
}

async function load() {
	loading.value = true;
	notFound.value = false;
	try {
		note.value = await getNotification(props.id);
		store.loadNotificationCount();
	} catch {
		notFound.value = true;
		note.value = null;
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

function openReference() {
	const r = reference.value;
	if (!r) return;
	if (r.to) router.push(r.to);
	else window.open(r.desk, "_blank", "noopener");
}
</script>

<template>
	<div class="max-w-3xl mx-auto px-3 sm:px-5 py-4 sm:py-6">
		<RouterLink
			:to="{ name: 'notifications' }"
			class="inline-flex items-center gap-1.5 text-xs text-ink-600 hover:text-ink-900 mb-3"
		>
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
			All notifications
		</RouterLink>

		<div v-if="loading" class="text-sm text-ink-500 px-1 py-14 text-center">Loading…</div>

		<div
			v-else-if="notFound || !note"
			class="border border-dashed border-ink-200 rounded-xl px-4 py-14 text-center"
		>
			<div class="text-sm text-ink-700">That notification is not here.</div>
			<div class="text-xs text-ink-500 mt-1">
				It may have been cleared, or it belongs to someone else.
			</div>
		</div>

		<div v-else class="bg-white border border-ink-200 rounded-xl overflow-hidden">
			<!-- Head -->
			<div class="px-4 sm:px-5 py-4 flex items-start gap-3">
				<span
					class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
					:class="kind.tint"
					:title="note.type"
				>
					<WorkspaceIcon :slug="kind.icon" :size="18" />
				</span>
				<div class="min-w-0 flex-1">
					<div class="flex flex-wrap items-center gap-2">
						<span class="text-[10px] uppercase tracking-wider font-semibold text-ink-500">
							{{ kind.label }}
						</span>
						<span class="text-[11px] text-ink-400 ml-auto">{{ when(note.creation) }}</span>
					</div>
					<h1 class="text-base sm:text-lg font-semibold text-ink-900 leading-snug mt-1">
						{{ note.subject }}
					</h1>
					<div v-if="note.from_user" class="flex items-center gap-1.5 mt-2 text-xs text-ink-600">
						<UserAvatar :user-id="note.from_user" size="xs" class="shrink-0" />
						<span>{{ note.from_user_name || note.from_user }}</span>
					</div>
				</div>
			</div>

			<!-- Body (the notification's own HTML content, when present) -->
			<div
				v-if="note.email_content"
				class="px-4 sm:px-5 py-4 border-t border-ink-100 text-sm text-ink-700 leading-relaxed notification-body"
				v-html="note.email_content"
			></div>

			<!-- Referenced record -->
			<div v-if="reference" class="px-4 sm:px-5 py-3 border-t border-ink-100">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1.5">
					Related record
				</div>
				<button
					type="button"
					class="inline-flex items-center gap-2 text-xs bg-ink-50 border border-ink-200 rounded-lg px-3 py-2 hover:border-brand-400"
					@click="openReference"
				>
					<span class="text-ink-900 font-medium truncate">{{ reference.label }}</span>
					<span class="text-ink-500 shrink-0">{{ reference.type }} →</span>
				</button>
			</div>
		</div>
	</div>
</template>

<style scoped>
/* The body is server-rendered Frappe HTML — give links + emphasis sensible defaults. */
.notification-body :deep(a) {
	color: theme("colors.brand.700");
	text-decoration: underline;
}
.notification-body :deep(p) {
	margin: 0 0 0.5rem;
}
.notification-body :deep(b),
.notification-body :deep(strong) {
	color: theme("colors.ink.900");
}
</style>
