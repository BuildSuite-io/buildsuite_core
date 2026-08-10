<script setup>
// Role-aware Home. One live aggregate read (api.home.get_home_dashboard) returns the
// logged-in user's snapshot tiles, primary CTA and alert cards — the same per-role content
// as the prototype's HomeWorkspaceView. This view is a thin renderer of that payload.
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useSessionStore } from "@/stores/session";
import { useUserNames } from "@/composables/useUserNames";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { fmtCompactINR } from "@/utils/format";
import { getHomeDashboard } from "@/data/homeDashboardApi";

const store = useDataStore();
const session = useSessionStore();
const { userName: resolveUserName } = useUserNames();

const dash = ref(null);
onMounted(async () => {
	try {
		dash.value = await getHomeDashboard();
	} catch {
		dash.value = null;
	}
});

const snapshot = computed(() => dash.value?.snapshot || []);
const alerts = computed(() => dash.value?.alerts || []);
const cta = computed(() => dash.value?.cta || null);

const now = new Date();
const greeting = computed(() => {
	const hour = now.getHours();
	if (hour < 12) return "Good morning";
	if (hour < 18) return "Good afternoon";
	return "Good evening";
});
const userName = computed(() => {
	const id = session.user && session.user !== "Guest" ? session.user : null;
	return (id && resolveUserName(id)) || store.user?.name || "Admin User";
});
const roleLabel = computed(() =>
	store.isAdmin ? "System Manager (Admin)" : store.currentRole?.name || "User"
);
const greetingSub = computed(
	() => dash.value?.greeting_sub || "Here is a snapshot of your work today."
);
const dateLabel = computed(() =>
	new Intl.DateTimeFormat("en-GB", {
		weekday: "long",
		day: "2-digit",
		month: "short",
		year: "numeric",
	}).format(now)
);
const initials = computed(() => {
	const name = userName.value || "A D";
	const parts = name.split(" ").filter(Boolean);
	if (!parts.length) return "AD";
	if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
	return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
});

// tone → icon chip classes (shared by snapshot tiles + alert cards).
const TONE = {
	brand: "bg-brand-50 text-brand-700",
	info: "bg-info-50 text-info-700",
	success: "bg-success-50 text-success-700",
	warning: "bg-warning-50 text-warning-700",
	danger: "bg-danger-50 text-danger-700",
	muted: "bg-ink-50 text-ink-400",
};
function toneClass(t) {
	return TONE[t] || TONE.brand;
}
function tileValue(m) {
	return m.format === "currency" ? fmtCompactINR(m.value) : m.value;
}

const quickActions = [
	{ label: "Users", to: "/settings/users", icon: "users" },
	{ label: "Companies", to: "/settings/companies", icon: "building-2" },
	{ label: "Project Categories", to: "/settings/project-categories", icon: "tag" },
	{ label: "Workspace Structure", to: "/settings/workspace-structure", icon: "layout-grid" },
	{ label: "All Projects", to: "/projects", icon: "clipboard-list" },
	{ label: "Data Tools", to: "/settings/data", icon: "database" },
];
</script>

