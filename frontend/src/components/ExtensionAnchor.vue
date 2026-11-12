<script setup>
// A position beside a form section where installed apps can add components. Rendered by
// DeskSection (for every section that has an `id`), so every form built from DeskSection is
// extendable without any per-view markup. Only active inside a form that has called
// useExtensionFields (it provides the DocType); elsewhere it renders nothing.
//
// Slot names: form.<DocType>.before.<id> and form.<DocType>.after.<id>.
import { inject } from "vue";
import ExtensionSlot from "@/components/ExtensionSlot.vue";
import { FORM_KEY } from "@/sdk/anchors";

defineProps({
	id: { type: String, required: true },
	position: { type: String, required: true }, // "before" | "after"
});

const form = inject(FORM_KEY, null);
</script>

<template>
	<ExtensionSlot
		v-if="form"
		:name="`form.${form.doctype}.${position}.${id}`"
		:context="form.context"
	/>
</template>
