<script setup>
// Rich-text (WYSIWYG) editor — a thin v-model wrapper over frappe-ui's TextEditor (TipTap), so a
// native "Text Editor" field edits like Frappe Desk: formatting, lists, links and TABLES. Used by
// the generic DocType form control (DocTypeFieldControl) and the Terms & Conditions settings, so
// a Text Editor field behaves the same everywhere. Heavy (TipTap) — load it lazily where it's used.
import { nextTick, ref, watch } from "vue";
import { TextEditor } from "frappe-ui";
import "frappe-ui/editor-style.css";

const props = defineProps({
	modelValue: { type: String, default: "" },
	editable: { type: Boolean, default: true },
	minHeight: { type: String, default: "10rem" },
});
const emit = defineEmits(["update:modelValue"]);

// Only a person typing is an edit. frappe-ui's TextEditor pushes `content` into TipTap with
// setContent(), and TipTap 3 emits an update for that — on a value set from outside and when
// the editor is (re)created with its content. So a terms template loaded for us came back as an
// edit, and a parent listening for edits (dropping the template link) reacted to its own load.
// A person's edit happens with the focus inside the editor (typing, pasting, the toolbar, which
// refocuses it); a programmatic load does not. The echo of an outside change is ignored too.
const root = ref(null);
let lastEmitted = props.modelValue;
let settingFromOutside = false;
watch(
	() => props.modelValue,
	(value) => {
		if (value === lastEmitted) return;
		settingFromOutside = true;
		nextTick(() => (settingFromOutside = false));
	}
);
function onChange(html) {
	if (settingFromOutside || !root.value?.contains(document.activeElement)) return;
	lastEmitted = html;
	emit("update:modelValue", html);
}
</script>

<template>
	<div
		ref="root"
		class="rich-text-editor bg-white border border-ink-200 rounded-md overflow-hidden"
		:class="{ 'rich-text-editor--readonly': !editable }"
	>
		<TextEditor
			:content="props.modelValue"
			:fixed-menu="editable"
			:editable="editable"
			:editor-class="`prose prose-sm max-w-none px-3 py-2 focus:outline-none rte-content`"
			@change="onChange"
		/>
	</div>
</template>

<style scoped>
.rich-text-editor :deep(.rte-content) {
	min-height: v-bind(minHeight);
}
/* frappe-ui's fixed toolbar ships a tight `p-1` (4px) with the buttons flush against the
   border and the scroll track. Give it breathing room and align its left edge with the
   editor content (px-3). Targets the toolbar bar (Menu.vue root) inside the fixed menu. */
.rich-text-editor :deep(.inline-flex.bg-surface-white) {
	padding: 0.5rem 0.75rem;
}
/* Keep tables legible both while editing and read-only. */
.rich-text-editor :deep(table) {
	border-collapse: collapse;
	width: 100%;
	margin: 0.5rem 0;
}
.rich-text-editor :deep(th),
.rich-text-editor :deep(td) {
	border: 1px solid var(--ink-200, #e5e7eb);
	padding: 0.35rem 0.5rem;
	text-align: left;
}
</style>
