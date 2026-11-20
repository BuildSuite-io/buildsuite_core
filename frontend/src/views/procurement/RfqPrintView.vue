<script setup>
// Request for Quotation — printable document, rendered from the Frappe Print Format (the
// company Letter Head + the "REQUEST FOR QUOTATION" title, as every other print). See
// ServerPrintDocument for the mechanism.
//
// One request goes to several suppliers, so the bar picks which supplier the copy is addressed
// to (?supplier=), and the page shows the email that would carry it and can send it.
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ServerPrintDocument from "@/components/ServerPrintDocument.vue";
import { usePermissions } from "@/composables/usePermissions";
import { getRfq, getRfqPrintHtml, sendRfqEmails, isEmail } from "@/data/rfqApi";
import { showToast } from "@/utils/appToast";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({ id: { type: String, required: true } });
const route = useRoute();
const router = useRouter();
const { canEdit } = usePermissions();

const rfq = ref(null);
const loadError = ref("");
const supplier = ref(route.query.supplier || "");
const sending = ref(false);

async function load() {
	loadError.value = "";
	try {
		rfq.value = await getRfq(props.id);
		if (!rfq.value.suppliers.some((s) => s.supplier === supplier.value))
			supplier.value = rfq.value.suppliers[0]?.supplier || "";
	} catch (err) {
		loadError.value = err.message || __("Failed to load request");
		showToast(loadError.value, "error");
	}
}
watch(() => props.id, load, { immediate: true });
// Keep the picked supplier in the URL, so a refresh or a shared link shows the same copy.
watch(supplier, (v) => {
	if (v !== (route.query.supplier || "")) router.replace({ query: v ? { supplier: v } : {} });
});

// A new function per supplier, so ServerPrintDocument re-renders the copy addressed to it. It
// depends on the request being loaded, not on its contents: sending an email replaces `rfq`, and
// that must not re-download the same copy.
const loaded = computed(() => !!rfq.value);
const loader = computed(() => {
	if (!loaded.value) return null;
	const name = props.id;
	const who = supplier.value;
	return () => getRfqPrintHtml(name, who);
});

const row = computed(
	() => rfq.value?.suppliers.find((s) => s.supplier === supplier.value) || null
);
const email = computed(() => (row.value ? rfq.value.email?.[row.value.supplier] || null : null));
const canSend = computed(
	() =>
		canEdit("rfq") &&
		rfq.value?.state === "Submitted" &&
		row.value &&
		isEmail(row.value.email_id)
);

async function send() {
	sending.value = true;
	try {
		const res = await sendRfqEmails(props.id, [row.value.supplier]);
		rfq.value = res.doc;
		showToast(__("Emailed to {0}.", [row.value.email_id]));
	} catch (err) {
		showToast(err.message || __("Could not send the email."), "error");
	} finally {
		sending.value = false;
	}
}
</script>

<template>
	<ServerPrintDocument
		v-if="loader"
		doctype="Request for Quotation"
		:name="props.id"
		:loader="loader"
		:back-to="`/procurement/rfqs/${props.id}`"
		:back-label="__('Back to request')"
	>
		<template #controls>
			<label
				v-if="rfq.suppliers.length"
				class="flex items-center gap-2 text-xs text-ink-500 ml-4"
			>
				{{ __("Addressed to") }}
				<select
					v-model="supplier"
					class="desk-input !py-1 !text-xs !w-56"
					data-test="rfq-print-supplier"
				>
					<option v-for="s in rfq.suppliers" :key="s.supplier" :value="s.supplier">
						{{ s.supplier_name }}
					</option>
				</select>
			</label>
		</template>
		<template #actions>
			<button
				v-if="canSend"
				class="text-xs px-3 py-1.5 rounded border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				:disabled="sending"
				data-test="rfq-print-send"
				@click="send"
			>
				{{ sending ? __("Sending…") : __("Send email") }}
			</button>
		</template>

		<template v-if="email" #above>
			<div class="border border-ink-200 rounded-lg text-xs" data-test="rfq-email-preview">
				<div
					class="bg-ink-50 border-b border-ink-200 px-4 py-2 text-[10px] uppercase tracking-wider text-ink-500 font-medium flex items-center justify-between"
				>
					<span>{{ __("Email preview") }}</span>
					<span v-if="row.email_sent" class="normal-case tracking-normal">{{
						__("Last sent {0}", [fmtDate(row.email_sent_at)])
					}}</span>
				</div>
				<div class="px-4 py-2 border-b border-ink-100">
					<span class="text-ink-500">{{ __("To:") }}</span>
					<span v-if="isEmail(email.to)" class="text-ink-900">
						{{ row.contact_person ? row.contact_person + " " : "" }}&lt;{{
							email.to
						}}&gt;</span
					>
					<span v-else class="text-warning-700">
						{{
							__(
								"No email address for this supplier. Add one on the request's page."
							)
						}}</span
					>
				</div>
				<div class="px-4 py-2 border-b border-ink-100 text-ink-900">
					<span class="text-ink-500">{{ __("Subject:") }}</span> {{ email.subject }}
				</div>
				<p class="px-4 py-3 text-ink-700 whitespace-pre-line">{{ email.body }}</p>
				<div class="px-4 py-2 border-t border-ink-100 text-ink-500">
					{{ __("Attachment: {0}.pdf, the document below", [rfq.name]) }}
				</div>
			</div>
			<p v-if="rfq.state !== 'Submitted'" class="text-xs text-ink-500 mt-2">
				{{ __("Submit the request to email it.") }}
			</p>
		</template>
	</ServerPrintDocument>
	<div v-else-if="loadError" class="p-8 text-sm text-ink-600">
		<p class="mb-3">{{ loadError }}</p>
		<router-link :to="`/procurement/rfqs/${props.id}`" class="text-brand-600 hover:underline">
			{{ __("Back to request") }}
		</router-link>
	</div>
</template>
