<script setup>
// A single form field with label-above-input layout. Frappe Desk pattern: small label
// in dark ink, red asterisk marker for required, optional hint or error line below.
// Slot receives the actual input — consumer passes DeskInput / DeskSelect / DeskTextarea
// or a custom widget.
//
// `name` makes the field addressable by installed apps (SDK 1.6): the form's own name for the
// field, usually the DocType fieldname (docs/extension-sdk-form-fields.md lists them per form).
// Inside a form that has called useExtensionFields, a named field
//   - takes the extension's rule for it: sdk.doctype(dt).on({ fieldRules: { <name>: { hidden,
//     readOnly, label, hint, required } } })
//   - offers the slots form.<DocType>.before.field.<name> and form.<DocType>.after.field.<name>
//   - shows the message of a FieldErrors thrown from a beforeSave hook
// A field Core marks `required` cannot be hidden by an extension: that would make the form unsaveable.

import { computed, inject, onBeforeUnmount, onMounted, watch } from "vue";
import ExtensionSlot from "@/components/ExtensionSlot.vue";
import { FORM_KEY } from "@/sdk/anchors";
import { fieldRule, fieldValue } from "@/sdk/registry";

const props = defineProps({
	label: { type: String, default: "" },
	required: { type: Boolean, default: false },
	hint: { type: String, default: "" },
	error: { type: String, default: "" }, // takes precedence over hint when present
	forId: { type: String, default: "" }, // optional id to wire the label to the input
	name: { type: String, default: "" }, // the field's name for extensions (see above)
});

const form = inject(FORM_KEY, null);
const addressed = computed(() => !!(form && props.name));
const rule = computed(() =>
	addressed.value ? fieldRule(form.doctype, props.name, form.context) : {}
);

const warned = new Set();
const hidden = computed(() => {
	if (!rule.value.hidden) return false;
	if (props.required) {
		const key = `${form.doctype}.${props.name}`;
		if (!warned.has(key)) {
			warned.add(key);
			console.warn(`[buildsuite] ${key} is required by Core: an extension cannot hide it`);
		}
		return false;
	}
	return true;
});
const label = computed(() => rule.value.label ?? props.label);
const hint = computed(() => rule.value.hint ?? props.hint);
const isRequired = computed(() => props.required || !!rule.value.required);
const message = computed(
	() => props.error || (addressed.value && form.context.fieldErrors?.[props.name]) || ""
);

// let the form know this field is on screen (so an extension's `required` is only enforced on fields
// that are), and drop a field-level message as soon as the value changes
onMounted(() => {
	if (addressed.value) form.mounted?.set(props.name, { label, hidden });
});
onBeforeUnmount(() => {
	if (addressed.value && form.mounted?.get(props.name)?.label === label) {
		form.mounted.delete(props.name);
	}
});
watch(
	() => (addressed.value ? fieldValue(form.context, props.name) : undefined),
	() => {
		if (addressed.value && form.context.fieldErrors?.[props.name]) {
			delete form.context.fieldErrors[props.name];
		}
	}
);
</script>

<template>
	<div v-if="!hidden" class="min-w-0" :data-field="addressed ? name : undefined">
		<ExtensionSlot
			v-if="addressed"
			:name="`form.${form.doctype}.before.field.${name}`"
			:context="form.context"
		/>
		<label v-if="label" :for="forId" class="block text-[11px] font-medium text-ink-700 mb-1">
			{{ label }}<span v-if="isRequired" style="color: #d32f2f" class="ml-0.5">*</span>
		</label>
		<div v-if="rule.readOnly" inert aria-disabled="true" class="opacity-70">
			<slot />
		</div>
		<slot v-else />
		<div v-if="message" data-field-error class="text-[11px] mt-1" style="color: #d32f2f">
			{{ message }}
		</div>
		<div v-else-if="hint" class="text-[11px] text-ink-500 mt-1">{{ hint }}</div>
		<ExtensionSlot
			v-if="addressed"
			:name="`form.${form.doctype}.after.field.${name}`"
			:context="form.context"
		/>
	</div>
</template>
