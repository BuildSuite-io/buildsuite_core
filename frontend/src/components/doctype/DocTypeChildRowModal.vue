<script setup>
// Full-detail editor for a single child-table row. The grid shows only the child
// DocType's in_list_view columns; this modal renders ALL of its fields so rows with
// more than a few fields are fully editable. Binds straight to the row object, so
// edits reflect in the grid immediately (the parent form saves the whole doc).
import { computed } from "vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import DeskField from "@/components/desk/DeskField.vue";
import DocTypeFieldControl from "@/components/doctype/DocTypeFieldControl.vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	row: { type: Object, default: () => ({}) },
	doctype: { type: String, required: true },
	title: { type: String, default: "Row detail" },
	disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);

const { meta } = useDoctypeMeta(props.doctype);

const SKIP = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Image",
	"Fold",
	"Heading",
	"Table",
	"Table MultiSelect",
]);

function evalDependsOn(expr) {
	if (!expr) return true;
	try {
		if (expr.startsWith("eval:")) {
			// eslint-disable-next-line no-new-func
			return !!Function("doc", `return (${expr.slice(5)});`)(props.row);
		}
		return !!props.row[expr];
	} catch {
		return true;
	}
}

const fields = computed(() =>
	(meta.value?.fields || []).filter(
		(f) => !SKIP.has(f.fieldtype) && !f.hidden && evalDependsOn(f.depends_on)
	)
);
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
			@click.self="emit('close')"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
				style="border-radius: 12px; max-height: calc(100vh - 3rem)"
				@click.stop
			>
				<header class="px-5 py-3 border-b border-ink-200 flex items-center justify-between">
					<h2 class="text-sm font-semibold text-ink-900">{{ title }}</h2>
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 text-lg leading-none"
						aria-label="Close"
						@click="emit('close')"
					>
						×
					</button>
				</header>

				<div class="p-5 overflow-y-auto min-h-0">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
						<DeskField
							v-for="f in fields"
							:key="f.fieldname"
							:label="f.label || f.fieldname"
							:required="!!f.reqd"
							:hint="f.description || ''"
						>
							<DocTypeFieldControl
								v-model="row[f.fieldname]"
								:field="f"
								:context="row"
								:disabled="disabled || !!f.read_only"
							/>
						</DeskField>
					</div>
				</div>

				<footer class="px-5 py-3 border-t border-ink-200 flex justify-end">
					<button type="button" class="desk-save-btn" @click="emit('close')">Done</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
