<script setup>
// A lead's notes — ERPNext's own CRM Note table on the Lead (who wrote what, when), as in
// ERPNext's Lead form. Notes are HTML (a Text Editor field); the read-only editor renders them
// safely. Every change returns the lead's notes again (api.leads.add/edit/delete_note), which
// this panel hands up through `update:notes`.
import { defineAsyncComponent, ref } from "vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { useConfirm } from "@/composables/useConfirm";
import { useUserNames } from "@/composables/useUserNames";
import { addLeadNote, deleteLeadNote, editLeadNote } from "@/data/leadsApi";
import { __ } from "@/utils/translate";

const RichTextEditor = defineAsyncComponent(() => import("@/components/RichTextEditor.vue"));

const props = defineProps({
	lead: { type: String, required: true },
	notes: { type: Array, default: () => [] }, // [{ name, note, added_by, added_on }], newest first
	canWrite: { type: Boolean, default: false },
});
const emit = defineEmits(["update:notes"]);

const confirmDialog = useConfirm();
const { userName } = useUserNames();

const draft = ref("");
const adding = ref(false);
const editing = ref(null); // { id, text }
const error = ref("");
const saving = ref(false);

const isBlank = (html) =>
	!String(html || "")
		.replace(/<[^>]*>/g, "")
		.trim();

async function run(fn, failMessage) {
	error.value = "";
	saving.value = true;
	try {
		emit("update:notes", await fn());
		return true;
	} catch (e) {
		error.value = e?.message || failMessage;
		return false;
	} finally {
		saving.value = false;
	}
}

async function addNote() {
	if (isBlank(draft.value)) return;
	if (await run(() => addLeadNote(props.lead, draft.value), __("Could not add the note."))) {
		draft.value = "";
		adding.value = false;
	}
}

async function saveNote() {
	if (isBlank(editing.value?.text)) return;
	const { id, text } = editing.value;
	if (await run(() => editLeadNote(props.lead, id, text), __("Could not save the note."))) {
		editing.value = null;
	}
}

async function removeNote(note) {
	const ok = await confirmDialog({
		title: __("Delete note"),
		message: __("Delete this note?"),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (ok)
		await run(() => deleteLeadNote(props.lead, note.name), __("Could not delete the note."));
}

const fmtNoteDate = (d) =>
	d
		? new Date(String(d).replace(" ", "T")).toLocaleString(undefined, {
				dateStyle: "medium",
				timeStyle: "short",
		  })
		: "";
</script>

<template>
	<div class="max-w-3xl" data-test="lead-notes">
		<div class="flex items-center mb-3">
			<span v-if="error" class="text-xs text-danger-700">{{ error }}</span>
			<button
				v-if="canWrite && !adding"
				type="button"
				class="ml-auto text-xs px-2.5 py-1 border border-ink-200 text-ink-700 hover:bg-ink-50"
				style="border-radius: 6px"
				@click="adding = true"
			>
				{{ __("+ New note") }}
			</button>
		</div>

		<div v-if="adding" class="mb-4 space-y-2">
			<RichTextEditor v-model="draft" min-height="6rem" />
			<div class="flex justify-end gap-2">
				<button
					type="button"
					class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					@click="
						adding = false;
						draft = '';
					"
				>
					{{ __("Cancel") }}
				</button>
				<button type="button" class="desk-save-btn" :disabled="saving" @click="addNote">
					{{ __("Add note") }}
				</button>
			</div>
		</div>

		<p v-if="!notes.length && !adding" class="text-sm text-ink-500">
			{{ __("No notes yet.") }}
		</p>

		<article
			v-for="n in notes"
			:key="n.name"
			class="bg-white border border-ink-200 px-4 py-3 mb-2"
			style="border-radius: 6px"
		>
			<div class="flex items-start gap-3">
				<UserAvatar :user-id="n.added_by" size="sm" />
				<div class="min-w-0 flex-1">
					<div class="text-xs flex items-baseline gap-2 flex-wrap">
						<span class="font-semibold text-ink-900">{{
							userName(n.added_by) || n.added_by
						}}</span>
						<span class="text-ink-500">{{ fmtNoteDate(n.added_on) }}</span>
					</div>
					<template v-if="editing && editing.id === n.name">
						<RichTextEditor v-model="editing.text" min-height="5rem" class="mt-2" />
						<div class="flex justify-end gap-2 mt-2">
							<button
								type="button"
								class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
								style="border-radius: 6px"
								@click="editing = null"
							>
								{{ __("Cancel") }}
							</button>
							<button
								type="button"
								class="desk-save-btn"
								:disabled="saving"
								@click="saveNote"
							>
								{{ __("Save") }}
							</button>
						</div>
					</template>
					<RichTextEditor
						v-else
						:model-value="n.note"
						:editable="false"
						min-height="0"
						class="mt-1 !border-0"
					/>
				</div>
				<div
					v-if="canWrite && !(editing && editing.id === n.name)"
					class="flex gap-1 shrink-0"
				>
					<button
						type="button"
						class="text-xs text-ink-500 hover:text-ink-900 px-1"
						:aria-label="__('Edit note')"
						@click="editing = { id: n.name, text: n.note }"
					>
						{{ __("Edit") }}
					</button>
					<button
						type="button"
						class="text-xs text-danger-700 hover:underline px-1"
						:aria-label="__('Delete note')"
						@click="removeNote(n)"
					>
						{{ __("Delete") }}
					</button>
				</div>
			</div>
		</article>
	</div>
</template>
