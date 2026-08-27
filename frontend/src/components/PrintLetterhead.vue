<script setup>
// The shared branding band rendered at the top of every printed surface — docs
// (PO / Work Order / Invoice) and reports alike. Pulls the seeded "BuildSuite
// Standard" Letter Head (logo + registered address + GSTIN) from the backend, so
// editing that one record re-flows the branding everywhere. Renders the Letter
// Head's own HTML (v-html) — the data-URI logo makes it self-contained for both
// the browser (window.print) and server PDF.
import { ref, onMounted } from "vue";
import { getLetterHead } from "@/data/coreSettingsApi";

const props = defineProps({
	// A hairline divider below the band (matches the doc/report letterhead style).
	// Turn off where the caller supplies its own separator.
	bordered: { type: Boolean, default: true },
	// Render just the branding content (no section wrapper / margins), so it can sit
	// inside a caller's flex row (docs put the band left, the doc title right).
	inline: { type: Boolean, default: false },
});

// Module-level cache — fetch once per session, shared across every instance.
let cache = null;
let inflight = null;

const content = ref(cache?.content || "");

async function ensure() {
	if (cache) {
		content.value = cache.content || "";
		return;
	}
	if (!inflight) inflight = getLetterHead().catch(() => null);
	cache = (await inflight) || { content: "" };
	content.value = cache.content || "";
}
onMounted(ensure);
</script>

<template>
	<div v-if="content && inline" class="print-letter-head min-w-0" v-html="content" />
	<section
		v-else-if="content"
		class="report-section print-letter-head mb-6 pb-4"
		:class="bordered ? 'border-b-2 border-ink-300' : ''"
		v-html="content"
	/>
</template>
