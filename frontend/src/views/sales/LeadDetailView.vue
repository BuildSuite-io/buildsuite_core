<script setup>
// Sales › Leads › one lead — the person, their organisation (only for a business), where they
// are, and the lead itself. Saved with an explicit Save; the status offers only what the rules
// allow (buildsuite_core.utils.lead): by hand until a quotation goes out, then it follows the
// quotations, and a converted lead's is fixed. The side panel lists its quotations and the
// customer it became.
import { computed, reactive, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { watchDebounced } from "@vueuse/core";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import FrappeUserBadge from "@/components/FrappeUserBadge.vue";
import LeadMobileMatches from "@/components/LeadMobileMatches.vue";
import { useConfirm } from "@/composables/useConfirm";
import { usePageTitle } from "@/composables/usePageTitle";
import { convertLead, deleteLead, findMobileMatches, getLead, updateLead } from "@/data/leadsApi";
import { leadStatusHint, leadStatusOptions, mobileKey } from "@/data/leads";
import { showToast } from "@/utils/appToast";
import { fmtCurrency, fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const confirmDialog = useConfirm();

const FIELDS = [
	"first_name",
	"last_name",
	"mobile_no",
	"email_id",
	"company_name",
	"city",
	"state",
	"utm_source",
	"lead_owner",
	"enquiry_note",
];

const data = ref(null); // getLead(): { lead, quotations, customer, mobile_matches, can }
const loading = ref(true);
const notFound = ref(false);
const saving = ref(false);
const form = reactive(Object.fromEntries([...FIELDS, "status"].map((f) => [f, ""])));
const matches = ref([]);
const nameError = ref("");

const lead = computed(() => data.value?.lead || null);
const can = computed(() => data.value?.can || {});
const quotations = computed(() => data.value?.quotations || []);
const customer = computed(() => data.value?.customer || null);

usePageTitle(() => lead.value?.lead_name || __("Lead"));

function fill(result) {
	data.value = result;
	for (const f of [...FIELDS, "status"]) form[f] = result.lead[f] ?? "";
	matches.value = result.mobile_matches || [];
	nameError.value = "";
}

async function load() {
	loading.value = true;
	notFound.value = false;
	try {
		fill(await getLead(props.id));
	} catch {
		notFound.value = true;
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const dirty = computed(
	() =>
		!!lead.value &&
		[...FIELDS, "status"].some((f) => (form[f] ?? "") !== (lead.value[f] ?? "")),
);
const statusOptions = computed(() => leadStatusOptions(lead.value));
const statusHint = computed(() => leadStatusHint(lead.value));

// Re-check the number as it is edited (the saved one's matches came with the lead).
watchDebounced(
	() => form.mobile_no,
	async (mobile) => {
		if (!lead.value || mobile === lead.value.mobile_no) {
			matches.value = data.value?.mobile_matches || [];
			return;
		}
		if (!mobileKey(mobile)) {
			matches.value = [];
			return;
		}
		try {
			matches.value = await findMobileMatches(mobile, props.id);
		} catch {
			matches.value = [];
		}
	},
	{ debounce: 300 },
);

async function onSave() {
	if (!String(form.first_name).trim() && !String(form.company_name).trim()) {
		nameError.value = __("A lead needs a person's name or an organisation's name.");
		return;
	}
	saving.value = true;
	const payload = Object.fromEntries(FIELDS.map((f) => [f, form[f] || ""]));
	if (form.status !== lead.value.status) payload.status = form.status;
	try {
		fill(await updateLead(props.id, payload));
		showToast(__("Saved."), "success");
	} catch (err) {
		showToast(err.message || __("Could not save the lead."), "error");
		form.status = lead.value.status;
	} finally {
		saving.value = false;
	}
}

function onCancel() {
	if (data.value) fill(data.value);
}

const canDelete = computed(() => can.value.delete && !quotations.value.length && !customer.value);
const canConvert = computed(() => can.value.convert && !customer.value);
const newQuotationTo = computed(() =>
	customer.value
		? `/quotations/new?customer=${encodeURIComponent(customer.value.name)}`
		: `/quotations/new?lead=${encodeURIComponent(props.id)}`,
);

async function onConvert() {
	const name = lead.value.company_name || lead.value.lead_name;
	const ok = await confirmDialog({
		title: __("Convert to customer"),
		message: __(
			"{0} becomes a customer{1}, with this mobile and email. If a customer already has this mobile number, the lead is linked to them instead.",
			[name, lead.value.company_name ? "" : ` (${__("Individual")})`],
		),
		confirmLabel: __("Convert"),
	});
	if (!ok) return;
	try {
		const out = await convertLead(props.id);
		showToast(
			out.linked
				? __("Linked to the existing customer {0} (same mobile number).", [
						out.customer_name,
					])
				: __("Customer {0} created.", [out.customer_name]),
			"success",
		);
		await load();
	} catch (err) {
		showToast(err.message || __("Could not convert the lead."), "error");
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete {0}?", [lead.value.lead_name]),
		message: __("This cannot be undone."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteLead(props.id);
		showToast(__("Lead deleted."), "success");
		router.push("/leads");
	} catch (err) {
		showToast(err.message || __("Could not delete the lead."), "error");
	}
}

const subtitle = computed(() => {
	if (!lead.value) return "";
	const l = lead.value;
	const who =
		l.company_name && l.company_name !== l.lead_name ? l.company_name : __("Individual");
	return [l.name, who, l.utm_source && __(l.utm_source)].filter(Boolean).join(" · ");
});

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Sales"), to: "/sales" },
	{ label: __("Leads"), to: "/leads" },
	{ label: lead.value?.lead_name || props.id },
]);

const secondaryBtn =
	"text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 disabled:opacity-50";
</script>

<template>
	<DeskPage
		v-if="lead"
		:title="lead.lead_name || lead.company_name || id"
		:subtitle="subtitle"
		:status="lead.status"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="canDelete"
				type="button"
				:class="secondaryBtn"
				style="border-radius: 6px"
				@click="onDelete"
			>
				{{ __("Delete") }}
			</button>
			<button
				v-if="canConvert"
				type="button"
				:class="secondaryBtn"
				style="border-radius: 6px"
				@click="onConvert"
			>
				{{ __("Convert to customer") }}
			</button>
			<RouterLink :to="newQuotationTo" class="desk-save-btn !text-xs">{{
				__("New quotation")
			}}</RouterLink>
		</template>

		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:can-save="!!can.write && dirty"
					:saving="saving"
					:show-save="!!can.write"
					:show-cancel="dirty"
					:save-label="__('Save')"
					:saving-label="__('Saving…')"
					@save="onSave"
					@cancel="onCancel"
				>
					<template #left>
						<span v-if="!can.write" class="text-xs text-ink-500">{{
							__("Read-only")
						}}</span>
					</template>
				</DeskActionBar>
			</template>

			<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
				<div class="lg:col-span-2 space-y-4">
					<DeskSection :title="__('Person')" :cols="2">
						<DeskField
							:label="__('First name')"
							:required="!String(form.company_name).trim()"
							:error="nameError"
						>
							<DeskInput v-model="form.first_name" :disabled="!can.write" />
						</DeskField>
						<DeskField :label="__('Last name')">
							<DeskInput v-model="form.last_name" :disabled="!can.write" />
						</DeskField>
						<DeskField
							:label="__('Mobile')"
							:hint="__('Finds the same person again.')"
						>
							<DeskInput
								v-model="form.mobile_no"
								type="tel"
								:disabled="!can.write"
							/>
						</DeskField>
						<DeskField :label="__('Email')">
							<DeskInput
								v-model="form.email_id"
								type="email"
								:disabled="!can.write"
							/>
						</DeskField>
						<div v-if="matches.length" class="md:col-span-2">
							<LeadMobileMatches
								:matches="matches"
								:heading="__('This number is also on file:')"
							/>
						</div>
					</DeskSection>

					<DeskSection :title="__('Organisation')" :cols="2">
						<DeskField
							:label="__('Organisation name')"
							:hint="
								__(
									'Only for a business. Blank for a person or a family. When set, quotations and the customer carry this name.',
								)
							"
						>
							<DeskInput v-model="form.company_name" :disabled="!can.write" />
						</DeskField>
					</DeskSection>

					<DeskSection :title="__('Address')" :cols="2">
						<DeskField :label="__('City / place')">
							<DeskInput v-model="form.city" :disabled="!can.write" />
						</DeskField>
						<DeskField :label="__('State')">
							<DeskInput v-model="form.state" :disabled="!can.write" />
						</DeskField>
					</DeskSection>

					<DeskSection :title="__('Lead')" :cols="2">
						<DeskField :label="__('Status')" :hint="__(statusHint)">
							<DeskSelect
								v-model="form.status"
								:disabled="!can.write || statusOptions.length < 2"
							>
								<option v-for="s in statusOptions" :key="s" :value="s">
									{{ __(s) }}
								</option>
							</DeskSelect>
						</DeskField>
						<DeskField :label="__('Source')">
							<DeskLinkPicker
								v-model="form.utm_source"
								doctype="UTM Source"
								placeholder="—"
								:disabled="!can.write"
							/>
						</DeskField>
						<DeskField :label="__('Lead owner')">
							<DeskLinkPicker
								v-model="form.lead_owner"
								doctype="User"
								label-field="full_name"
								:search-fields="['full_name', 'name']"
								:filters="[
									['enabled', '=', 1],
									['user_type', '=', 'System User'],
								]"
								placeholder="—"
								:disabled="!can.write"
							/>
						</DeskField>
						<DeskField :label="__('Created')">
							<DeskInput :model-value="fmtDate(lead.creation)" readonly disabled />
						</DeskField>
						<div class="md:col-span-2">
							<DeskField :label="__('Notes')">
								<DeskTextarea
									v-model="form.enquiry_note"
									:rows="3"
									:disabled="!can.write"
								/>
							</DeskField>
						</div>
					</DeskSection>
				</div>

				<aside class="lg:col-span-1 space-y-2">
					<div
						class="bg-white border border-ink-200 px-3 py-2"
						style="border-radius: 8px"
					>
						<div class="flex items-center justify-between mb-1">
							<span
								class="text-[10px] uppercase tracking-wider font-semibold text-ink-500"
							>
								{{ __("Quotations") }} {{ quotations.length }}
							</span>
							<RouterLink :to="newQuotationTo" class="desk-link text-xs">{{
								__("+ New")
							}}</RouterLink>
						</div>
						<ul v-if="quotations.length" class="divide-y divide-ink-100">
							<li v-for="q in quotations" :key="q.name" class="py-1.5">
								<div class="flex items-center gap-2">
									<RouterLink
										:to="`/quotations/${encodeURIComponent(q.name)}`"
										class="font-mono text-xs text-brand-700 hover:underline"
									>
										{{ q.name }}
									</RouterLink>
									<StatusBadge v-if="q.status" :status="q.status" size="xs" />
								</div>
								<div class="text-xs text-ink-700 truncate">
									{{ q.title || "—" }}
								</div>
								<div class="text-[11px] text-ink-500 tabular-nums">
									{{ fmtCurrency(q.grand_total, q.currency) }} ·
									{{ fmtDate(q.transaction_date) }}
								</div>
							</li>
						</ul>
						<p v-else class="text-xs text-ink-500">{{ __("None yet.") }}</p>
					</div>

					<div
						class="bg-white border border-ink-200 px-3 py-2"
						style="border-radius: 8px"
					>
						<div
							class="text-[10px] uppercase tracking-wider font-semibold text-ink-500 mb-1"
						>
							{{ __("Customer") }}
						</div>
						<template v-if="customer">
							<RouterLink to="/customers" class="desk-link text-sm">{{
								customer.customer_name
							}}</RouterLink>
							<div class="text-[11px] text-ink-500">
								{{ __("Converted {0}", [fmtDate(customer.creation)])
								}}{{
									customer.customer_type
										? ` · ${__(customer.customer_type)}`
										: ""
								}}
							</div>
						</template>
						<p v-else class="text-xs text-ink-500">
							{{ __("Not yet. Convert the lead when they accept a quotation.") }}
						</p>
					</div>

					<div
						class="bg-white border border-ink-200 px-3 py-2"
						style="border-radius: 8px"
					>
						<div
							class="text-[10px] uppercase tracking-wider font-semibold text-ink-500 mb-1"
						>
							{{ __("Lead owner") }}
						</div>
						<FrappeUserBadge v-if="lead.lead_owner" :user-id="lead.lead_owner" />
						<span v-else class="text-xs text-ink-500">—</span>
					</div>
				</aside>
			</div>
		</DeskForm>
	</DeskPage>

	<DeskPage
		v-else-if="notFound"
		:title="__('Lead not found')"
		:breadcrumbs="[{ label: __('Leads'), to: '/leads' }]"
	>
		<RouterLink to="/leads" class="desk-link text-sm">{{ __("Back to Leads") }}</RouterLink>
	</DeskPage>
	<div v-else-if="loading" class="p-6 text-sm text-ink-500">{{ __("Loading…") }}</div>
</template>
