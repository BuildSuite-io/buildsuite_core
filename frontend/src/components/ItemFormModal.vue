<script setup>
// New / Edit Item. One modal, two modes — a null `item` means create.

import { computed, ref, watch } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import { showToast } from "@/utils/appToast";
import { fmtINR } from "@/utils/format";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	// A list row — it carries every field the form needs, so no extra fetch.
	item: { type: Object, default: null },
});
const emit = defineEmits(["close", "saved"]);

const adapter = createDataAdapter(useDataStore());
const confirmDialog = useConfirm();
const { canEdit, canDelete, canCreate } = usePermissions();
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
	item_code: "item_code",
	item_group: "item_group",
	stock_uom: "stock_uom",
});

function blank() {
	return {
		item_code: "",
		item_name: "",
		item_group: "",
		stock_uom: "",
		standard_rate: "",
		custom_rate_master: "",
		disabled: false,
	};
}

const saving = ref(false);
const form = ref(blank());
const editing = computed(() => !!props.item?.name);
const canSaveForm = computed(() => (editing.value ? canEdit("item") : canCreate("item")));

// Same options block and cache key as the estimation views — frappe-ui dedupes
// on the key, so this adds no request.
const rateMastersRes = useDocTypeList("Construction Rate Master", {
	fields: ["name", "rate_name", "category", "current_rate", "uom"],
	filters: [["disabled", "=", 0]],
	orderBy: "category asc",
	pageLength: 0,
	cache: "buildsuite-rate-master-options",
});

const rateMasterOptions = computed(() =>
	(rateMastersRes.data || []).map((r) => ({
		value: r.name,
		label: `${r.name} · ${r.rate_name}`,
		group: r.category,
		hint: `${fmtINR(r.current_rate)} per ${r.uom}`,
	}))
);

const linkedRate = computed(() =>
	(rateMastersRes.data || []).find((r) => r.name === form.value.custom_rate_master)
);

// api/procurement.py compares a PO rate against the Rate Master rate with no UOM
// check, so a per-bag item linked to a per-kg rate makes that check meaningless.
const uomMismatch = computed(
	() =>
		!!linkedRate.value?.uom &&
		!!form.value.stock_uom &&
		linkedRate.value.uom.trim() !== form.value.stock_uom.trim()
);

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return;
		setErrors({});
		const row = props.item;
		form.value = row
			? {
					item_code: row.name || "",
					item_name: row.item_name || "",
					item_group: row.item_group || "",
					stock_uom: row.stock_uom || "",
					standard_rate: row.standard_rate ?? "",
					custom_rate_master: row.custom_rate_master || "",
					disabled: !!row.disabled,
			  }
			: blank();
	},
	{ immediate: true }
);

// A courtesy only — the server owns the real rules. It does not reject a
// negative standard_rate, though, so that check is the only guard there is.
function validate() {
	const f = form.value;
	const e = {};
	if (!f.item_code.trim()) e.item_code = "Item code is required.";
	if (!f.item_group) e.item_group = "Item group is required.";
	if (!f.stock_uom) e.stock_uom = "UOM is required.";
	if (Number(f.standard_rate) < 0) e.standard_rate = "Standard rate cannot be negative.";
	setErrors(e);
	return Object.keys(e).length === 0;
}

function payload() {
	return {
		// Left blank, ERPNext copies item_code into item_name on validate.
		item_name: form.value.item_name.trim(),
		item_group: form.value.item_group,
		stock_uom: form.value.stock_uom,
		standard_rate: Number(form.value.standard_rate) || 0,
		custom_rate_master: form.value.custom_rate_master || "",
		disabled: form.value.disabled ? 1 : 0,
	};
}

