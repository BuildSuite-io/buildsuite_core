<script setup>
// Request for Quotation detail — the native submittable lifecycle (Draft → Edit / Submit /
// Delete; Submitted → Cancel; Cancelled → Amend / Delete) and, once submitted, the working
// surface of the enquiry: print it for a supplier, email it, correct the person or address it
// goes to (and offer that back to the supplier's record), record the Supplier Quotation that
// comes back, and compare the quotations.
import { computed, defineAsyncComponent, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getRfq,
	submitRfq,
	cancelRfq,
	amendRfq,
	deleteRfq,
	setRfqSupplierContact,
	saveRfqContactToSupplier,
	sendRfqEmails,
	isEmail,
} from "@/data/rfqApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import { usePermissions } from "@/composables/usePermissions";
import { useWorkflow } from "@/composables/useWorkflow";
import { fmtDate, fmtINR } from "@/utils/format";
import { useReportAccess } from "@/composables/useReportAccess";
import { __ } from "@/utils/translate";

const RichTextEditor = defineAsyncComponent(() => import("@/components/RichTextEditor.vue"));

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const { canEdit, canSubmit, canCreate, canDelete } = usePermissions();

// Defer to an active Frappe Workflow on Request for Quotation when one is configured; with
// none, the plain Submit / Cancel lifecycle shows.
const {
	active: wfActive,
	state: wfState,
	transitions: wfTransitions,
	refresh: refreshWorkflow,
	applyAction: applyWorkflowAction,
} = useWorkflow("Request for Quotation");

const rfq = ref(null);
const loading = ref(true);
const busy = ref(false);

const { canOpenReport } = useReportAccess();

