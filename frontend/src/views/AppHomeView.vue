<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";

const store = useDataStore();

const now = new Date();
const todayISO = now.toISOString().slice(0, 10);

const greeting = computed(() => {
	const hour = now.getHours();
	if (hour < 12) return "Good morning";
	if (hour < 18) return "Good afternoon";
	return "Good evening";
});

const userName = computed(() => store.user?.name || "Admin User");

const roleLabel = computed(() =>
	store.isAdmin ? "System Manager (Admin)" : store.currentRole?.name || "User"
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

const activeProjectsCount = computed(() => store.activeProjectsCount || 0);
const openTasksCount = computed(() => store.openTasksCount || 0);
const usersCount = computed(() => {
	const ids = new Set((store.team || []).map((u) => u.id));
	if (store.user?.id) ids.add(store.user.id);
	return ids.size;
});
const workspacesCount = computed(() => (store.visibleWorkspaces || []).length);

const pendingScosCount = computed(() => store.pendingScosCount || 0);
const overdueTasksCount = computed(
	() =>
		(store.tasks || []).filter(
			(t) =>
				t.endDate &&
				t.endDate < todayISO &&
				t.status !== "Completed" &&
				t.status !== "Cancelled"
		).length
);
const progressTodayCount = computed(
	() => (store.taskProgressEntries || []).filter((e) => e.entryDate === todayISO).length
);

const quickActions = [
	{ label: "Users", to: "/settings/users", icon: "users" },
	{ label: "Companies", to: "/settings/companies", icon: "companies" },
	{ label: "Project Types", to: "/settings/project-types", icon: "project-types" },
	{
		label: "Workspace Structure",
		to: "/settings/workspace-structure",
		icon: "workspace-structure",
	},
	{ label: "All Projects", to: "/projects", icon: "projects" },
	{ label: "Data Tools", to: "/settings/data", icon: "data-tools" },
];

function showCount(value, fallback) {
	return Number.isFinite(value) ? value : fallback;
}
</script>

<template>
	<div class="px-6 py-8 max-w-6xl mx-auto">
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
				<p class="text-sm text-ink-500 mt-1.5">
					Here is a snapshot of system activity today.
				</p>
				<div class="text-[11px] text-ink-400 mt-1 flex flex-wrap items-center gap-x-2">
					<span>{{ roleLabel }}</span>
					<span class="text-ink-300">·</span>
					<span>{{ dateLabel }}</span>
				</div>
			</div>
		</div>

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
						<div>
							<div
								class="w-11 h-11 rounded-lg flex items-center justify-center mb-3 bg-brand-50 text-brand-700"
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
								>
									<rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
									<path
										d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"
									></path>
									<path d="M12 11h4"></path>
									<path d="M12 16h4"></path>
									<path d="M8 11h.01"></path>
									<path d="M8 16h.01"></path>
								</svg>
							</div>
							<div
								class="text-3xl font-semibold text-ink-900 tabular-nums leading-none"
							>
								{{ showCount(activeProjectsCount, 4) }}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-2"
							>
								Active projects
							</div>
						</div>
						<div>
							<div
								class="w-11 h-11 rounded-lg flex items-center justify-center mb-3 bg-info-50 text-info-700"
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
								>
									<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
									<polyline points="22 4 12 14.01 9 11.01"></polyline>
								</svg>
							</div>
							<div
								class="text-3xl font-semibold text-ink-900 tabular-nums leading-none"
							>
								{{ showCount(openTasksCount, 9) }}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-2"
							>
								Open tasks
							</div>
						</div>
						<div>
							<div
								class="w-11 h-11 rounded-lg flex items-center justify-center mb-3 bg-success-50 text-success-700"
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
								>
									<path d="M14 19a6 6 0 0 0-12 0"></path>
									<circle cx="8" cy="9" r="4"></circle>
									<path d="M22 19a6 6 0 0 0-6-6 4 4 0 1 0 0-8"></path>
								</svg>
							</div>
							<div
								class="text-3xl font-semibold text-ink-900 tabular-nums leading-none"
							>
								{{ showCount(usersCount, 7) }}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-2"
							>
								Users
							</div>
						</div>
						<div>
							<div
								class="w-11 h-11 rounded-lg flex items-center justify-center mb-3 bg-warning-50 text-warning-700"
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
								>
									<rect width="7" height="7" x="3" y="3" rx="1"></rect>
									<rect width="7" height="7" x="14" y="3" rx="1"></rect>
									<rect width="7" height="7" x="14" y="14" rx="1"></rect>
									<rect width="7" height="7" x="3" y="14" rx="1"></rect>
								</svg>
							</div>
							<div
								class="text-3xl font-semibold text-ink-900 tabular-nums leading-none"
							>
								{{ showCount(workspacesCount, 11) }}
							</div>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mt-2"
							>
								Workspaces
							</div>
						</div>
					</div>
				</div>
			</section>

			<RouterLink
				to="/settings"
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
						>
							<path
								d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"
							></path>
							<circle cx="12" cy="12" r="3"></circle>
						</svg>
					</div>
					<div class="min-w-0">
						<h2 class="text-base font-semibold text-ink-900 leading-tight">
							Settings
						</h2>
						<p class="text-xs text-ink-600 mt-1.5 leading-snug">
							Manage workspaces, users, project types, and data.
						</p>
					</div>
				</div>
				<div
					class="mt-4 inline-flex items-center gap-1.5 bg-brand-600 group-hover:bg-brand-700 text-white text-xs font-medium px-2.5 py-1.5 rounded-md self-start transition-colors"
				>
					Open Settings <span aria-hidden="true">→</span>
				</div>
			</RouterLink>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
			<RouterLink
				to="/sco"
				class="bg-white border border-ink-200 hover:border-brand-400 rounded-lg p-4 flex items-center gap-3 transition-colors group"
			>
				<div
					class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-warning-50 text-warning-700"
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
					>
						<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
						<path d="M3 3v5h5"></path>
						<path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
						<path d="M16 16h5v5"></path>
					</svg>
				</div>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-semibold text-ink-900">Pending SCOs</div>
					<div class="text-xs text-ink-500 mt-0.5 truncate">
						{{ showCount(pendingScosCount, 2) }} awaiting approval
					</div>
				</div>
				<div
					class="text-xs text-brand-700 group-hover:text-brand-800 font-medium flex-shrink-0"
				>
					View →
				</div>
			</RouterLink>

			<RouterLink
				to="/tasks"
				class="bg-white border border-ink-200 hover:border-brand-400 rounded-lg p-4 flex items-center gap-3 transition-colors group"
			>
				<div
					class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-danger-50 text-danger-700"
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
					>
						<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
						<polyline points="22 4 12 14.01 9 11.01"></polyline>
					</svg>
				</div>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-semibold text-ink-900">Overdue tasks</div>
					<div class="text-xs text-ink-500 mt-0.5 truncate">
						{{ showCount(overdueTasksCount, 4) }} past their end date
					</div>
				</div>
				<div
					class="text-xs text-brand-700 group-hover:text-brand-800 font-medium flex-shrink-0"
				>
					View →
				</div>
			</RouterLink>

			<RouterLink
				to="/progress-entries"
				class="bg-white border border-ink-200 hover:border-brand-400 rounded-lg p-4 flex items-center gap-3 transition-colors group"
			>
				<div
					class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 bg-ink-50 text-ink-400"
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
					>
						<path
							d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
						></path>
						<polyline points="14 2 14 8 20 8"></polyline>
						<line x1="16" x2="8" y1="13" y2="13"></line>
						<line x1="16" x2="8" y1="17" y2="17"></line>
						<line x1="10" x2="8" y1="9" y2="9"></line>
					</svg>
				</div>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-semibold text-ink-900">Progress today</div>
					<div class="text-xs text-ink-500 mt-0.5 truncate">
						{{
							progressTodayCount
								? `${progressTodayCount} entries filed`
								: "No entries filed yet"
						}}
					</div>
				</div>
				<div
					class="text-xs text-brand-700 group-hover:text-brand-800 font-medium flex-shrink-0"
				>
					View →
				</div>
			</RouterLink>
		</div>

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
							v-if="action.icon === 'users'"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="M14 19a6 6 0 0 0-12 0"></path>
							<circle cx="8" cy="9" r="4"></circle>
							<path d="M22 19a6 6 0 0 0-6-6 4 4 0 1 0 0-8"></path>
						</svg>
						<svg
							v-else-if="action.icon === 'companies'"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"></path>
							<path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"></path>
							<path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"></path>
							<path d="M10 6h4"></path>
							<path d="M10 10h4"></path>
							<path d="M10 14h4"></path>
							<path d="M10 18h4"></path>
						</svg>
						<svg
							v-else-if="action.icon === 'project-types'"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<circle cx="12" cy="12" r="10"></circle>
							<path d="M12 16v-4"></path>
							<path d="M12 8h.01"></path>
						</svg>
						<svg
							v-else-if="action.icon === 'workspace-structure'"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<rect width="7" height="7" x="3" y="3" rx="1"></rect>
							<rect width="7" height="7" x="14" y="3" rx="1"></rect>
							<rect width="7" height="7" x="14" y="14" rx="1"></rect>
							<rect width="7" height="7" x="3" y="14" rx="1"></rect>
						</svg>
						<svg
							v-else-if="action.icon === 'projects'"
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
							<path
								d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"
							></path>
							<path d="M12 11h4"></path>
							<path d="M12 16h4"></path>
							<path d="M8 11h.01"></path>
							<path d="M8 16h.01"></path>
						</svg>
						<svg
							v-else
							width="20"
							height="20"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path
								d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
							></path>
							<polyline points="14 2 14 8 20 8"></polyline>
							<line x1="16" x2="8" y1="13" y2="13"></line>
							<line x1="16" x2="8" y1="17" y2="17"></line>
							<line x1="10" x2="8" y1="9" y2="9"></line>
						</svg>
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