async function save() {
	if (!validate()) return;
	saving.value = true;
	try {
		if (editing.value) {
			await adapter.update("Item", props.item.name, payload());
		} else {
			// A duplicate code fails server-side; no point pre-checking and racing.
			await adapter.create("Item", { item_code: form.value.item_code.trim(), ...payload() });
		}
		showToast(editing.value ? "Item updated" : "Item created");
		emit("saved");
		emit("close");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to save the item", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: "Delete item?",
		// Not the demo's wording: there an item is a plain string on each line, here
		// item_code is a Link, so Frappe raises LinkExistsError instead of deleting.
		message: `Delete "${
			props.item.item_name || props.item.name
		}" from the item master? An item already used on an MR, PO or receipt cannot be deleted — disable it instead.`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Item", props.item.name);
		showToast("Item deleted");
		emit("saved");
		emit("close");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete the item", "error");
	}
}
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
				<header
					class="px-5 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">
						{{ editing ? "Edit Item" : "New Item" }}
					</h2>
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 text-lg leading-none"
						aria-label="Close"
						@click="emit('close')"
					>
						×
					</button>
				</header>

				<div class="p-5 space-y-3 overflow-y-auto min-h-0">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						<DeskField
							label="Item code"
							required
							:error="errors.item_code"
							:hint="
								editing ? 'The code is the item id — it cannot be changed.' : ''
							"
						>
							<DeskInput
								v-model="form.item_code"
								class="font-mono"
								:disabled="editing"
								placeholder="e.g. CEM-OPC53"
								@input="clearError('item_code')"
							/>
						</DeskField>
						<DeskField label="Item name">
							<DeskInput
								v-model="form.item_name"
								placeholder="Cement — OPC 53 Grade"
							/>
						</DeskField>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						<DeskField label="Item group" required :error="errors.item_group">
							<DeskLinkPicker
								v-model="form.item_group"
								doctype="Item Group"
								label-field="name"
								value-field="name"
								placeholder="— Select group —"
								@change="clearError('item_group')"
							/>
						</DeskField>
						<DeskField label="UOM" required :error="errors.stock_uom">
							<DeskLinkPicker
								v-model="form.stock_uom"
								doctype="UOM"
								label-field="name"
								value-field="name"
								placeholder="— Select UOM —"
								@change="clearError('stock_uom')"
							/>
						</DeskField>
					</div>

					<DeskField
						label="Standard rate (₹)"
						:error="errors.standard_rate"
						hint="Default rate pre-filled on MR / PO lines — editable per document."
					>
						<DeskInput
							v-model="form.standard_rate"
							type="number"
							min="0"
							@input="clearError('standard_rate')"
						/>
					</DeskField>

					<DeskField
						label="Rate Master"
						hint="Links this item to the QS price book, so purchase lines can check their rate against it."
					>
						<DeskSearchableSelect
							v-model="form.custom_rate_master"
							:options="rateMasterOptions"
							placeholder="Not linked"
							search-placeholder="Search rate codes, descriptions…"
							allow-clear
						/>
					</DeskField>

					<p
						v-if="uomMismatch"
						class="text-[11px] text-warning-700 bg-warning-50 border border-warning-200 px-2.5 py-2 -mt-1"
						style="border-radius: 6px"
					>
						Unit mismatch — this item is <strong>{{ form.stock_uom }}</strong> but the
						rate is per <strong>{{ linkedRate.uom }}</strong
						>. The rate check compares the two figures directly, so the link does
						nothing until the units match.
					</p>

					<label class="flex items-center gap-2 text-sm text-ink-700">
						<input v-model="form.disabled" type="checkbox" />
						Disabled (hidden from pickers)
					</label>
				</div>

				<footer
					class="px-5 py-3 border-t border-ink-200 flex items-center justify-between gap-2"
				>
					<button
						v-if="editing && canDelete('item')"
						type="button"
						class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
						style="border-radius: 6px"
						@click="onDelete"
					>
						Delete
					</button>
					<span v-else></span>

					<div class="flex items-center gap-2">
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							@click="emit('close')"
						>
							Cancel
						</button>
						<button
							type="button"
							class="desk-save-btn !text-xs"
							:disabled="saving || !canSaveForm"
							@click="save"
						>
							{{ saving ? "Saving…" : editing ? "Save changes" : "Create item" }}
						</button>
					</div>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
