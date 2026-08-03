<script setup>
// Trade field — a searchable Construction Trade picker with an inline "+ New" that creates a
// trade on the spot (saved permanently) and selects it, so a subcontractor's trade can be added
// without leaving the form. Construction Trade is autonamed field:trade_name.
import { ref } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { showToast } from "@/utils/appToast";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

defineProps({
	modelValue: { type: String, default: "" },
	error: { type: String, default: "" },
});
const emit = defineEmits(["update:modelValue"]);
const adapter = createDataAdapter(useDataStore());

const open = ref(false);
const name = ref("");
const saving = ref(false);
const pickerKey = ref(0); // bump to refresh the picker's options after creating a trade

function openCreate() {
	name.value = "";
	open.value = true;
}
async function createTrade() {
	const trade = name.value.trim();
	if (!trade) return;
	saving.value = true;
	try {
		const res = await adapter.create("Construction Trade", { trade_name: trade, enabled: 1 });
		emit("update:modelValue", res.name);
		pickerKey.value++;
		open.value = false;
		showToast(`Trade "${res.name}" created.`);
	} catch (err) {
		showToast(err.message || "Could not create the trade.", "error");
	} finally {
		saving.value = false;
	}
}
</script>

<template>
	<div class="flex items-center gap-2">
		<div class="flex-1 min-w-0">
			<DeskLinkPicker
				:key="pickerKey"
				:model-value="modelValue"
				doctype="Construction Trade"
				label-field="name"
				value-field="name"
				placeholder="Pick a trade…"
				:error="error"
				@update:model-value="(v) => emit('update:modelValue', v)"
			/>
		</div>
		<button
			type="button"
			class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-brand-700 rounded-md flex-shrink-0 whitespace-nowrap"
			title="Create a new trade"
			@click="openCreate"
		>
			+ New
		</button>
	</div>

	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-sm shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Create new trade</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4">
					<label
						class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
						>Trade name</label
					>
					<input
						v-model="name"
						type="text"
						placeholder="e.g. Waterproofing"
						class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						@keyup.enter="createTrade"
					/>
				</div>
				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="open = false"
					>
						Cancel
					</button>
					<button
						type="button"
						class="text-xs desk-save-btn"
						:disabled="saving || !name.trim()"
						@click="createTrade"
					>
						{{ saving ? "Creating…" : "Create trade" }}
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
