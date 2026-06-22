<script setup>
// Inline link styled to BuildSuite brand green (#16A34A + underline-on-hover) via
// the .desk-link utility. Use this anywhere a list cell or form field needs a
// clickable text link inside Desk-styled pages. The color was originally Frappe
// blue (#1976D2); revised to brand green for cross-codebase visual consistency
// (see CLAUDE.md §12.4). For nav-style links inside the DeskShell sidebar use a
// plain RouterLink with .desk-nav-link instead.

import { RouterLink } from "vue-router";

defineProps({
	to: { type: [String, Object], default: null }, // Vue Router target
	href: { type: String, default: "" }, // external URL
	target: { type: String, default: "" }, // for href: _blank etc.
});
</script>

<template>
	<RouterLink v-if="to" :to="to" class="desk-link"><slot /></RouterLink>
	<a v-else-if="href" :href="href" :target="target" class="desk-link"><slot /></a>
	<span v-else class="desk-link"><slot /></span>
</template>