<template>
	<div class="px-6 py-8 max-w-6xl mx-auto">
		<!-- Greeting -->
		<div class="flex items-start gap-4 mb-6">
			<div class="inline-flex items-center gap-2">
				<div
					class="w-12 h-12 text-base bg-brand-600 rounded-full flex items-center justify-center text-white font-medium flex-shrink-0"
				>
					{{ initials }}
				</div>
			</div>
			<div class="flex-1 min-w-0">
				<div class="text-sm text-ink-500">{{ greeting }},</div>
				<h1 class="text-2xl font-semibold text-ink-900 mt-0.5">{{ userName }}</h1>
				<p class="text-sm text-ink-500 mt-1.5">{{ greetingSub }}</p>
				<div class="text-[11px] text-ink-400 mt-1 flex flex-wrap items-center gap-x-2">
					<span>{{ roleLabel }}</span>
					<span class="text-ink-300">·</span>
					<span>{{ dateLabel }}</span>
				</div>
			</div>
		</div>

		<!-- Snapshot + CTA -->
		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
			<section
				class="lg:col-span-2 bg-white border border-ink-200 rounded-lg overflow-hidden"
			>
				<header
					class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Today's snapshot</h2>
					<span
						class="text-[10px] uppercase tracking-wider font-medium text-success-700 bg-success-50 px-2 py-0.5 rounded-full inline-flex items-center gap-1"
					>
						<span class="w-1.5 h-1.5 rounded-full bg-success-500"></span>
						Live
					</span>
				</header>
				<div class="p-5">
					<div class="grid grid-cols-2 sm:grid-cols-4 gap-5">
						<div v-for="m in snapshot" :key="m.label">
							<div
								class="w-11 h-11 rounded-lg flex items-center justify-center mb-3"
								:class="toneClass(m.tone)"
							>
								<svg
									width="22"
									height="22"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath(m.slug)"
								/>
							</div>
							<div
								class="font-semibold text-ink-900 tabular-nums leading-none"
								:class="m.format === 'currency' ? 'text-2xl' : 'text-3xl'"
							>
								{{ tileValue(m) }}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-2"
							>
								{{ m.label }}
							</div>
						</div>
					</div>
				</div>
			</section>

			<RouterLink
				v-if="cta"
				:to="cta.to"
				class="bg-brand-50 hover:bg-brand-100 rounded-lg p-5 flex flex-col justify-between transition-colors group"
			>
				<div class="flex items-start gap-3">
					<div
						class="w-9 h-9 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center flex-shrink-0"
					>
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath(cta.slug)"
						/>
					</div>
					<div class="min-w-0">
						<h2 class="text-base font-semibold text-ink-900 leading-tight">
							{{ cta.title }}
						</h2>
						<p class="text-xs text-ink-600 mt-1.5 leading-snug">{{ cta.sub }}</p>
					</div>
				</div>
				<div
					class="mt-4 inline-flex items-center gap-1.5 bg-brand-600 group-hover:bg-brand-700 text-white text-xs font-medium px-2.5 py-1.5 rounded-md self-start transition-colors"
				>
					{{ cta.cta }} <span aria-hidden="true">→</span>
				</div>
			</RouterLink>
		</div>

		<!-- Alert cards -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
			<RouterLink
				v-for="a in alerts"
				:key="a.key"
				:to="a.to"
				class="bg-white border border-ink-200 hover:border-brand-400 rounded-lg p-4 flex items-center gap-3 transition-colors group"
			>
				<div
					class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
					:class="toneClass(a.tone)"
				>
					<svg
						width="18"
						height="18"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
						v-html="getWorkspaceIconPath(a.slug)"
					/>
				</div>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-semibold text-ink-900">{{ a.title }}</div>
					<div class="text-xs text-ink-500 mt-0.5 truncate">{{ a.sub }}</div>
				</div>
				<div
					class="text-xs text-brand-700 group-hover:text-brand-800 font-medium flex-shrink-0"
				>
					View →
				</div>
			</RouterLink>
		</div>

		<!-- Quick actions -->
		<div class="mb-6">
			<h2 class="text-sm font-semibold text-ink-900 mb-3">Quick actions</h2>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
				<RouterLink
					v-for="action in quickActions"
					:key="action.to"
					:to="action.to"
					class="bg-white border border-ink-200 hover:border-brand-400 hover:shadow-sm p-4 rounded-lg flex items-center gap-3 group transition-all"
				>
					<div
						class="w-10 h-10 rounded-lg bg-ink-50 group-hover:bg-brand-50 text-ink-600 group-hover:text-brand-700 flex items-center justify-center flex-shrink-0 transition-colors"
					>
						<svg
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath(action.icon)"
						/>
					</div>
					<div class="flex-1 min-w-0">
						<div
							class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors"
						>
							{{ action.label }}
						</div>
					</div>
					<div class="text-ink-300 group-hover:text-brand-500 transition-colors">→</div>
				</RouterLink>
			</div>
		</div>
	</div>
</template>
