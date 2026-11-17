<script setup>
// New / edit dialog for a BuildSuite Payment Term Template. Ported from the
// demo's PaymentTermsTemplatesView modal. `name` null → new, else edit.

import { ref, watch } from "vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import PaymentScheduleEditor from "@/components/PaymentScheduleEditor.vue";
import { getRecord, insertRecord, saveRecord, deleteRecord } from "@/data/doctypeRecordApi";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { __ } from "@/utils/translate";

const DOCTYPE = "BuildSuite Payment Term Template";

const props = defineProps({
	open: { type: Boolean, default: false },
	name: { type: String, default: null },
});
const emit = defineEmits(["close", "saved"]);

const confirmDialog = useConfirm();

const doc = ref(null); // the loaded doc when editing
const form = ref(emptyForm());
const error = ref("");
const saving = ref(false);

function emptyForm() {
	return {
		payment_term_name: "",
		project_category: "",
		description: "",
		enabled: 1,
		milestones: [],
	};
}

watch(
	() => props.open,
	async (o) => {
		if (!o) return;
		error.value = "";
		saving.value = false;
		doc.value = null;
		form.value = emptyForm();
		if (!props.name) return;
		try {
			doc.value = await getRecord(DOCTYPE, props.name);
		} catch (e) {
			error.value = e?.message || __("Could not load the template.");
			return;
		}
		form.value = {
			payment_term_name: doc.value.payment_term_name,
			project_category: doc.value.project_category || "",
			description: doc.value.description || "",
			enabled: doc.value.enabled,
			milestones: doc.value.milestones || [],
		};
	},
);

async function save() {
	if (!form.value.payment_term_name.trim()) return;
	saving.value = true;
	error.value = "";
	try {
		const payload = { ...form.value, project_category: form.value.project_category || null };
		await (doc.value
			? saveRecord({ ...doc.value, ...payload })
			: insertRecord({ doctype: DOCTYPE, ...payload }));
		showToast(__("Template saved"));
		emit("saved");
		emit("close");
	} catch (e) {
		error.value = e?.message || __("Could not save the template.");
	} finally {
		saving.value = false;
	}
}

async function remove() {
	const ok = await confirmDialog({
		title: __("Delete template"),
		message: __(
			'Delete "{0}"? Quotations, tenders and projects that already loaded it keep their own copy of the milestones.',
			[form.value.payment_term_name],
		),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteRecord(DOCTYPE, props.name);
		showToast(__("Template deleted"));
		emit("saved");
		emit("close");
	} catch (e) {
		error.value = e?.message || __("Could not delete the template.");
	}
}
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-4 overflow-y-auto"
			@click.self="emit('close')"
		>
			<div
				class="bg-white w-full max-w-4xl shadow-fp-lg my-6 flex flex-col"
				style="border-radius: 12px; max-height: calc(100vh - 3rem)"
				@click.stop
			>
				<header
					class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0"
				>
					<h2 class="text-sm font-semibold text-ink-900">
						{{ name ? __("Edit template") : __("New template") }}
					</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-700 px-1"
						:aria-label="__('Close')"
						@click="emit('close')"
					>
						✕
					</button>
				</header>

				<div class="p-5 space-y-4 overflow-y-auto flex-1">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						<DeskField :label="__('Name')" required>
							<DeskInput
								v-model="form.payment_term_name"
								:placeholder="__('e.g. Residential, stage-wise')"
							/>
						</DeskField>
						<DeskField :label="__('Project Category')">
							<DeskLinkPicker
								v-model="form.project_category"
								doctype="Project Category"
								:placeholder="__('Any project type')"
							/>
						</DeskField>
					</div>
					<DeskField :label="__('Description')">
						<DeskTextarea v-model="form.description" :rows="2" />
					</DeskField>
					<label class="flex items-center gap-2 text-sm text-ink-700">
						<input
							type="checkbox"
							class="accent-brand-600"
							:checked="!!form.enabled"
							@change="(e) => (form.enabled = e.target.checked ? 1 : 0)"
						/>
						{{ __("Enabled") }}
					</label>

					<PaymentScheduleEditor
						:rows="form.milestones"
						@update:rows="(v) => (form.milestones = v)"
					/>
					<div v-if="error" class="text-xs text-danger-700">{{ error }}</div>
				</div>

				<footer
					class="px-5 py-3 border-t border-ink-200 flex items-center justify-between gap-2 flex-shrink-0"
				>
					<button
						v-if="name"
						type="button"
						class="text-xs px-3 py-1.5 border border-danger-200 text-danger-700 hover:bg-danger-50"
						style="border-radius: 6px"
						@click="remove"
					>
						{{ __("Delete") }}
					</button>
					<span v-else></span>
					<div class="flex gap-2">
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 text-ink-700 hover:bg-ink-50"
							style="border-radius: 6px"
							@click="emit('close')"
						>
							{{ __("Cancel") }}
						</button>
						<button
							type="button"
							class="desk-save-btn"
							:disabled="!form.payment_term_name.trim() || saving"
							@click="save"
						>
							{{ saving ? __("Saving…") : __("Save") }}
						</button>
					</div>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