async function load() {
	loading.value = true;
	try {
		rfq.value = await getRfq(props.id);
		await refreshWorkflow(props.id);
	} catch (err) {
		showToast(err.message || __("Failed to load request"), "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => rfq.value?.state === "Draft");
const isSubmitted = computed(() => rfq.value?.state === "Submitted");
const isCancelled = computed(() => rfq.value?.state === "Cancelled");
const canManage = computed(() => canEdit("rfq"));
const anySubmittedQuote = computed(() =>
	(rfq.value?.quotations || []).some((q) => q.docstatus === 1)
);

function onEdit() {
	router.push(`/procurement/rfqs/${rfq.value.name}/edit`);
}
function onPrint(supplier) {
	const q = supplier ? `?supplier=${encodeURIComponent(supplier)}` : "";
	router.push(`/procurement/rfqs/${rfq.value.name}/print${q}`);
}
function onCompare() {
	router.push(
		`/procurement/supplier-quotation-comparison?rfq=${encodeURIComponent(rfq.value.name)}`
	);
}
function onAddQuotation(supplier) {
	router.push(
		`/procurement/supplier-quotations/new?rfq=${encodeURIComponent(
			rfq.value.name
		)}&supplier=${encodeURIComponent(supplier)}`
	);
}

async function onSubmit() {
	const n = rfq.value.suppliers.length;
	const ok = await confirmDialog({
		title: __("Submit {0}?", [rfq.value.name]),
		message:
			n === 1
				? __(
						"It can then be printed and emailed to its supplier. A submitted request is cancelled, not edited."
				  )
				: __(
						"It can then be printed and emailed to its {0} suppliers. A submitted request is cancelled, not edited.",
						[n]
				  ),
		confirmLabel: __("Submit"),
	});
	if (!ok) return;
	busy.value = true;
	try {
		rfq.value = await submitRfq(rfq.value.name);
		await refreshWorkflow(rfq.value.name);
		showToast(__("Request submitted."));
	} catch (err) {
		showToast(err.message || __("Submit failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: __("Cancel {0}?", [rfq.value.name]),
		message: __(
			"Cancelling withdraws the request. Supplier quotations against it must be cancelled first."
		),
		confirmLabel: __("Cancel request"),
		cancelLabel: __("Keep"),
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		rfq.value = await cancelRfq(rfq.value.name);
		await refreshWorkflow(rfq.value.name);
		showToast(__("Request cancelled."));
	} catch (err) {
		showToast(err.message || __("Cancel failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onWorkflowAction(action) {
	busy.value = true;
	try {
		await applyWorkflowAction(rfq.value.name, action);
		await load();
		showToast(__("{0} done.", [action]));
	} catch (err) {
		showToast(err.message || __("Action failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onAmend() {
	busy.value = true;
	try {
		const res = await amendRfq(rfq.value.name);
		showToast(__("Amended — a fresh draft was created."));
		router.push(`/procurement/rfqs/${res.name}`);
	} catch (err) {
		showToast(err.message || __("Amend failed"), "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete {0}?", [rfq.value.name]),
		message: __("This request, its suppliers and its items will be removed permanently."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteRfq(rfq.value.name);
		router.push("/procurement/rfqs");
	} catch (err) {
		showToast(err.message || __("Failed to delete request"), "error");
	}
}

// ---- contact person / email, corrected on the request ----
const editing = ref(null); // the supplier whose row is being edited
const draft = reactive({ contact_person: "", email_id: "" });
function startEdit(row) {
	editing.value = row.supplier;
	draft.contact_person = row.contact_person || "";
	draft.email_id = row.email_id || "";
}
async function saveEdit(row) {
	if (draft.email_id && !isEmail(draft.email_id)) {
		showToast(__("That email address does not look right."), "error");
		return;
	}
	try {
		rfq.value = await setRfqSupplierContact(rfq.value.name, row.supplier, {
			contact_person: draft.contact_person,
			email_id: draft.email_id,
		});
		editing.value = null;
	} catch (err) {
		showToast(err.message || __("Could not save the contact."), "error");
	}
}
async function saveToSupplier(row) {
	try {
		rfq.value = await saveRfqContactToSupplier(rfq.value.name, row.supplier);
		showToast(__("{0}: contact saved to the supplier's record.", [row.supplier_name]));
	} catch (err) {
		showToast(err.message || __("Could not update the supplier."), "error");
	}
}

// ---- email: one copy per supplier, sent on demand ----
const mailOpen = ref(false);
const mailPick = reactive({});
const sending = ref(false);
function openMail(only) {
	const rows = rfq.value.suppliers;
	for (const s of rows)
		mailPick[s.supplier] = only
			? s.supplier === only && isEmail(s.email_id)
			: isEmail(s.email_id) && !s.email_sent;
	// Everyone already has it: offer a resend to all who can receive one.
	if (!only && !Object.values(mailPick).some(Boolean))
		for (const s of rows) mailPick[s.supplier] = isEmail(s.email_id);
	mailOpen.value = true;
}
const mailTo = computed(() =>
	rfq.value ? rfq.value.suppliers.filter((s) => mailPick[s.supplier]) : []
);
const mailSample = computed(() =>
	mailTo.value.length ? rfq.value.email?.[mailTo.value[0].supplier] || null : null
);
async function sendMail() {
	sending.value = true;
	try {
		const res = await sendRfqEmails(
			rfq.value.name,
			mailTo.value.map((s) => s.supplier)
		);
		rfq.value = res.doc;
		mailOpen.value = false;
		showToast(
			__("Emailed to {0}.", [res.sent.join(", ")]) +
				(res.skipped.length
					? " " + __("Not sent to {0}: no email address.", [res.skipped.join(", ")])
					: "")
		);
	} catch (err) {
		showToast(err.message || __("Could not send the email."), "error");
	} finally {
		sending.value = false;
	}
}

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Request for Quotation"), to: "/procurement/rfqs" },
	{ label: rfq.value?.name || props.id },
]);
</script>

<template>
	<DeskPage
		v-if="rfq"
		:title="rfq.name"
		:subtitle="
			rfq.material_request
				? __('{0} · {1} · from {2}', [
						rfq.project_name || rfq.project,
						fmtDate(rfq.transaction_date),
						rfq.material_request,
				  ])
				: `${rfq.project_name || rfq.project} · ${fmtDate(rfq.transaction_date)}`
		"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<ProcurementStatusPill
				:status="rfq.status"
				class="self-center mr-1"
				data-test="rfq-status"
			/>
			<span
				v-if="wfActive && wfState && wfState !== rfq.status"
				class="self-center mr-1 text-[11px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200"
				>{{ __(wfState) }}</span
			>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 flex items-center gap-1.5"
				style="border-radius: 6px"
				:title="__('See the request as the supplier will, and print or save it as a PDF')"
				@click="onPrint()"
			>
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.75"
						d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
					/>
				</svg>
				{{ __("Preview / Print") }}
			</button>
			<button
				v-if="isDraft && canEdit('rfq')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="onEdit"
			>
				{{ __("Edit") }}
			</button>
			<button
				v-if="
					anySubmittedQuote &&
					canOpenReport('/procurement/supplier-quotation-comparison')
				"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				data-test="rfq-compare"
				@click="onCompare"
			>
				{{ __("Compare quotations") }}
			</button>
			<button
				v-if="isSubmitted && canManage"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				data-test="rfq-send-email"
				@click="openMail()"
			>
				{{ __("Send email") }}
			</button>
			<!-- Plain docstatus lifecycle (no workflow configured) -->
			<button
				v-if="!wfActive && isDraft && canSubmit('rfq')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				data-test="rfq-submit"
				@click="onSubmit"
			>
				{{ __("Submit") }}
			</button>
			<button
				v-if="!wfActive && isSubmitted && canSubmit('rfq')"
				type="button"
				class="text-xs px-2.5 py-1 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				data-test="rfq-cancel"
				@click="onCancel"
			>
				{{ __("Cancel") }}
			</button>
			<!-- Workflow transitions (active workflow) — role- and state-filtered by the backend -->
			<button
				v-for="t in wfActive ? wfTransitions : []"
				:key="t.action"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onWorkflowAction(t.action)"
			>
				{{ __(t.action) }}
			</button>
			<button
				v-if="isCancelled && canCreate('rfq')"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				:title="__('Create a fresh editable draft copy (the original stays cancelled)')"
				@click="onAmend"
			>
				{{ __("Amend") }}
			</button>
			<button
				v-if="!isSubmitted && canDelete('rfq')"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				{{ __("Delete") }}
			</button>
		</template>

		<div
			v-if="isDraft"
			class="mb-4 px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-md text-xs text-ink-600"
		>
			{{ __("Draft. Submit it to send it to suppliers and record their quotations.") }}
		</div>
		<div
			v-if="isCancelled"
			class="mb-4 px-4 py-2.5 bg-ink-100 border border-ink-200 rounded-md text-xs text-ink-600"
		>
			{{ __("This request is cancelled. Amend it to raise a corrected draft.") }}
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
			<div class="bg-white border border-ink-200 rounded-lg p-3 col-span-2">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Subject") }}
				</div>
				<div class="text-sm font-medium text-ink-900 mt-0.5">
					{{ rfq.subject || "—" }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Project") }}
				</div>
				<DeskLink :to="`/projects/${rfq.project}`" class="text-sm">{{
					rfq.project_name || rfq.project
				}}</DeskLink>
				<div v-if="rfq.material_request" class="mt-0.5">
					<DeskLink
						:to="`/procurement/material-requests/${rfq.material_request}`"
						class="text-[11px]"
						>{{ rfq.material_request }}</DeskLink
					>
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg p-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">
					{{ __("Quote by") }}
				</div>
				<div class="text-sm text-ink-900 mt-0.5">
					{{ rfq.closing_date ? fmtDate(rfq.closing_date) : "—" }}
				</div>
				<div class="text-[10px] text-ink-500">
					{{
						rfq.schedule_date
							? __("Material required by {0}", [fmtDate(rfq.schedule_date)])
							: __("No required date")
					}}
				</div>
			</div>
		</div>

		<!-- Suppliers asked -->
		<section
			class="bg-white border border-ink-200 rounded-lg overflow-x-auto mb-4"
			data-test="rfq-suppliers"
		>
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					{{ __("Suppliers asked") }}
				</h3>
			</div>
			<table class="w-full text-xs" style="min-width: 820px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">{{ __("Supplier") }}</th>
						<th class="text-left px-3 py-2">{{ __("Contact person") }}</th>
						<th class="text-left px-3 py-2">{{ __("Email") }}</th>
						<th class="text-left px-3 py-2">{{ __("Emailed") }}</th>
						<th class="text-left px-3 py-2">{{ __("Quotation") }}</th>
						<th class="px-3 py-2"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="s in rfq.suppliers"
						:key="s.supplier"
						class="border-t border-ink-100 align-top"
						data-test="rfq-supplier-row"
					>
						<td class="px-3 py-2.5 text-ink-900 font-medium whitespace-nowrap">
							{{ s.supplier_name }}
						</td>
						<template v-if="editing === s.supplier">
							<td class="px-3 py-2">
								<input
									v-model="draft.contact_person"
									class="desk-input !py-1 !text-xs"
									:placeholder="__('Contact person')"
								/>
							</td>
							<td class="px-3 py-2">
								<input
									v-model="draft.email_id"
									type="email"
									class="desk-input !py-1 !text-xs"
									:placeholder="__('name@supplier.com')"
									data-test="rfq-email-input"
								/>
							</td>
						</template>
						<template v-else>
							<td class="px-3 py-2.5 text-ink-700">
								{{ s.contact_person || "—" }}
							</td>
							<td class="px-3 py-2.5">
								<span v-if="s.email_id" class="text-ink-700">{{
									s.email_id
								}}</span>
								<span v-else class="text-warning-700">{{
									__("No email address")
								}}</span>
								<div
									v-if="
										canManage &&
										!isCancelled &&
										s.differs_from_master &&
										rfq.can_edit_supplier
									"
									class="text-[11px] text-ink-500 mt-0.5"
								>
									{{ __("Differs from the supplier's record.") }}
									<button
										type="button"
										class="text-brand-700 hover:underline"
										data-test="rfq-save-to-supplier"
										@click="saveToSupplier(s)"
									>
										{{ __("Save it there") }}
									</button>
								</div>
							</td>
						</template>
						<td
							class="px-3 py-2.5 whitespace-nowrap"
							:class="s.email_sent ? 'text-ink-700' : 'text-ink-500'"
						>
							{{ s.email_sent ? fmtDate(s.email_sent_at) : __("Not yet") }}
						</td>
						<td class="px-3 py-2.5 whitespace-nowrap">
							<ProcurementStatusPill :status="s.quote_status" />
							<template v-if="s.quotation">
								<DeskLink
									:to="`/procurement/supplier-quotations/${s.quotation.name}`"
									class="ml-2"
									>{{ s.quotation.name }}</DeskLink
								>
								<span class="text-ink-500 ml-1 tabular-nums">{{
									fmtINR(s.quotation.total)
								}}</span>
							</template>
						</td>
						<td class="px-3 py-2.5 text-right whitespace-nowrap">
							<template v-if="canManage && !isCancelled">
								<template v-if="editing === s.supplier">
									<button
										type="button"
										class="text-brand-700 hover:underline mr-3"
										@click="saveEdit(s)"
									>
										{{ __("Save") }}
									</button>
									<button
										type="button"
										class="text-ink-500 hover:underline"
										@click="editing = null"
									>
										{{ __("Cancel") }}
									</button>
								</template>
								<template v-else>
									<button
										type="button"
										class="text-ink-600 hover:underline mr-3"
										data-test="rfq-edit-contact"
										@click="startEdit(s)"
									>
										{{ __("Edit contact") }}
									</button>
									<button
										type="button"
										class="text-ink-600 hover:underline mr-3"
										@click="onPrint(s.supplier)"
									>
										{{ __("Print") }}
									</button>
									<button
										v-if="isSubmitted"
										type="button"
										class="text-ink-600 hover:underline mr-3"
										@click="openMail(s.supplier)"
									>
										{{ __("Email") }}
									</button>
									<button
										v-if="
											isSubmitted &&
											!s.quotation &&
											canCreate('supplierQuotation')
										"
										type="button"
										class="text-brand-700 hover:underline"
										data-test="rfq-add-quotation"
										@click="onAddQuotation(s.supplier)"
									>
										+ {{ __("Supplier quotation") }}
									</button>
								</template>
							</template>
						</td>
					</tr>
				</tbody>
			</table>
		</section>

		<!-- Item lines -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto mb-4">
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					{{ __("Items") }}
				</h3>
			</div>
			<table class="w-full text-xs" style="min-width: 560px">
				<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">{{ __("Item") }}</th>
						<th class="text-right px-3 py-2">{{ __("Qty") }}</th>
						<th class="text-left px-3 py-2">{{ __("UOM") }}</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(it, i) in rfq.items"
						:key="i"
						class="border-t border-ink-100 align-top"
					>
						<td class="px-3 py-2">
							<span class="text-ink-900">{{ it.item_name || it.item_code }}</span>
							<span
								v-if="it.item_name && it.item_code !== it.item_name"
								class="text-[10px] font-mono text-ink-400 ml-1.5"
								>{{ it.item_code }}</span
							>
							<span
								v-if="it.description"
								class="block text-[11px] text-ink-500 mt-0.5"
								>{{ it.description }}</span
							>
							<span
								v-if="it.cost_code && it.cost_code.label"
								class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded mt-1"
								:class="
									it.cost_code.type === 'item'
										? 'bg-brand-50 text-brand-700'
										: 'bg-info-50 text-info-700'
								"
								>{{ it.cost_code.label }}</span
							>
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ it.qty }}
						</td>
						<td class="px-3 py-2 text-ink-500">{{ it.uom || "—" }}</td>
					</tr>
				</tbody>
			</table>
		</section>

		<!-- Quotations received -->
		<section
			v-if="rfq.quotations.length"
			class="bg-white border border-ink-200 rounded-lg overflow-x-auto mb-4"
			data-test="rfq-quotations"
		>
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					{{ __("Supplier quotations") }}
				</h3>
			</div>
			<table class="w-full text-xs" style="min-width: 560px">
				<tbody>
					<tr
						v-for="q in rfq.quotations"
						:key="q.name"
						class="border-t border-ink-100 first:border-t-0 cursor-pointer hover:bg-ink-50"
						@click="router.push(`/procurement/supplier-quotations/${q.name}`)"
					>
						<td class="px-3 py-2.5 font-mono text-[11px] text-ink-600">
							{{ q.name }}
						</td>
						<td class="px-3 py-2.5 text-ink-900">
							{{ q.supplier_name || q.supplier }}
						</td>
						<td class="px-3 py-2.5 text-ink-500 whitespace-nowrap">
							{{ fmtDate(q.transaction_date) }}
						</td>
						<td class="px-3 py-2.5 text-right tabular-nums text-ink-900 font-medium">
							{{ fmtINR(q.total) }}
						</td>
						<td class="px-3 py-2.5 text-right">
							<ProcurementStatusPill :status="q.status" kind="quotation" />
						</td>
					</tr>
				</tbody>
			</table>
		</section>

		<section class="bg-white border border-ink-200 rounded-lg overflow-hidden mb-4">
			<header class="px-4 py-2 bg-ink-50 border-b border-ink-200">
				<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
					{{ __("Message to suppliers") }}
				</div>
			</header>
			<p class="px-4 py-3 text-xs text-ink-700 whitespace-pre-line">
				{{ rfq.message_for_supplier || "—" }}
			</p>
		</section>

		<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
			<header
				class="flex items-center justify-between px-4 py-2 bg-ink-50 border-b border-ink-200"
			>
				<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
					{{ __("Terms & conditions") }}
				</div>
				<span
					v-if="rfq.terms"
					class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600"
					style="border-radius: 9999px"
				>
					{{ rfq.tc_name ? __("Template") : __("Manual") }}
				</span>
			</header>
			<div class="p-4">
				<RichTextEditor
					v-if="rfq.terms"
					:model-value="rfq.terms"
					:editable="false"
					min-height="auto"
				/>
				<p v-else class="text-sm text-ink-400">
					{{ __("No terms recorded. Edit the draft to add them.") }}
				</p>
			</div>
		</section>

		<!-- Send email -->
		<Teleport to="body">
			<div
				v-if="mailOpen"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
				@click.self="mailOpen = false"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-xl shadow-xl flex flex-col"
					style="border-radius: 12px"
					data-test="rfq-mail"
					@click.stop
				>
					<header
						class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
					>
						<h2 class="text-sm font-semibold text-ink-900">
							{{ __("Email request for quotation") }}
						</h2>
						<button
							type="button"
							class="text-ink-400 hover:text-ink-900"
							:aria-label="__('Close')"
							@click="mailOpen = false"
						>
							✕
						</button>
					</header>
					<div class="px-4 py-4 space-y-3">
						<div>
							<div
								class="text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>
								{{ __("Send to") }}
							</div>
							<label
								v-for="s in rfq.suppliers"
								:key="s.supplier"
								class="flex items-center gap-2 py-1 text-sm flex-wrap"
								:class="isEmail(s.email_id) ? 'text-ink-900' : 'text-ink-500'"
							>
								<input
									v-model="mailPick[s.supplier]"
									type="checkbox"
									:disabled="!isEmail(s.email_id)"
								/>
								<span class="font-medium">{{ s.supplier_name }}</span>
								<span class="text-xs text-ink-500">{{
									isEmail(s.email_id)
										? s.email_id
										: __("no email address: add one with Edit contact")
								}}</span>
								<span v-if="s.email_sent" class="text-[10px] text-ink-500"
									>· {{ __("sent {0}", [fmtDate(s.email_sent_at)]) }}</span
								>
							</label>
						</div>
						<div v-if="mailSample" class="border border-ink-200 rounded-lg text-xs">
							<div class="px-3 py-2 border-b border-ink-100 text-ink-600">
								<span class="text-ink-500">{{ __("To:") }}</span>
								{{ mailSample.to }}
								<span v-if="mailTo.length > 1" class="text-ink-500">
									({{ __("each supplier gets its own copy") }})</span
								>
							</div>
							<div class="px-3 py-2 border-b border-ink-100 text-ink-900">
								<span class="text-ink-500">{{ __("Subject:") }}</span>
								{{ mailSample.subject }}
							</div>
							<p class="px-3 py-2 text-ink-700 whitespace-pre-line">
								{{ mailSample.body }}
							</p>
							<div class="px-3 py-2 border-t border-ink-100 text-ink-500">
								{{ __("Attachment: {0}.pdf", [rfq.name]) }}
							</div>
						</div>
					</div>
					<footer
						class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
							@click="mailOpen = false"
						>
							{{ __("Cancel") }}
						</button>
						<button
							type="button"
							class="desk-save-btn !text-xs"
							:disabled="!mailTo.length || sending"
							:class="{ 'opacity-50': !mailTo.length || sending }"
							data-test="rfq-mail-send"
							@click="sendMail"
						>
							{{
								sending
									? __("Sending…")
									: mailTo.length === 1
									? __("Send to 1 supplier")
									: __("Send to {0} suppliers", [mailTo.length])
							}}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">
		{{ loading ? __("Loading request…") : __("Request for quotation not found.") }}
	</div>
</template>
