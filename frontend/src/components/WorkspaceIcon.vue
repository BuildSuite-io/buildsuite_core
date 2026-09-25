<script setup>
// Small inline icon by slug — wraps getWorkspaceIconPath (the app's shared line-icon set) so
// components can drop in an icon the way the prototype's WorkspaceIcon did.
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

defineProps({
	slug: { type: String, required: true },
	size: { type: [Number, String], default: 16 },
});
</script>

<template>
	<svg
		:width="size"
		:height="size"
		viewBox="0 0 24 24"
		fill="none"
		stroke="currentColor"
		stroke-width="1.75"
		stroke-linecap="round"
		stroke-linejoin="round"
		aria-hidden="true"
		v-html="getWorkspaceIconPath(slug)"
	/>
</template>
