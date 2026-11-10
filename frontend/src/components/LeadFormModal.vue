<script setup>
// New lead — the enquiry before there is a customer. Opened from Sales › Leads and from the
// quotation form's "+ New lead". Saving creates an ERPNext Lead (status Lead, owned by whoever
// adds it) and emits `saved` with it; the Leads page then opens it, the quotation form picks it.
//
// The mobile is how the same person is found again: while it is typed, the leads and customers
// already on file with that number are shown (LeadMobileMatches). With `offerUse`, picking one
// emits `use` instead of adding a second record.
import { ref, watch } from "vue";
import { watchDebounced } from "@vueuse/core";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import LeadMobileMatches from "@/components/LeadMobileMatches.vue";
import { createLead, findMobileMatches } from "@/data/leadsApi";
import { mobileKey } from "@/data/leads";
import { __ } from "@/utils/translate";

const props = defineProps({
	open: { type: Boolean, default: false },
	offerUse: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "saved", "use"]);

const BLANK = {
	first_name: "",
	last_name: "",
	mobile_no: "",
	city: "",
	utm_source: "",
	company_name: "",
	enquiry_note: "",
};
const form = ref({ ...BLANK });
const error = ref("");
const serverError = ref("");
const saving = ref(false);
const matches = ref([]);
const firstInput = ref(null);

watch(
	() => props.open,
	(o) => {
		if (!o) return;
		form.value = { ...BLANK };
		error.value = "";
		serverError.value = "";
		saving.value = false;
		matches.value = [];
		// DeskInput's root may be the <input> itself or a wrapper around it.
		setTimeout(() => {
			const el = firstInput.value?.$el;
			(el?.tagName === "INPUT" ? el : el?.querySelector?.("input"))?.focus?.();
		}, 0);
	},
);

watchDebounced(
	() => form.value.mobile_no,
	async (mobile) => {
		if (!props.open || !mobileKey(mobile)) {
			matches.value = [];
			return;
		}
		try {
			matches.value = await findMobileMatches(mobile);
		} catch {
			matches.value = [];
		}
	},
	{ debounce: 300 },
);

async function save() {
	if (!form.value.first_name.trim() && !form.value.company_name.trim()) {
		error.value = __("A person's name, or an organisation's below.");
		return;
	}
	error.value = "";
	serverError.value = "";
	saving.value = true;
	try {
		const lead = await createLead(form.value);
		emit("saved", lead);
		emit("close");
	} catch (e) {
		serverError.value = e?.message || __("Could not add the lead.");
	} finally {
		saving.value = false;
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
				class="bg-white border border-ink-200 w-full max-w-lg shadow-fp-lg flex flex-col max-h-full"
				style="border-radius: 12px"
				role="dialog"
				aria-modal="true"
				:aria-label="__('New lead')"
				@click.stop
			>
				<header
					class="px-5 py-3 border-b border-ink-200 flex items-center justify-between bg-white"
					style="border-radius: 12px 12px 0 0"
				>
					<h2 class="text-sm font-semibold text-ink-900">{{ __("New lead") }}</h2>
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 text-lg leading-none"
						:aria-label="__('Close')"
						@click="emit('close')"
					>
						×
					</button>
				</header>

				<div class="p-5 space-y-3 overflow-y-auto">
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
						<DeskField
							:label="__('First name')"
							:required="!form.company_name.trim()"
							:error="error"
						>
							<DeskInput
								ref="firstInput"
								v-model="form.first_name"
								:placeholder="__('e.g. Shameer')"
							/>
						</DeskField>
						<DeskField :label="__('Last name')">
							<DeskInput
								v-model="form.last_name"
								:placeholder="__('e.g. Kunnath')"
							/>
						</DeskField>
					</div>

					<DeskField
						:label="__('Mobile')"
						:hint="__('How you reach them, and how the same person is found again.')"
					>
						<DeskInput
							v-model="form.mobile_no"
							type="tel"
							:placeholder="__('+91 98470 12345')"
						/>
					</DeskField>
					<LeadMobileMatches
						:matches="matches"
						:offer-use="offerUse"
						@use="(m) => emit('use', m)"
						@open="emit('close')"
					/>

					<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
						<DeskField :label="__('City / place')">
							<DeskInput v-model="form.city" :placeholder="__('e.g. Kottakkal')" />
						</DeskField>
						<DeskField :label="__('Source')">
							<DeskLinkPicker
								v-model="form.utm_source"
								doctype="UTM Source"
								placeholder="—"
							/>
						</DeskField>
					</div>

					<DeskField
						:label="__('Organisation')"
						:hint="__('Only for a business. Leave blank for a person or a family.')"
					>
						<DeskInput
							v-model="form.company_name"
							:placeholder="__('e.g. Siddiqui Textiles')"
						/>
					</DeskField>

					<DeskField :label="__('Notes')">
						<DeskTextarea
							v-model="form.enquiry_note"
							:rows="2"
							:placeholder="__('What they asked for')"
						/>
					</DeskField>

					<p v-if="serverError" class="text-xs text-danger-700">{{ serverError }}</p>
				</div>

				<footer
					class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 bg-white"
					style="border-radius: 0 0 12px 12px"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
						style="border-radius: 6px"
						@click="emit('close')"
					>
						{{ __("Cancel") }}
					</button>
					<button type="button" class="desk-save-btn" :disabled="saving" @click="save">
						{{ saving ? __("Adding…") : __("Add lead") }}
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
