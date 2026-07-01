<script setup>
// Multi-line text input styled to Frappe Desk standards. Accepts v-model.

defineProps({
	modelValue: { type: String, default: "" },
	rows: { type: Number, default: 4 },
	placeholder: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
	readonly: { type: Boolean, default: false },
	name: { type: String, default: "" },
});
defineEmits(["update:modelValue"]);
</script>

<template>
	<textarea
		:value="modelValue"
		:rows="rows"
		:placeholder="placeholder"
		:disabled="disabled"
		:readonly="readonly"
		:name="name"
		class="desk-input resize-y leading-snug"
		@input="$emit('update:modelValue', $event.target.value)"
	/>
</template>
