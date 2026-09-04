<script setup>
// Shared create/edit modal for a "party" (Customer or Supplier). Both masters
// share the same shape (name, type, contact, phone, email, tax id). The parent
// supplies the title + type options and persists via its own API call, so this
// component owns no data logic. Ported from the prototype (PartyFormModal).
import { ref, watch } from "vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	title: { type: String, default: "New party" },
	typeLabel: { type: String, default: "Type" },
	typeOptions: { type: Array, default: () => [] }, // string[]
	initial: { type: Object, default: null }, // for edit
	serverError: { type: String, default: "" }, // e.g. duplicate-name from the parent's save attempt
	canDelete: { type: Boolean, default: false }, // show Delete when editing an existing record
});
const emit = defineEmits(["save", "close", "delete"]);

const form = ref(blank());
const error = ref("");

function blank() {
	return { name: "", type: "", contactPerson: "", phone: "", email: "", gstin: "" };
}

watch(
	() => props.open,
	(o) => {
		if (o) {
			form.value = props.initial ? { ...blank(), ...props.initial } : blank();
			error.value = "";
		}
	}
);

function onSave() {
	const name = (form.value.name || "").trim();
	if (!name) {
		error.value = "Name is required.";
		return;
	}
	emit("save", { ...form.value, name });
}
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6"
			@click.self="emit('close')"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-lg shadow-xl flex flex-col"
				style="border-radius: 12px; max-height: 85vh"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0"
				>
					<h2 class="text-sm font-semibold text-ink-900">{{ title }}</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						aria-label="Close"
						@click="emit('close')"
					>
						✕
					</button>
				</header>

				<div class="px-4 py-4 overflow-y-auto flex-1 space-y-3">
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>Name <span class="text-danger-600">*</span></label
						>
						<input
							v-model="form.name"
							type="text"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							placeholder="Party name"
						/>
						<div v-if="error || serverError" class="text-[11px] text-danger-600 mt-1">
							{{ error || serverError }}
						</div>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>{{ typeLabel }}</label
						>
						<select
							v-model="form.type"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						>
							<option value="">—</option>
							<option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</option>
						</select>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Contact person</label
							>
							<input
								v-model="form.contactPerson"
								type="text"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
						</div>
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Phone</label
							>
							<input
								v-model="form.phone"
								type="text"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
						</div>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>Email</label
						>
						<input
							v-model="form.email"
							type="email"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						/>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>Tax ID</label
						>
						<input
							v-model="form.gstin"
							type="text"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 font-mono"
							placeholder="29AABC…1Z5"
						/>
					</div>
				</div>

				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center gap-2 flex-shrink-0"
				>
					<!-- Delete only when editing an existing record and the persona may delete. -->
					<button
						v-if="initial && canDelete"
						type="button"
						class="text-xs px-3 py-1.5 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700 rounded-md"
						@click="emit('delete')"
					>
						Delete
					</button>
					<div class="ml-auto flex items-center gap-2">
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
							@click="emit('close')"
						>
							Cancel
						</button>
						<button type="button" class="text-xs desk-save-btn" @click="onSave">
							Save
						</button>
					</div>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
