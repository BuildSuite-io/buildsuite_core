<script setup>
// Gives a group of fields their own extension scope, for a form that sits on a screen of another DocType
// (the Task page's progress-entry and dependency forms). Inside it, a named DeskField takes the fieldRules
// registered for `doctype`, offers its field slots and shows its FieldErrors messages, exactly as on a form
// of its own. The screen's own scope (useExtensionFields on the page) is untouched: this one provides its own.
//
//   <ExtensionFormScope ref="scope" doctype="Task Progress Entry" :form="progressForm">
//     <DeskField name="narrative" ...>...</DeskField>
//   </ExtensionFormScope>
//   ...before saving:  await scope.value.ext.beforeSave(payload, progressForm)   // required rules, extension hooks
//   ...after saving:   await scope.value.ext.afterSave(doc, { isNew: true })
//
// `form` is the reactive object the fields are bound to (a rule's `ctx.form`, and what `required` reads).
import { useExtensionFields } from "@/sdk/useExtensionFields";

const props = defineProps({
	doctype: { type: String, required: true },
	form: { type: Object, default: () => ({}) },
});

const ext = useExtensionFields(props.doctype, props.form);
defineExpose({ ext });
</script>

<template>
	<slot :ext="ext" />
</template>
