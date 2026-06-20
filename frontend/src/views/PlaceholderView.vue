<script setup>
// Stub used by the 12 workspace landing routes (and the 4 legacy placeholders) until
// a proper Desk-styled workspace page lands. When `links` is non-empty, renders a row
// of shortcut tiles below the description — used by workspaces whose underlying list
// views already exist (Site Execution → Projects / WP / Tasks / Schedule, etc.) so the
// sidebar isn't a dead end. Workspaces with no backing screens omit `links` and show
// just the "Coming next" panel.

import { RouterLink } from "vue-router";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath, resolveWorkspaceIconSlug } from "@/utils/workspaceIcons";

defineProps({
	title: { type: String, required: true },
	icon: { type: String, default: "📄" },
	desc: { type: String, default: "" },
	// [{ label, to, icon, desc }] — when present, renders a tile grid linking out to
	// the listed routes. Leave empty for true "nothing here yet" placeholders.
	links: { type: Array, default: () => [] },
});
</script>

<template>
	<div class="px-6 py-10">
		<div class="max-w-3xl mx-auto">
			<div class="flex items-start gap-4 mb-6">
				<div
					class="w-12 h-12 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center flex-shrink-0"
				>
					<svg
						class="w-6 h-6"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
						v-html="getWorkspaceIconPath(resolveWorkspaceIconSlug(icon))"
					/>
				</div>
				<div class="min-w-0 flex-1">
					<h1 class="text-xl font-semibold text-ink-900">{{ title }}</h1>
					<p class="text-sm text-ink-500 mt-1 leading-relaxed">{{ desc }}</p>
				</div>
			</div>

			<!-- Shortcut tiles — only when `links` is provided. -->
			<div v-if="links.length" class="mb-6">
				<div class="text-[11px] uppercase tracking-wider text-ink-500 font-semibold mb-2">
					Module shortcuts
				</div>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<WorkspaceShortcut
						v-for="l in links"
						:key="l.to"
						:to="l.to"
						:icon="l.icon"
						:label="l.label"
						:description="l.desc || ''"
					/>
				</div>
			</div>

			<div
				v-if="!links.length"
				class="px-4 py-3 bg-ink-50 border border-ink-200 text-xs text-ink-600"
				style="border-radius: 6px"
			>
				<div class="font-medium text-ink-700 mb-1">No shortcuts available</div>
				<p class="leading-relaxed">
					There are no shortcuts configured for this workspace yet.
				</p>
			</div>
		</div>
	</div>
</template>
