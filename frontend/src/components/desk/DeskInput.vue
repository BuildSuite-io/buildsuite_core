<script setup>
// Single-line text input styled to Frappe Desk standards (thin border, tight padding,
// Frappe blue focus ring). Accepts v-model.

defineProps({
	modelValue: { type: [String, Number], default: "" },
	type: { type: String, default: "text" }, // text, number, date, email, etc.
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
	readonly: { type: Boolean, default: false },
	name: { type: String, default: "" },
	autocomplete: { type: String, default: "" },
	// Number-input bounds. Forwarded to the native input so browser arrow keys
	// + spin buttons honour them; the parent should ALSO clamp on save for
	// belt-and-braces (paste / direct typing can bypass HTML min/max).
	min: { type: [String, Number], default: undefined },
	max: { type: [String, Number], default: undefined },
	step: { type: [String, Number], default: undefined },
});
defineEmits(["update:modelValue"]);
</script>

<template>
	<input
		:type="type"
		:value="modelValue"
		:placeholder="placeholder"
		:disabled="disabled"
		:readonly="readonly"
		:name="name"
		:autocomplete="autocomplete"
		:min="min"
		:max="max"
		:step="step"
		class="desk-input"
		@input="$emit('update:modelValue', $event.target.value)"
	/>
</template>
