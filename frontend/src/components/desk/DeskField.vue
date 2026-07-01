<script setup>
// A single form field with label-above-input layout. Frappe Desk pattern: small label
// in dark ink, red asterisk marker for required, optional hint or error line below.
// Slot receives the actual input — consumer passes DeskInput / DeskSelect / DeskTextarea
// or a custom widget.

defineProps({
	label: { type: String, default: "" },
	required: { type: Boolean, default: false },
	hint: { type: String, default: "" },
	error: { type: String, default: "" }, // takes precedence over hint when present
	forId: { type: String, default: "" }, // optional id to wire the label to the input
});
</script>

<template>
	<div class="min-w-0">
		<label v-if="label" :for="forId" class="block text-[11px] font-medium text-ink-700 mb-1">
			{{ label }}<span v-if="required" style="color: #d32f2f" class="ml-0.5">*</span>
		</label>
		<slot />
		<div v-if="error" class="text-[11px] mt-1" style="color: #d32f2f">{{ error }}</div>
		<div v-else-if="hint" class="text-[11px] text-ink-500 mt-1">{{ hint }}</div>
	</div>
</template>
