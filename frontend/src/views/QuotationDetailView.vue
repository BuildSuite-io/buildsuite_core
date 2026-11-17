<script setup>
import { computed, defineAsyncComponent, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import ExtensionSlot from "@/components/ExtensionSlot.vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useConfirm } from "@/composables/useConfirm";
import { usePageTitle } from "@/composables/usePageTitle";
import { showToast } from "@/utils/appToast";
import { fmtCurrency, fmtDate, daysBetween } from "@/utils/format";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import OfferPaymentTerms from "@/components/OfferPaymentTerms.vue";
import QuotationLostModal from "@/components/QuotationLostModal.vue";
import { usePermissions } from "@/composables/usePermissions";
import { offerStatus } from "@/data/offerStatus";
import { acceptQuotation, rejectQuotation, sendQuotation } from "@/data/quotationApi";
import { convertLead } from "@/data/leadsApi";
// Rich text (Text Editor) is heavy (TipTap) — load it only when a quotation is opened.
const RichTextEditor = defineAsyncComponent(() => import("@/components/RichTextEditor.vue"));

const props = defineProps({ id: String });
const adapter = createDataAdapter(useDataStore());
const router = useRouter();
const confirmDialog = useConfirm();

// The id can change without the component being torn down (one quotation linking to another),
// so the read follows the id rather than being taken once in setup().
const resource = ref(null);
watch(
	() => props.id,
	(id) => (resource.value = adapter.read("Quotation", id)),
	{
		immediate: true,
	}
);

const doc = computed(() => resource.value?.doc || null);

const offer = computed(() => offerStatus(doc.value));
const isDraft = computed(() => doc.value?.docstatus === 0);
// Still with the client: sent, not yet accepted or rejected.
const isOut = computed(() => offer.value === "Sent");
const { canEdit, canSubmit, canCreate } = usePermissions();

// ERPNext fills `customer_name` for a lead too (its organisation, else the person), so it is the
// name to show whoever the quotation went to; `party_name` is the record id.
const subtitle = computed(() =>
	[props.id, doc.value?.customer_name || doc.value?.party_name, doc.value?.customer_type]
		.filter(Boolean)
		.join(" · ")
);

// A quotation to a lead names the lead; once it is won, the customer it became.
const leadResource = ref(null);
const customerOfLead = ref(null);
watch(
	() => [doc.value?.quotation_to, doc.value?.party_name],
	([to, party]) => {
		leadResource.value = null;
		customerOfLead.value = null;
		if (to !== "Lead" || !party) return;
		leadResource.value = adapter.list("Lead", {
			fields: ["name", "lead_name", "mobile_no", "status"],
			filters: [["name", "=", party]],
			pageLength: 1,
		});
		customerOfLead.value = adapter.list("Customer", {
			fields: ["name", "customer_name"],
			filters: [["lead_name", "=", party]],
			pageLength: 1,
		});
	},
	{ immediate: true }
);
const firstRow = (r) => {
	const raw = r?.data;
	const rows = Array.isArray(raw) ? raw : Array.isArray(raw?.value) ? raw.value : [];
	return rows[0] || null;
};
const lead = computed(() => firstRow(leadResource.value));
const leadCustomer = computed(() => firstRow(customerOfLead.value));

async function act(fn, done) {
	busy.value = true;
	try {
		const res = await fn();
		await resource.value?.reload?.();
		leadResource.value?.reload?.();
		customerOfLead.value?.reload?.();
		if (done) showToast(done(res), "success");
	} catch (err) {
		showToast(err.message || __("That did not work."), "error");
	} finally {
		busy.value = false;
	}
}
const onSend = async () => {
	const ok = await confirmDialog({
		title: __("Send {0}?", [props.id]),
		message: __("It can no longer be edited once it is sent."),
		confirmLabel: __("Send"),
	});
	if (ok)
		act(
			() => sendQuotation(props.id),
			() => __("Sent.")
		);
};
const onAccept = async () => {
	const ok = await confirmDialog({
		title: __("Mark {0} as accepted?", [props.id]),
		message:
			doc.value.quotation_to === "Lead"
				? __(
						"The client said yes. The lead becomes a customer, which is what the project and the invoices are raised against."
				  )
				: __("The client said yes."),
		confirmLabel: __("Accepted"),
	});
	if (ok)
		act(
			() => acceptQuotation(props.id),
			(r) => (r.customer ? __("Accepted. Customer {0}.", [r.customer]) : __("Accepted."))
		);
};
const onConvert = () =>
	act(
		() => convertLead(doc.value.party_name),
		(r) => __("Customer {0}.", [r.customer])
	);
const lostOpen = ref(false);
function onReject(lost) {
	act(
		() => rejectQuotation(props.id, lost),
		() => __("Marked as rejected.")
	).then(() => (lostOpen.value = false));
}

// Counted from today: what is left is the number worth acting on.
const daysLeft = computed(() => {
	const validTill = doc.value?.valid_till;
	if (!validTill) return null;
	return daysBetween(new Date().toISOString().slice(0, 10), validTill);
});

const validityNote = computed(() => {
	const n = daysLeft.value;
	if (n === null) return "";
	if (n < 0) {
		const d = -n;
		return d === 1 ? __("expired {0} day ago", [d]) : __("expired {0} days ago", [d]);
	}
	if (n === 0) return __("expires today");
	return n === 1 ? __("{0} day left", [n]) : __("{0} days left", [n]);
});

const lines = computed(() => doc.value?.items || []);

// A line saved before the margin change has a rate and no cost; its rate IS the cost.
const lineCost = (l) => Number(l.price_list_rate) || Number(l.rate) || 0;

// Margin is the DIFFERENCE rather than a stored figure, so it can never disagree with the rows
// above by a rounding step.
const cost = computed(() =>
	lines.value.reduce((a, l) => a + (Number(l.qty) || 0) * lineCost(l), 0)
);
const margin = computed(() => (Number(doc.value?.net_total) || 0) - cost.value);

const marginPct = computed(() => Number(lines.value[0]?.margin_rate_or_amount) || 0);
// A margin of nothing has no sell rate worth a column — the rate IS the rate.
const hasMargin = computed(() => marginPct.value !== 0);
// Source · Description · Unit · Qty · Rate [· Sell rate] · Amount
const cols = computed(() => 6 + (hasMargin.value ? 1 : 0));

const lineCount = computed(() => {
	const n = lines.value.length;
	return n === 1 ? __("{0} line", [n]) : __("{0} lines", [n]);
});

const busy = ref(false);

// The payment schedule saves as each change is made — like the tender page.
async function persist(values) {
	try {
		await adapter.update("Quotation", props.id, values);
		await resource.value?.reload?.();
	} catch (err) {
		showToast(err.message || __("Could not update the payment schedule"), "error");
	}
}

// What an installed app's components get on this page (slots detail.Quotation.*): the saved
// document, and a way to save fields on it and reload.
async function extPersist(values) {
	try {
		await adapter.update("Quotation", props.id, values);
		await resource.value?.reload?.();
	} catch (err) {
		showToast(err.message || __("Could not update the quotation"), "error");
		throw err;
	}
}
const extContext = computed(() => ({
	doctype: "Quotation",
	doc: doc.value,
	persist: extPersist,
	reload: () => resource.value?.reload?.(),
}));

async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete {0}?", [props.id]),
		message: __("This cannot be undone."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		await adapter.remove("Quotation", props.id);
		router.push("/quotations");
	} catch (err) {
		showToast(err.message || __("Could not delete the quotation"), "error");
	} finally {
		busy.value = false;
	}
}

