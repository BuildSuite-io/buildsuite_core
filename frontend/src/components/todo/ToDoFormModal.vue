<script setup>
// The to-do create / edit form (S365), over Frappe's ToDo via api.todo.save_todo. The reference
// (what it's about) is set by the record it was raised from and shown read-only — never typed.
import { ref, reactive, computed, watch } from "vue";
import { getSessionUser } from "@/utils/session";
import { TODO_STATUSES, TODO_PRIORITIES, todoReference } from "@/data/todo";
import { saveTodo } from "@/data/todoApi";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	todo: { type: Object, default: null },
	referenceType: { type: String, default: null },
	referenceName: { type: String, default: null },
});
const emit = defineEmits(["close", "saved"]);

const error = ref("");
const saving = ref(false);
const me = getSessionUser();

const BLANK = {
	description: "",
	allocated_to: "",
	priority: "Medium",
	status: "Open",
	date: "",
	reference_type: null,
	reference_name: null,
};
const form = reactive({ ...BLANK });
const editing = computed(() => !!props.todo);
const reference = computed(() =>
	todoReference({
		reference_type: form.reference_type,
		reference_name: form.reference_name,
		reference_label: props.todo?.reference_label,
	})
);

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return;
		error.value = "";
		if (props.todo) {
			Object.assign(form, {
				description: props.todo.description || "",
				allocated_to: props.todo.allocated_to || "",
				priority: props.todo.priority || "Medium",
				status: props.todo.status || "Open",
				date: props.todo.date || "",
				reference_type: props.todo.reference_type || null,
				reference_name: props.todo.reference_name || null,
			});
		} else {
			Object.assign(form, {
				...BLANK,
				allocated_to: me || "",
				reference_type: props.referenceType || null,
				reference_name: props.referenceName || null,
			});
		}
	},
	{ immediate: true }
);

async function save() {
	const text = form.description.trim();
	if (!text) {
		error.value = "Write what needs doing — it is the only required field.";
		return;
	}
	saving.value = true;
	try {
		const saved = await saveTodo({
			name: props.todo?.name || undefined,
			description: text,
			priority: form.priority,
			status: form.status,
			date: form.date || undefined,
			allocated_to: form.allocated_to || undefined,
		});
		emit("saved", saved);
	} catch (e) {
		error.value = e.message || "Could not save that.";
	} finally {
		saving.value = false;
	}
}
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-end sm:items-center justify-center sm:p-4"
			@click="emit('close')"
		>
			<div
				class="bg-white w-full sm:max-w-lg max-h-[92vh] sm:max-h-[86vh] flex flex-col rounded-t-2xl sm:rounded-xl border border-ink-200 shadow-xl"
				@click.stop
			>
				<header class="px-4 sm:px-5 py-3 border-b border-ink-200 flex items-center justify-between gap-3 shrink-0">
					<h2 class="text-sm font-semibold text-ink-900">{{ editing ? "Edit to-do" : "New to-do" }}</h2>
					<button
						type="button"
						class="w-9 h-9 -mr-1.5 flex items-center justify-center text-ink-500 hover:text-ink-900 hover:bg-ink-50 rounded-lg"
						aria-label="Close"
						@click="emit('close')"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
					</button>
				</header>

				<div class="px-4 sm:px-5 py-4 overflow-y-auto flex-1 space-y-4">
					<DeskField label="What needs doing" required hint="The first line becomes the heading on the board.">
						<DeskTextarea v-model="form.description" :rows="3" placeholder="e.g. Renew the company GST registration certificate" />
					</DeskField>

					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<DeskField label="Assigned to">
							<DeskLinkPicker
								v-model="form.allocated_to"
								doctype="User"
								label-field="full_name"
								value-field="name"
								placeholder="Pick a person…"
							/>
						</DeskField>
						<DeskField label="Due date" hint="Optional.">
							<DeskInput v-model="form.date" type="date" />
						</DeskField>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<DeskField label="Priority">
							<DeskSelect v-model="form.priority">
								<option v-for="p in TODO_PRIORITIES" :key="p" :value="p">{{ p }}</option>
							</DeskSelect>
						</DeskField>
						<DeskField v-if="editing" label="Status">
							<DeskSelect v-model="form.status">
								<option v-for="st in TODO_STATUSES" :key="st" :value="st">{{ st }}</option>
							</DeskSelect>
						</DeskField>
					</div>

					<DeskField v-if="reference" label="About" hint="Set by the record this was raised from.">
						<div class="flex items-center gap-2 text-sm text-ink-700 bg-ink-50 border border-ink-200 rounded-lg px-3 py-2">
							<WorkspaceIcon :slug="reference.icon" :size="14" class="text-ink-500 shrink-0" />
							<span class="truncate">{{ reference.label }}</span>
							<span class="text-[11px] text-ink-500 shrink-0">{{ reference.type }}</span>
						</div>
					</DeskField>

					<p v-if="error" class="text-xs text-danger-700">{{ error }}</p>
				</div>

				<footer class="px-4 sm:px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 shrink-0">
					<button
						type="button"
						class="text-xs font-medium px-3 h-10 sm:h-8 border border-ink-200 bg-white text-ink-700 hover:bg-ink-50 rounded-md"
						@click="emit('close')"
					>
						Cancel
					</button>
					<button type="button" class="desk-save-btn !h-10 sm:!h-8 !px-4" :disabled="saving" @click="save">
						{{ saving ? "Saving…" : editing ? "Save" : "Add to-do" }}
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
