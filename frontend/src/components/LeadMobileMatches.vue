<script setup>
// "This number is already on file" — the leads and customers that share a mobile number with the
// one being typed. A warning, never a block: the same person asking twice is common, and so is a
// shared family number. Used by the New lead form and the lead's page.
//
// With `offerUse` (the quotation form) each match offers "Use this lead / customer" (emits `use`);
// otherwise it links to the record (emits `open` first, e.g. to close a modal).
import { RouterLink } from "vue-router";
import StatusBadge from "@/components/StatusBadge.vue";
import { __ } from "@/utils/translate";

defineProps({
	matches: { type: Array, default: () => [] }, // [{ kind: 'Lead' | 'Customer', id, name, status }]
	offerUse: { type: Boolean, default: false },
	heading: { type: String, default: "" },
});
const emit = defineEmits(["use", "open"]);

function linkTo(match) {
	return match.kind === "Lead" ? `/leads/${encodeURIComponent(match.id)}` : "/customers";
}
</script>

<template>
	<div
		v-if="matches.length"
		class="border border-warning-200 bg-warning-50 px-3 py-2 text-xs text-warning-800"
		style="border-radius: 6px"
		role="status"
	>
		<p class="font-medium mb-1">{{ heading || __("This number is already on file:") }}</p>
		<ul class="space-y-1">
			<li
				v-for="m in matches"
				:key="`${m.kind}:${m.id}`"
				class="flex items-center gap-2 flex-wrap"
			>
				<span
					class="text-[10px] uppercase tracking-wider font-semibold text-warning-700"
					>{{ __(m.kind) }}</span
				>
				<span class="text-ink-900">{{ m.name }}</span>
				<StatusBadge v-if="m.status" :status="m.status" size="xs" />
				<button
					v-if="offerUse"
					type="button"
					class="desk-link ml-auto"
					@click="emit('use', m)"
				>
					{{ m.kind === "Lead" ? __("Use this lead") : __("Use this customer") }}
				</button>
				<RouterLink
					v-else
					:to="linkTo(m)"
					class="desk-link ml-auto"
					@click="emit('open', m)"
				>
					{{ __("Open") }}
				</RouterLink>
			</li>
		</ul>
	</div>
</template>
