<script setup>
// App picker landing (Frappe-like): root route `/` acts as the launchpad into
// the Desk app. Uses existing workspace metadata and keeps ERPNext integration
// external to this Vue app.

import { computed, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { WORKSPACE_META } from "@/data/workspaces";
import LogoIcon from "@/components/LogoIcon.vue";
import RoleSwitcher from "@/components/RoleSwitcher.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const store = useDataStore();
const router = useRouter();

const TILE_STYLE = {
	brand: "bg-white border border-ink-200 text-brand-600",
	workspace: "bg-ink-700 text-white",
	settings: "bg-ink-700 text-white",
};

const tiles = computed(() => {
	const out = [
		{
			key: "buildsuite-app",
			label: "BuildSuite",
			to: "/home",
			style: TILE_STYLE.brand,
			isLogo: true,
			iconSlug: null,
		},
	];

	for (const slug of store.visibleWorkspaces) {
		const meta = WORKSPACE_META[slug];
		if (!meta) continue;
		out.push({
			key: slug,
			label: meta.name,
			to: meta.to,
			style: TILE_STYLE.workspace,
			isLogo: false,
			iconSlug: slug,
		});
	}

	if (store.isAdmin) {
		out.push({
			key: "settings",
			label: "Settings",
			to: "/settings",
			style: TILE_STYLE.settings,
			isLogo: false,
			iconSlug: "settings",
		});
	}

	return out;
});

const search = ref("");
function onSearchSubmit() {
	if (search.value.trim()) router.push("/projects");
}
</script>

<template>
	<div class="min-h-screen bg-white flex flex-col">
		<header class="h-14 border-b border-ink-200 px-4 sm:px-6 flex items-center gap-3 sm:gap-4">
			<RouterLink to="/" class="flex items-center flex-shrink-0" title="Home">
				<LogoIcon :size="28" />
			</RouterLink>

			<div class="flex-1 flex justify-center">
				<div class="relative w-full max-w-xl">
					<svg
						class="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-400 pointer-events-none"
						width="15"
						height="15"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<circle cx="11" cy="11" r="7" />
						<path d="m21 21-4.3-4.3" />
					</svg>
					<input
						v-model="search"
						type="text"
						placeholder="Search"
						class="w-full bg-ink-50 border border-transparent hover:bg-ink-100 focus:bg-white focus:border-ink-200 text-sm text-ink-700 placeholder:text-ink-400 transition-colors"
						style="border-radius: 8px; padding: 8px 60px 8px 36px"
						@keyup.enter="onSearchSubmit"
					/>
					<span
						class="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-ink-400 font-medium hidden sm:inline tracking-wide"
						>Ctrl+K</span
					>
				</div>
			</div>

			<div class="flex items-center gap-1 sm:gap-2 flex-shrink-0">
				<button
					type="button"
					class="text-ink-400 hover:text-ink-700 hover:bg-ink-50 p-1.5 rounded"
					aria-label="Notifications"
					title="Notifications"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
						/>
					</svg>
				</button>
				<RoleSwitcher />
			</div>
		</header>

		<main class="flex-1 flex items-start justify-center px-4 sm:px-6 pt-16 sm:pt-24 pb-10">
			<div class="w-full max-w-5xl mx-auto">
				<div
					class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-x-4 gap-y-8"
				>
					<RouterLink
						v-for="tile in tiles"
						:key="tile.key"
						:to="tile.to"
						class="flex flex-col items-center gap-3 group"
					>
						<div
							class="w-16 h-16 flex items-center justify-center overflow-hidden transition-all group-hover:shadow-fp-md group-hover:-translate-y-0.5"
							:class="tile.style"
							style="border-radius: 14px"
						>
							<LogoIcon v-if="tile.isLogo" :size="64" />
							<svg
								v-else
								class="w-7 h-7"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath(tile.iconSlug)"
							/>
						</div>
						<span class="text-sm font-medium text-ink-900 text-center leading-tight">{{
							tile.label
						}}</span>
					</RouterLink>
				</div>
			</div>
		</main>
	</div>
</template>
