<script setup>
// Server-rendered print document — renders a doctype's Frappe Print Format inside the
// SPA. The body is whatever Desk would print: the doctype's DEFAULT Print Format
// (Customize Form → "Default Print Format") and the default / document Letter Head.
// Change the default in Desk and this view follows — no code change. PDF export is
// window.print() + the global @media print rules in style.css (hide chrome, white A4).
//
// Replaces the old bespoke per-doctype Vue layouts, which hardcoded the design and so
// never reflected the Desk print format / letter head.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getPrintHtml } from "@/data/printApi";
import { showToast } from "@/utils/appToast";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
	backTo: { type: String, default: "" },
	backLabel: { type: String, default: "Back" },
});
const router = useRouter();

const html = ref("");
const style = ref("");
const loading = ref(true);

// A <style> element inserted via innerHTML is parsed and applied by the browser, so the
// print format's own CSS rides along with its markup. Only rendered when we have HTML.
const rendered = computed(() =>
	html.value ? `<style>${style.value || ""}</style>${html.value}` : ""
);

function printDoc() {
	window.print();
}
function goBack() {
	if (props.backTo) router.push(props.backTo);
}

async function load() {
	loading.value = true;
	html.value = "";
	style.value = "";
	try {
		const res = await getPrintHtml(props.doctype, props.name);
		html.value = res?.html || "";
		style.value = res?.style || "";
	} catch (err) {
		showToast(err.message || "Failed to load print", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => [props.doctype, props.name], load, { immediate: true });
</script>

<template>
	<div class="bg-white min-h-full report-root">
		<!-- ===== Control bar (hidden in print) ===== -->
		<header class="border-b border-ink-200 bg-white sticky top-0 z-10 print:hidden">
			<div class="max-w-4xl mx-auto px-6 py-3 flex items-center gap-3">
				<button
					v-if="backTo"
					@click="goBack"
					class="text-xs text-ink-600 hover:text-ink-900 flex items-center gap-1"
				>
					<span>←</span><span>{{ backLabel }}</span>
				</button>
				<button
					v-if="html"
					@click="printDoc"
					class="ml-auto text-xs px-3 py-1.5 rounded bg-ink-900 text-white hover:bg-ink-800 flex items-center gap-1.5"
					title="Opens the browser print dialog. Pick 'Save as PDF' to export."
				>
					<svg
						class="w-3.5 h-3.5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.75"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<polyline points="6 9 6 2 18 2 18 9" />
						<path
							d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
						/>
						<rect x="6" y="14" width="12" height="8" />
					</svg>
					<span>Export PDF</span>
				</button>
			</div>
		</header>

		<!-- ===== Document (Frappe print format HTML + its style) ===== -->
		<main
			v-if="html"
			class="report-content max-w-4xl mx-auto px-6 py-8"
			v-html="rendered"
		></main>

		<!-- Loading / not found -->
		<main
			v-else-if="loading"
			class="max-w-4xl mx-auto px-6 py-16 text-center text-sm text-ink-500"
		>
			Loading…
		</main>
		<main v-else class="max-w-4xl mx-auto px-6 py-16 text-center">
			<div class="text-sm text-ink-700 mb-2">
				No printable document for <span class="font-mono">{{ name }}</span
				>.
			</div>
			<button
				v-if="backTo"
				@click="goBack"
				class="text-xs text-brand-700 hover:underline"
			>
				← {{ backLabel }}
			</button>
		</main>
	</div>
</template>
