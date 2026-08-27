<script setup>
// Page-level chrome for a Desk-styled page. Renders:
//   [ breadcrumb › trail        ]
//   [ Title  <StatusBadge>      <actions slot> ]
//   [ optional subtitle line    ]
//   [ slot: page body            ]
//
// Sharp corners on the outer container (Desk doesn't round its page chrome), tight
// vertical padding, white background. Place a DeskList, DeskForm, or freeform body
// inside via the default slot.

import { computed } from "vue";
import { RouterLink } from "vue-router";
import StatusBadge from "@/components/StatusBadge.vue";
import PrintLetterhead from "@/components/PrintLetterhead.vue";

const props = defineProps({
	title: { type: String, required: true },
	subtitle: { type: String, default: "" },
	breadcrumbs: { type: Array, default: () => [] }, // [{ label, to? }]
	// Accepts a single status string OR an array of status strings (each rendered as a
	// StatusBadge inline with the title — useful for status + priority pairs).
	status: { type: [String, Array], default: "" },
	// Puts a Print / PDF button in the actions row and marks the page as a print
	// root, so the shared @media print rules in style.css hide the desk chrome and
	// scale the type down. Kept on the primitive rather than pasted into each report
	// so every report surface prints the same way and none are silently missing it.
	printable: { type: Boolean, default: false },
});

// window is not in template scope, so this cannot be an inline handler.
function printPage() {
	window.print();
}

const statusList = computed(() => {
	if (!props.status) return [];
	return Array.isArray(props.status) ? props.status.filter(Boolean) : [props.status];
});
</script>

<template>
	<div class="desk-page" :class="printable ? 'report-root report-content' : ''">
		<!-- Shared branding band — print-only, so the on-screen report stays a plain
		     app table but the printed/PDF output carries the Letter Head. -->
		<PrintLetterhead v-if="printable" class="hidden print:block" />
		<nav
			v-if="breadcrumbs.length"
			class="text-[11px] text-ink-500 flex items-center gap-1.5 flex-wrap mb-1.5"
			aria-label="Breadcrumb"
		>
			<template v-for="(c, i) in breadcrumbs" :key="i">
				<RouterLink v-if="c.to" :to="c.to" class="desk-link">{{ c.label }}</RouterLink>
				<span v-else>{{ c.label }}</span>
				<span v-if="i < breadcrumbs.length - 1" class="text-ink-300">›</span>
			</template>
		</nav>

		<div class="flex items-start justify-between gap-3 mb-3">
			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-2 flex-wrap">
					<h1
						data-test="page-title"
						class="text-base font-semibold text-ink-900 leading-tight"
					>
						{{ title }}
					</h1>
					<StatusBadge v-for="s in statusList" :key="s" :status="s" />
				</div>
				<p v-if="subtitle" class="text-xs text-ink-500 mt-0.5">{{ subtitle }}</p>
			</div>
			<div
				data-test="page-actions"
				class="flex items-center gap-2 flex-shrink-0 print:hidden"
			>
				<slot name="actions" />
				<button
					v-if="printable"
					type="button"
					class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 flex items-center gap-1.5"
					style="border-radius: 6px"
					title="Print, or save as PDF from the print dialog"
					@click="printPage"
				>
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
						class="w-3.5 h-3.5 text-ink-400"
					>
						<path d="M6 9V2h12v7" />
						<path
							d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
						/>
						<path d="M6 14h12v8H6z" />
					</svg>
					Print
				</button>
			</div>
		</div>

		<slot />
	</div>
</template>
