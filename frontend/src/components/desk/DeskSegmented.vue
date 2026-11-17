<script setup>
// A segmented control — a few mutually exclusive choices side by side (Board | List,
// Lead | Customer). The same look as the To-dos view toggle, as a shared component.
//
//   <DeskSegmented v-model="view" :options="[{ value: 'board', label: __('Board'), icon: 'layout-grid' }, …]" />
//
// An option's icon is a WorkspaceIcon slug; with one, the label hides on narrow screens.
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";

defineProps({
	modelValue: { type: [String, Number, Boolean], default: "" },
	options: { type: Array, required: true }, // [{ value, label, icon?, title? }]
	size: { type: String, default: "md" }, // sm (h-7) | md (h-8)
	disabled: { type: Boolean, default: false },
	ariaLabel: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue", "change"]);

function pick(value) {
	emit("update:modelValue", value);
	emit("change", value);
}
</script>

<template>
	<div
		role="group"
		:aria-label="ariaLabel || undefined"
		class="inline-flex items-center gap-1 bg-ink-100 rounded-lg p-0.5 shrink-0"
	>
		<button
			v-for="o in options"
			:key="String(o.value)"
			type="button"
			class="flex items-center gap-1.5 px-2.5 rounded-md text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			:class="[
				size === 'sm' ? 'h-7' : 'h-8',
				modelValue === o.value
					? 'bg-white text-ink-900 shadow-sm'
					: 'text-ink-600 hover:text-ink-900',
			]"
			:aria-pressed="modelValue === o.value"
			:title="o.title || o.label"
			:disabled="disabled"
			@click="pick(o.value)"
		>
			<WorkspaceIcon v-if="o.icon" :slug="o.icon" :size="14" />
			<span :class="o.icon ? 'hidden sm:inline' : ''">{{ o.label }}</span>
		</button>
	</div>
</template>
