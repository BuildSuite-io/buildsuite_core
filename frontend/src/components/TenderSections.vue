<script setup>
// Named prose blocks on a tender — scope of work ahead of the items, terms after them.
// Read-only when `editable` is false, which is how the detail page renders it.

import { ref } from "vue";
import { frappeRequest } from "frappe-ui-frappe-request";
import { useConfirm } from "@/composables/useConfirm";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const props = defineProps({
	sections: { type: Array, default: () => [] },
	editable: { type: Boolean, default: false },
	title: { type: String, default: "Sections" },
	addLabel: { type: String, default: "+ Add section" },
	emptyHint: { type: String, default: "No sections yet." },
	purposeHint: { type: String, default: "" },
});
const emit = defineEmits(["update:sections"]);

const confirmDialog = useConfirm();
const newOpen = ref(false);
const draft = ref({ heading: "", template: "" });

// The template body is HTML; this box is plain text. DOMParser, not innerHTML — the parsed
// document is inert, so nothing in the markup runs or fetches.
function toPlainText(html) {
	if (!html || !html.includes("<")) return html || "";
	return new DOMParser().parseFromString(html, "text/html").body.textContent || "";
}

async function templateBody(id) {
	try {
		const res = await frappeRequest({
			url: "frappe.client.get_value",
			params: { doctype: "Terms and Conditions", filters: id, fieldname: "terms" },
		});
		return toPlainText(res?.terms);
	} catch {
		return ""; // an unreadable template leaves the section blank rather than failing
	}
}

async function addSection() {
	const id = draft.value.template;
	emit("update:sections", [
		...props.sections,
		{
			heading: draft.value.heading.trim() || id || "New section",
			template: id || null,
			text: id ? await templateBody(id) : "",
		},
	]);
	draft.value = { heading: "", template: "" };
	newOpen.value = false;
}

function patch(i, p) {
	emit(
		"update:sections",
		props.sections.map((s, n) => (n === i ? { ...s, ...p } : s))
	);
}

function remove(i) {
	emit(
		"update:sections",
		props.sections.filter((_, n) => n !== i)
	);
}

// Pulling in a clause replaces the body, so it asks before overwriting typed text.
async function swapTemplate(i, id) {
	const body = await templateBody(id);
	const current = props.sections[i];
	if (current?.text && current.text !== body) {
		const ok = await confirmDialog({
			title: "Replace this section's text",
			message: `Pulling in "${id}" overwrites what is in this section now.`,
			confirmLabel: "Replace",
		});
		if (!ok) return;
	}
	patch(i, { template: id, text: body, heading: current?.heading || id });
}
</script>

<template>
	<div class="space-y-3">
		<div class="flex items-center justify-between">
			<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
				{{ title }}
				<span class="text-ink-400 normal-case tracking-normal">
					· {{ sections.length }} section{{ sections.length === 1 ? "" : "s" }}
				</span>
			</div>
			<button v-if="editable" type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 text-ink-700 hover:bg-ink-50"
				style="border-radius: 6px" @click="newOpen = !newOpen">
				{{ addLabel }}
			</button>
		</div>

		<div v-if="newOpen && editable" class="border border-brand-200 bg-brand-50 p-3 space-y-2"
			style="border-radius: 8px">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
				<label class="block">
					<span class="text-[10px] uppercase tracking-wider text-ink-600 font-medium">
						Start from a template
					</span>
					<DeskLinkPicker v-model="draft.template" doctype="Terms and Conditions"
						placeholder="Blank section" />
				</label>
				<label class="block">
					<span class="text-[10px] uppercase tracking-wider text-ink-600 font-medium">
						Heading
					</span>
					<DeskInput v-model="draft.heading"
						placeholder="Takes the template's name if left blank" />
				</label>
			</div>
			<div class="flex justify-end gap-2">
				<button type="button"
					class="text-xs px-2.5 py-1 border border-ink-200 bg-white text-ink-700 hover:bg-ink-50"
					style="border-radius: 6px" @click="newOpen = false">
					Cancel
				</button>
				<button type="button" class="desk-save-btn" @click="addSection">Add section</button>
			</div>
		</div>

		<div v-for="(s, i) in sections" :key="s.name || i" class="border border-ink-200 overflow-hidden"
			style="border-radius: 8px">
			<header class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between gap-2">
				<DeskInput v-if="editable" :model-value="s.heading"
					class="!w-auto flex-1 !text-sm !font-medium"
					@change="(e) => patch(i, { heading: e.target.value })" />
				<div v-else class="text-sm font-medium text-ink-900">{{ s.heading }}</div>
				<div class="flex items-center gap-2 shrink-0">
					<span class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600 rounded-full">
						{{ s.template ? "Template" : "Manual" }}
					</span>
					<button v-if="editable" type="button" class="text-ink-400 hover:text-danger-700 px-1"
						title="Remove section" @click="remove(i)">
						×
					</button>
				</div>
			</header>
			<div class="p-4 space-y-2">
				<div v-if="editable" class="max-w-md">
					<DeskLinkPicker :model-value="s.template" doctype="Terms and Conditions"
						placeholder="Pull in a different clause…"
						@update:model-value="(v) => (v ? swapTemplate(i, v) : patch(i, { template: null }))" />
				</div>
				<DeskTextarea v-if="editable" :model-value="s.text" :rows="6"
					@change="(e) => patch(i, { text: e.target.value })" />
				<p v-else class="text-sm text-ink-700 whitespace-pre-line leading-relaxed">
					{{ s.text || "—" }}
				</p>
			</div>
		</div>

		<p v-if="!sections.length"
			class="text-sm text-ink-400 border border-dashed border-ink-200 px-4 py-6 text-center"
			style="border-radius: 8px">
			{{ emptyHint }}
			<span v-if="purposeHint" class="block text-[11px] text-ink-400 mt-1">{{ purposeHint }}</span>
		</p>
	</div>
</template>