usePageTitle(() => doc.value?.title || props.id);

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Estimation"), to: "/estimation" },
	{ label: __("Quotations"), to: "/quotations" },
	{ label: props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.title || id"
		:subtitle="subtitle"
		:status="offer"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="isDraft && canSubmit('quotation')"
				type="button"
				class="desk-save-btn"
				:disabled="busy"
				@click="onSend"
			>
				{{ __("Send") }}
			</button>
			<template v-if="isOut && canEdit('quotation')">
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
					style="border-radius: 6px"
					:disabled="busy"
					@click="lostOpen = true"
				>
					{{ __("Rejected") }}
				</button>
				<button type="button" class="desk-save-btn" :disabled="busy" @click="onAccept">
					{{ __("Accepted") }}
				</button>
			</template>
			<RouterLink
				:to="`/quotations/${encodeURIComponent(id)}/print`"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
			>
				{{ __("Print / PDF") }}
			</RouterLink>
			<RouterLink
				v-if="isDraft"
				:to="`/quotations/${encodeURIComponent(id)}/edit`"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
			>
				{{ __("Edit") }}
			</RouterLink>
			<button
				v-if="isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onDelete"
			>
				{{ __("Delete") }}
			</button>
		</template>

		<!-- Who it went to, when that is a lead. -->
		<div
			v-if="doc.quotation_to === 'Lead' && lead"
			class="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink-700"
		>
			<span
				class="text-[10px] uppercase tracking-wider font-semibold px-1.5 py-0.5 bg-info-50 text-info-700"
				style="border-radius: 4px"
				>{{ __("Lead") }}</span
			>
			<RouterLink :to="`/leads/${encodeURIComponent(lead.name)}`" class="desk-link">{{
				lead.lead_name
			}}</RouterLink>
			<span v-if="lead.mobile_no" class="text-ink-500 tabular-nums"
				>· {{ lead.mobile_no }}</span
			>
			<StatusBadge :status="lead.status" size="xs" />
			<span v-if="leadCustomer" class="text-success-700">
				· {{ __("now customer {0}", [leadCustomer.customer_name || leadCustomer.name]) }}
			</span>
		</div>
		<div
			v-if="offer === 'Accepted' && doc.quotation_to === 'Lead' && lead && !leadCustomer"
			class="mb-3 bg-warning-50 border border-warning-200 px-3 py-2.5 flex items-center justify-between gap-3"
			style="border-radius: 6px"
		>
			<div class="text-xs text-warning-700">
				{{
					__(
						"Won, but {0} is still a lead. The project and the invoices need a customer.",
						[lead.lead_name]
					)
				}}
				<span v-if="!canCreate('customer')" class="text-ink-600">{{
					__("Ask someone who can create customers to convert the lead.")
				}}</span>
			</div>
			<button
				v-if="canCreate('customer')"
				type="button"
				class="desk-save-btn text-xs shrink-0"
				:disabled="busy"
				@click="onConvert"
			>
				{{ __("Convert to customer") }}
			</button>
		</div>
		<div
			v-if="
				doc.docstatus === 1 &&
				offer === 'Rejected' &&
				(doc.lost_reasons?.length || doc.order_lost_reason)
			"
			class="mb-3 bg-danger-50 border border-danger-200 px-4 py-3"
			style="border-radius: 8px"
			data-lost
		>
			<div class="text-[10px] uppercase tracking-wider text-danger-700 font-semibold mb-1.5">
				{{ __("Lost") }}
			</div>
			<div v-if="doc.lost_reasons?.length" class="flex flex-wrap gap-1.5 mb-1.5">
				<span
					v-for="r in doc.lost_reasons"
					:key="r.lost_reason"
					class="text-xs px-2 py-0.5 bg-white border border-danger-200 text-danger-700"
					style="border-radius: 9999px"
					>{{ r.lost_reason }}</span
				>
			</div>
			<div v-if="doc.competitors?.length" class="text-xs text-ink-700">
				{{ __("Lost to") }} {{ doc.competitors.map((c) => c.competitor).join(", ") }}
			</div>
			<p v-if="doc.order_lost_reason" class="text-sm text-ink-800 mt-1 whitespace-pre-line">
				{{ doc.order_lost_reason }}
			</p>
		</div>
		<QuotationLostModal
			:open="lostOpen"
			:title="`${id} · ${doc.customer_name || doc.party_name}`"
			:saving="busy"
			@close="lostOpen = false"
			@confirm="onReject"
		/>

		<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Issued") }}
				</div>
				<div class="text-sm font-medium text-ink-900">
					{{ doc.transaction_date ? fmtDate(doc.transaction_date) : "—" }}
				</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Valid to") }}
				</div>
				<div class="text-sm font-medium text-ink-900">
					{{ doc.valid_till ? fmtDate(doc.valid_till) : "—" }}
				</div>
				<div
					v-if="validityNote"
					class="text-[10px]"
					:class="daysLeft < 0 ? 'text-warning-700' : 'text-ink-500'"
				>
					{{ validityNote }}
				</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Value") }}
				</div>
				<div class="text-sm font-semibold text-ink-900 tabular-nums">
					{{ fmtCurrency(doc.grand_total, doc.currency) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("incl. tax") }}</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Prepared by") }}
				</div>
				<div class="text-sm text-ink-900 truncate">{{ doc.owner || "—" }}</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Project") }}
				</div>
				<RouterLink
					v-if="doc.project"
					:to="`/projects/${encodeURIComponent(doc.project)}`"
					class="text-sm text-brand-700 hover:underline"
				>
					{{ doc.project }}
				</RouterLink>
				<div v-else class="text-sm text-ink-400">{{ __("Not linked yet") }}</div>
			</div>
		</div>

		<ExtensionSlot name="detail.Quotation.before.lines" :context="extContext" />
		<div class="text-xs text-ink-500 mb-2">{{ lineCount }}</div>

		<div class="border border-ink-200 overflow-hidden" style="border-radius: 8px">
			<div class="overflow-x-auto">
				<table class="w-full text-sm" style="min-width: 760px">
					<thead>
						<tr
							class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
						>
							<th class="text-left font-medium px-3 py-2 w-24">
								{{ __("Source") }}
							</th>
							<th class="text-left font-medium px-3 py-2">
								{{ __("Description") }}
							</th>
							<th class="text-left font-medium px-3 py-2 w-28">{{ __("Unit") }}</th>
							<th class="text-right font-medium px-3 py-2 w-28">{{ __("Qty") }}</th>
							<th class="text-right font-medium px-3 py-2 w-32">{{ __("Rate") }}</th>
							<th v-if="hasMargin" class="text-right font-medium px-3 py-2 w-32">
								{{ __("Sell rate") }}
								<span
									class="block normal-case tracking-normal text-[10px] text-ink-400 font-normal"
								>
									+{{ marginPct }}% {{ __("margin") }}
								</span>
							</th>
							<th class="text-right font-medium px-3 py-2 w-36">
								{{ __("Amount") }}
							</th>
						</tr>
					</thead>

					<tbody>
						<tr
							v-for="(l, i) in lines"
							:key="l.name || i"
							class="border-b border-ink-100"
						>
							<td class="px-3 py-2">
								<StatusBadge :status="l.source" size="xs" />
							</td>
							<td class="px-3 py-2">
								<div class="text-ink-900">{{ l.item_name }}</div>
								<div
									v-if="l.code || l.source_ref"
									class="text-[10px] font-mono text-ink-500"
								>
									{{ [l.code, l.source_ref].filter(Boolean).join(" · ") }}
								</div>
							</td>
							<td class="px-3 py-2 text-ink-700">{{ l.uom }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ l.qty }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ fmtCurrency(lineCost(l), doc.currency) }}
							</td>
							<td
								v-if="hasMargin"
								class="px-3 py-2 text-right tabular-nums text-ink-600"
							>
								{{ fmtCurrency(l.rate, doc.currency) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ fmtCurrency(l.amount, doc.currency) }}
							</td>
						</tr>

						<tr v-if="!lines.length">
							<td :colspan="cols" class="px-3 py-6 text-center text-ink-500 text-xs">
								{{ __("No lines on this quotation.") }}
							</td>
						</tr>
					</tbody>

					<tfoot>
						<tr v-if="lines.length" class="border-t-2 border-ink-200 bg-ink-50">
							<td
								:colspan="cols - 1"
								class="px-3 py-2 text-right text-[11px] font-semibold text-ink-600 uppercase tracking-wider"
							>
								{{ __("Price before tax") }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
							>
								{{ fmtCurrency(doc.net_total, doc.currency) }}
							</td>
						</tr>
						<tr v-if="lines.length && hasMargin">
							<td
								:colspan="cols"
								class="px-3 pb-3 pt-1 text-right text-[10px] uppercase tracking-wider text-ink-500"
							>
								{{ __("of which cost") }} {{ fmtCurrency(cost, doc.currency) }} ·
								{{ __("margin") }} {{ fmtCurrency(margin, doc.currency) }}
							</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</div>

		<ExtensionSlot name="detail.Quotation.after.lines" :context="extContext" />

		<OfferPaymentTerms
			v-if="doc"
			:doc="doc"
			kind="Quotation"
			:base="Number(doc.net_total) || 0"
			:currency="doc.currency"
			class="mt-4"
			:class="isDraft ? '' : 'opacity-70'"
			:inert="!isDraft"
			@save="persist"
		/>

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
			<div
				class="lg:col-span-2 border border-ink-200 overflow-hidden"
				style="border-radius: 8px"
			>
				<header
					class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between"
				>
					<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
						{{ __("Terms & conditions") }}
					</div>
					<span
						class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600"
						style="border-radius: 9999px"
					>
						{{ doc.tc_name ? __("Template") : __("Manual") }}
					</span>
				</header>
				<div class="p-4">
					<RichTextEditor
						v-if="doc.terms"
						:model-value="doc.terms"
						:editable="false"
						min-height="auto"
					/>
					<p v-else class="text-sm text-ink-400">{{ __("No terms recorded.") }}</p>
				</div>
			</div>

			<div
				class="border border-ink-200 overflow-hidden self-start"
				style="border-radius: 8px"
			>
				<header
					class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100"
				>
					<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
						{{ __("Pricing") }}
					</div>
				</header>
				<div class="p-4 space-y-2 text-sm">
					<!-- Each row says how the one under it was reached, so a zero margin still shows. -->
					<div class="flex justify-between">
						<span class="text-ink-600">{{ __("Subtotal") }}</span>
						<span class="tabular-nums text-ink-900">{{
							fmtCurrency(cost, doc.currency)
						}}</span>
					</div>
					<div class="flex justify-between">
						<span class="text-ink-600">{{ __("Margin {0}%", [marginPct]) }}</span>
						<span class="tabular-nums text-ink-900">{{
							fmtCurrency(margin, doc.currency)
						}}</span>
					</div>
					<div class="flex justify-between border-t border-ink-100 pt-2">
						<span class="text-ink-600">{{ __("Price before tax") }}</span>
						<span class="tabular-nums text-ink-900">
							{{ fmtCurrency(doc.net_total, doc.currency) }}
						</span>
					</div>
					<div v-if="doc.taxes?.length" class="flex justify-between">
						<span class="text-ink-600">{{ __("Tax") }}</span>
						<span class="tabular-nums text-ink-900">
							{{ fmtCurrency(doc.total_taxes_and_charges, doc.currency) }}
						</span>
					</div>
					<div class="flex justify-between border-t border-ink-200 pt-2 font-semibold">
						<span class="text-ink-900">{{ __("Total") }}</span>
						<span class="tabular-nums text-ink-900">
							{{ fmtCurrency(doc.grand_total, doc.currency) }}
						</span>
					</div>
				</div>
			</div>
		</div>
		<div
			v-if="doc.internal_note"
			class="mt-4 bg-ink-50 border border-ink-200 px-4 py-3"
			style="border-radius: 8px"
		>
			<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">
				{{ __("Internal note — not printed") }}
			</div>
			<p class="text-sm text-ink-700 whitespace-pre-line">{{ doc.internal_note }}</p>
		</div>
	</DeskPage>

	<DeskPage
		v-else-if="resource?.doc === null"
		:title="__('Quotation not found')"
		:breadcrumbs="breadcrumbs"
	>
		<p class="text-sm text-ink-600">
			{{ __("No quotation with that id.") }}
			<RouterLink to="/quotations" class="desk-link">{{
				__("Back to the register →")
			}}</RouterLink>
		</p>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">{{ __("Loading quotation…") }}</div>
</template>
