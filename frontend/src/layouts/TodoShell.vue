<script setup>
// To-dos — the shell (prototype S365/S393). Deliberately thin: this app has two
// screens and one job, so a sidebar would be four-fifths chrome. The bar carries
// the way back to the app home, what app you're in, the theme toggle, and whose
// list this is. The screens render full-width beneath it (no DeskShell sidebar).
import { computed } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { useDataStore } from "@/stores";
import { useSessionStore } from "@/stores/session";
import { useUserNames } from "@/composables/useUserNames";
import { getSessionUser } from "@/utils/session";
import { __ } from "@/utils/translate";
import LogoIcon from "@/components/LogoIcon.vue";
import NotificationPanel from "@/components/NotificationPanel.vue";
import UserAvatar from "@/components/UserAvatar.vue";

const store = useDataStore();
const session = useSessionStore();
const { userName } = useUserNames();

function toggleTheme() {
	store.toggleTheme();
}

// The signed-in user — same resolution as DeskShell's footer profile.
const profileUser = computed(() => {
	const u = session.user;
	return u && u !== "Guest" ? u : getSessionUser();
});
const profileName = computed(() => userName(profileUser.value) || profileUser.value || "User");
const profileRole = computed(() => {
	const persona = session.access?.persona;
	if (persona) return persona;
	const roles = session.access?.roles || [];
	const bs = roles.find((r) => r.startsWith("BuildSuite "));
	if (bs) return bs.replace("BuildSuite ", "");
	if (roles.includes("System Manager")) return "System Manager";
	if (profileUser.value === "Administrator") return "Administrator";
	return "";
});
</script>

<template>
	<div class="min-h-screen bg-ink-50 flex flex-col">
		<header
			class="h-14 bg-white border-b border-ink-200 px-3 sm:px-5 flex items-center gap-2 sm:gap-3 sticky top-0 z-30"
		>
			<!-- Back to the app home. Label hides on a phone; the chevron carries it. -->
			<RouterLink
				to="/home"
				class="flex items-center gap-1.5 text-ink-600 hover:text-ink-900 hover:bg-ink-50 rounded-lg px-2 h-10 shrink-0"
				:title="__('Back to home')"
			>
				<svg
					class="w-4 h-4 shrink-0"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M15 19l-7-7 7-7"
					/>
				</svg>
				<span class="text-sm hidden sm:inline">{{ __("Home") }}</span>
			</RouterLink>

			<div class="w-px h-6 bg-ink-200 shrink-0 hidden sm:block"></div>

			<RouterLink to="/todo" class="flex items-center gap-2 min-w-0 h-10 px-1 rounded-lg">
				<LogoIcon :size="24" class="shrink-0" />
				<span class="font-semibold text-ink-900 text-sm sm:text-base truncate">{{
					__("To-dos")
				}}</span>
			</RouterLink>

			<div class="ml-auto flex items-center gap-1 sm:gap-2">
				<!-- Theme toggle — sun in dark mode, moon in light mode. -->
				<button
					type="button"
					class="text-ink-500 hover:text-ink-900 hover:bg-ink-50 rounded-lg w-10 h-10 flex items-center justify-center"
					:aria-label="
						store.theme === 'dark'
							? __('Switch to light theme')
							: __('Switch to dark theme')
					"
					:title="
						store.theme === 'dark'
							? __('Switch to light theme')
							: __('Switch to dark theme')
					"
					@click="toggleTheme"
				>
					<svg
						v-if="store.theme === 'dark'"
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
						/>
					</svg>
					<svg
						v-else
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
						/>
					</svg>
				</button>

				<!-- Notifications — the bell stays reachable without the full desk chrome. -->
				<NotificationPanel />

				<!-- Whose list this is, in words rather than a tooltip. -->
				<div
					v-if="profileUser"
					class="hidden md:flex items-center gap-2 pl-2 ml-1 border-l border-ink-200"
				>
					<UserAvatar :user-id="profileUser" size="sm" />
					<span class="leading-tight min-w-0">
						<span class="block text-xs font-medium text-ink-900 truncate">{{
							profileName
						}}</span>
						<span class="block text-[10px] text-ink-500 truncate">{{
							profileRole
						}}</span>
					</span>
				</div>
			</div>
		</header>

		<main class="flex-1 min-w-0">
			<RouterView />
		</main>
	</div>
</template>
