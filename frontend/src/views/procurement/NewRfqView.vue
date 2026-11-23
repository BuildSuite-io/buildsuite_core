<script setup>
// Request for Quotation form — create + edit (draft only). Project + dates header, the
// suppliers asked (contact person and email come from the Supplier's primary contact and can
// be corrected here for this request), an item grid, the subject / message that go on the
// email, and the terms. Honors ?mr=<id> to raise it from a submitted Material Request: the
// project, the required date and every line come across, and each line stays linked to the
// request line it came from. Saved via save_request_for_quotation.
import { computed, defineAsyncComponent, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { frappeRequest } from "frappe-ui-frappe-request";
import { showToast } from "@/utils/appToast";
import {
	getRfq,
	getMrForRfq,
	getSupplierContact,
	saveRfq,
	isEmail,
	todayISO,
} from "@/data/rfqApi";
import { getSupplierBillItemDetails } from "@/data/supplierBillApi";
import { addSupplier } from "@/data/suppliersApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import ItemFormModal from "@/components/ItemFormModal.vue";
import PartyFormModal from "@/views/finance/PartyFormModal.vue";
import { usePermissions } from "@/composables/usePermissions";
import { getDefaultTerms } from "@/data/termsApi";
import { __ } from "@/utils/translate";

const RichTextEditor = defineAsyncComponent(() => import("@/components/RichTextEditor.vue"));

const route = useRoute();
const router = useRouter();
const { canEdit, canCreate } = usePermissions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);
const canSaveForm = computed(() => (isEdit.value ? canEdit("rfq") : canCreate("rfq")));

function emptyLine() {
	return {
		item_code: "",
		description: "",
		qty: null,
		uom: "",
		cost_code: null,
		material_request: null,
		material_request_item: null,
	};
}

const form = ref({
	project: route.query.project || "",
	transaction_date: todayISO(),
	schedule_date: "",
	closing_date: "",
	subject: "",
	message_for_supplier: __(
		"Dear Sir / Madam,\n\nPlease send us your best quotation for the items below, delivered to the project site."
	),
	material_request: null,
	tc_name: "",
	terms: "",
	suppliers: [],
	lines: [emptyLine()],
});
const errors = ref({});
const saving = ref(false);
// Remount the rich-text editor when the terms are set for us (template pull or record load), so it
// initialises with that body rather than reporting it as an edit and dropping the template link.
const editorKey = ref(0);

// ---- suppliers: picked from the master; contact + email are copied in and stay editable ----
const supplierPick = ref("");
const supplierFilters = computed(() =>
	form.value.suppliers.length
		? [["name", "not in", form.value.suppliers.map((s) => s.supplier)]]
		: []
);
async function addSupplierRow(supplier) {
	supplierPick.value = "";
	if (!supplier || form.value.suppliers.some((s) => s.supplier === supplier)) return;
	try {
		const c = await getSupplierContact(supplier);
		form.value.suppliers.push({
			supplier,
			supplier_name: c.supplier_name || supplier,
			contact_person: c.contact_person || "",
			email_id: c.email_id || "",
		});
		delete errors.value.suppliers;
	} catch (err) {
		showToast(err.message || __("Could not read that supplier."), "error");
	}
}
function removeSupplierRow(idx) {
	form.value.suppliers.splice(idx, 1);
}

// Create a supplier straight from the picker (the shared PartyFormModal, as the Suppliers panel).
const SUPPLIER_TYPES = ["Company", "Individual", "Partnership"];
const supplierModalOpen = ref(false);
const supplierModalInitial = ref(null);
const supplierModalError = ref("");
function openSupplierCreate(text) {
	supplierModalInitial.value = { name: text || "", type: "Company" };
	supplierModalError.value = "";
	supplierModalOpen.value = true;
}
async function onSupplierSave(payload) {
	try {
		const res = await addSupplier(payload);
		supplierModalOpen.value = false;
		await addSupplierRow(res.name);
	} catch (err) {
		supplierModalError.value = err.message || __("Could not create the supplier.");
	}
}

// ---- items ----
// Default the line's UOM (and description, when blank) from the Item master on pick, as the
// Purchase Order form does.
async function onPickItem(line) {
	if (!line.item_code) return;
	try {
		const d = await getSupplierBillItemDetails(line.item_code);
		if (d.uom) line.uom = d.uom;
	} catch {
		/* leave the row for manual entry */
	}
}
const itemModalOpen = ref(false);
const itemModalInitial = ref("");
let itemModalLine = null;
function openItemCreate(line, text) {
	itemModalLine = line;
	itemModalInitial.value = text || "";
	itemModalOpen.value = true;
}
async function onItemCreated(code) {
	if (itemModalLine && code) {
		itemModalLine.item_code = code;
		await onPickItem(itemModalLine);
	}
	itemModalOpen.value = false;
	itemModalLine = null;
}
function addLine() {
	form.value.lines.push(emptyLine());
}
function removeLine(idx) {
	form.value.lines.splice(idx, 1);
	if (!form.value.lines.length) addLine();
}
const validLines = computed(() =>
	form.value.lines.filter((l) => l.item_code && Number(l.qty) > 0)
);

// ---- terms: a template copies its text in; editing afterwards makes them this request's own ----
async function onPickTerms(name) {
	form.value.tc_name = name || "";
	if (!name) return;
	try {
		const res = await frappeRequest({
			url: "frappe.client.get_value",
			params: { doctype: "Terms and Conditions", filters: name, fieldname: "terms" },
		});
		form.value.terms = res?.terms || "";
		editorKey.value += 1;
	} catch {
		form.value.tc_name = "";
		showToast(__("Could not read that terms template."), "error");
	}
}
function onTermsEdited() {
	form.value.tc_name = "";
}

// A new request starts with the standard clause, where one is set ("Offer this one first" under
// Settings › Terms & conditions › Request for Quotation).
if (!isEdit.value) {
	getDefaultTerms("Request for Quotation")
		.then((def) => {
			if (!def || form.value.terms) return;
			form.value.tc_name = def.name;
			form.value.terms = def.terms || "";
			editorKey.value += 1;
		})
		.catch(() => {
			// no default: the terms start empty
		});
}

// Edit mode: load the draft request.
watch(
	editingId,
	async (id) => {
		if (!id) return;
		try {
			const r = await getRfq(id);
			if (r.state !== "Draft") {
				showToast(__("Only a draft request can be edited."), "error");
				router.replace(`/procurement/rfqs/${id}`);
				return;
			}
			form.value = {
				project: r.project || "",
				transaction_date: r.transaction_date || todayISO(),
				schedule_date: r.schedule_date || "",
				closing_date: r.closing_date || "",
				subject: r.subject || "",
				message_for_supplier: r.message_for_supplier || "",
				material_request: r.material_request || null,
				tc_name: r.tc_name || "",
				terms: r.terms || "",
				suppliers: (r.suppliers || []).map((s) => ({
					supplier: s.supplier,
					supplier_name: s.supplier_name,
					contact_person: s.contact_person || "",
					email_id: s.email_id || "",
				})),
				lines: (r.items || []).map((it) => ({
					item_code: it.item_code || "",
					description: it.description || "",
					qty: it.qty,
					uom: it.uom || "",
					cost_code: it.cost_code || null,
					material_request: it.material_request || null,
					material_request_item: it.material_request_item || null,
				})),
			};
			if (!form.value.lines.length) form.value.lines = [emptyLine()];
			editorKey.value += 1;
		} catch (err) {
			showToast(err.message || __("Failed to load request"), "error");
		}
	},
	{ immediate: true }
);

// From a Material Request: prefill project, required date, subject and lines (/new?mr=<id>).
watch(
	() => route.query.mr,
	async (mrId) => {
		if (!mrId || isEdit.value) return;
		try {
			const pre = await getMrForRfq(mrId);
			form.value.project = pre.project || form.value.project;
			form.value.material_request = pre.material_request;
			form.value.schedule_date = pre.schedule_date || form.value.schedule_date;
			form.value.subject = form.value.subject || pre.subject || "";
			if (pre.lines?.length) {
				form.value.lines = pre.lines.map((l) => ({
					item_code: l.item_code || "",
					description: l.description || "",
					qty: l.qty,
					uom: l.uom || "",
					cost_code: l.cost_code || null,
					material_request: l.material_request || null,
					material_request_item: l.material_request_item || null,
				}));
			}
		} catch (err) {
			showToast(err.message || __("Failed to load material request"), "error");
		}
	},
	{ immediate: true }
);

function validate() {
	const e = {};
	if (!form.value.project) e.project = __("Pick a project.");
	if (!form.value.subject.trim())
		e.subject = __("Give the request a subject: it is the email subject too.");
	if (!form.value.suppliers.length) e.suppliers = __("Add at least one supplier to ask.");
	const bad = form.value.suppliers.find((s) => s.email_id && !isEmail(s.email_id));
	if (bad) e.suppliers = __("{0}: that email address does not look right.", [bad.supplier_name]);
	if (!validLines.value.length) e.lines = __("Add at least one item with a quantity.");
	if (
		form.value.closing_date &&
		form.value.schedule_date &&
		form.value.closing_date > form.value.schedule_date
	)
		e.closing_date = __("Quotations should be in before the material is required.");
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const rfq = await saveRfq({
			name: editingId.value || undefined,
			project: form.value.project,
			transaction_date: form.value.transaction_date,
			schedule_date: form.value.schedule_date || "",
			closing_date: form.value.closing_date || "",
			subject: form.value.subject.trim(),
			message_for_supplier: form.value.message_for_supplier || "",
			terms: form.value.terms || "",
			tc_name: form.value.tc_name || "",
			suppliers: form.value.suppliers.map((s) => ({
				supplier: s.supplier,
				contact_person: s.contact_person,
				email_id: s.email_id,
			})),
			items: validLines.value.map((l) => ({
				item_code: l.item_code,
				description: l.description,
				qty: Number(l.qty),
				uom: l.uom || null,
				cost_code: l.cost_code || null,
				// Keeps the line tied to its Material Request line.
				material_request: l.material_request || null,
				material_request_item: l.material_request_item || null,
			})),
		});
		showToast(isEdit.value ? __("Request saved.") : __("Request created."));
		router.push(`/procurement/rfqs/${rfq.name}`);
	} catch (err) {
		showToast(err.message || __("Failed to save request"), "error");
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Request for Quotation"), to: "/procurement/rfqs" },
	isEdit.value
		? { label: editingId.value, to: `/procurement/rfqs/${editingId.value}` }
		: { label: __("New") },
	...(isEdit.value ? [{ label: __("Edit") }] : []),
]);
const pageTitle = computed(() =>
	isEdit.value ? __("Edit {0}", [editingId.value]) : __("New Request for Quotation")
);
const saveLabel = computed(() =>
	saving.value ? __("Saving…") : isEdit.value ? __("Save changes") : __("Save draft")
);
</script>

<template>
	<DeskPage
		:title="pageTitle"
		:breadcrumbs="breadcrumbs"
		:subtitle="
			form.material_request ? __('From material request {0}', [form.material_request]) : ''
		"
	>
		<div
			v-if="!canSaveForm"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{
				isEdit
					? __("You don't have permission to edit this request for quotation.")
					: __("You don't have permission to create a request for quotation.")
			}}
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection id="request" :title="__('Request')" :cols="4">
				<DeskField
					:label="__('Project')"
					required
					:error="errors.project"
					:hint="form.material_request ? __('Set by the material request.') : ''"
				>
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						:disabled="!!form.material_request"
						:placeholder="__('— Select project —')"
					/>
				</DeskField>
				<DeskField :label="__('Date')">
					<DeskInput v-model="form.transaction_date" type="date" />
				</DeskField>
				<DeskField :label="__('Material required by')">
					<DeskInput v-model="form.schedule_date" type="date" />
				</DeskField>
				<DeskField
					:label="__('Quote by')"
					:error="errors.closing_date"
					:hint="__('The closing date suppliers are asked to reply by.')"
				>
					<DeskInput v-model="form.closing_date" type="date" />
				</DeskField>
			</DeskSection>

			<!-- Suppliers -->
			<section class="mt-6" data-test="rfq-suppliers">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						{{ __("Suppliers") }}
					</h3>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 640px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">{{ __("Supplier") }}</th>
								<th class="text-left px-3 py-2">{{ __("Contact person") }}</th>
								<th class="text-left px-3 py-2">{{ __("Email") }}</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(s, idx) in form.suppliers"
								:key="s.supplier"
								class="border-t border-ink-100"
								data-test="rfq-supplier-row"
							>
								<td class="px-3 py-2 text-ink-900 font-medium">
									{{ s.supplier_name || s.supplier }}
								</td>
								<td class="px-3 py-2">
									<input
										v-model="s.contact_person"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										:placeholder="__('Contact person')"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model="s.email_id"
										type="email"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										:placeholder="__('name@supplier.com')"
									/>
								</td>
								<td class="px-2 py-2 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										:title="__('Remove')"
										@click="removeSupplierRow(idx)"
									>
										✕
									</button>
								</td>
							</tr>
							<tr v-if="!form.suppliers.length" class="border-t border-ink-100">
								<td colspan="4" class="px-3 py-3 text-center text-ink-400 italic">
									{{ __("No suppliers yet. Add the ones to ask below.") }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div class="mt-2 max-w-sm">
					<DeskLinkPicker
						:model-value="supplierPick"
						doctype="Supplier"
						label-field="supplier_name"
						value-field="name"
						:search-fields="['supplier_name', 'name']"
						:filters="supplierFilters"
						:placeholder="__('+ Add supplier…')"
						:allow-create="canCreate('supplier')"
						:create-label="__('supplier')"
						data-test="rfq-add-supplier"
						@update:model-value="addSupplierRow"
						@create="openSupplierCreate"
					/>
				</div>
				<p v-if="errors.suppliers" class="text-xs text-danger-700 mt-1">
					{{ errors.suppliers }}
				</p>
				<p class="text-[11px] text-ink-500 mt-2">
					{{
						__(
							"Contact and email come from the supplier's record. Correct them here for this request; the request's page offers to save a change back to the supplier."
						)
					}}
				</p>
			</section>

			<!-- Item lines -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						{{ __("Items") }}
					</h3>
					<button
						type="button"
						class="text-xs text-brand-700 hover:underline"
						@click="addLine"
					>
						+ {{ __("Add item") }}
					</button>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 820px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2" style="min-width: 200px">
									{{ __("Item") }}
								</th>
								<th class="text-left px-3 py-2">{{ __("Description") }}</th>
								<th class="text-left px-3 py-2" style="min-width: 160px">
									{{ __("Cost code") }}
								</th>
								<th class="text-right px-3 py-2 w-24">{{ __("Qty") }}</th>
								<th class="text-left px-3 py-2 w-28">{{ __("UOM") }}</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(line, idx) in form.lines"
								:key="idx"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2" style="min-width: 200px">
									<DeskLinkPicker
										v-model="line.item_code"
										doctype="Item"
										label-field="item_name"
										value-field="name"
										:search-fields="['item_name', 'item_code', 'name']"
										:placeholder="__('— Item —')"
										:allow-create="canCreate('item')"
										:create-label="__('item')"
										@update:model-value="onPickItem(line)"
										@create="(text) => openItemCreate(line, text)"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model="line.description"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										:placeholder="__('Make, grade, size…')"
									/>
								</td>
								<td class="px-3 py-2" style="min-width: 160px">
									<CostCodePicker
										v-model="line.cost_code"
										:project-id="form.project"
										:placeholder="__('— Cost code —')"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.qty"
										type="number"
										min="0"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
									/>
								</td>
								<td class="px-3 py-2" style="min-width: 110px">
									<DeskLinkPicker
										v-model="line.uom"
										doctype="UOM"
										label-field="name"
										value-field="name"
										placeholder="—"
									/>
								</td>
								<td class="px-2 py-2 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										:title="__('Remove')"
										@click="removeLine(idx)"
									>
										✕
									</button>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">{{ errors.lines }}</p>
			</section>

			<DeskSection id="message" :title="__('Message to suppliers')" :cols="1" class="mt-6">
				<DeskField
					:label="__('Subject')"
					required
					:error="errors.subject"
					:hint="__('Heads the printed request and is the subject of the email.')"
				>
					<DeskInput
						v-model="form.subject"
						:placeholder="__('Request for Quotation: …')"
					/>
				</DeskField>
				<DeskField
					:label="__('Message')"
					:hint="
						__(
							'The body of the email. Each supplier is greeted by its contact person; the request itself goes as an attachment.'
						)
					"
				>
					<DeskTextarea v-model="form.message_for_supplier" :rows="5" />
				</DeskField>
			</DeskSection>

			<DeskSection :title="__('Terms & conditions')" :cols="1" class="mt-6">
				<DeskField
					:label="__('Import from template')"
					:hint="
						__(
							'Templates are kept under Settings › Terms & conditions › Request for Quotation. Picking one replaces the text below.'
						)
					"
				>
					<DeskLinkPicker
						:model-value="form.tc_name"
						doctype="Terms and Conditions"
						label-field="name"
						value-field="name"
						:filters="{ custom_applicable_for: 'Request for Quotation' }"
						:placeholder="__('Import from template…')"
						@update:model-value="onPickTerms"
					/>
				</DeskField>
				<DeskField
					:label="__('Terms & conditions')"
					:hint="
						form.tc_name
							? __(
									'Pulled from a template. Editing it here does not change the library.'
							  )
							: __(
									'Validity, delivery, payment and reply terms. Prints on the request.'
							  )
					"
				>
					<RichTextEditor
						:key="editorKey"
						v-model="form.terms"
						min-height="10rem"
						@update:model-value="onTermsEdited"
					/>
				</DeskField>
			</DeskSection>
		</DeskForm>

		<ItemFormModal
			:open="itemModalOpen"
			:initial-code="itemModalInitial"
			@close="itemModalOpen = false"
			@saved="onItemCreated"
		/>
		<PartyFormModal
			:open="supplierModalOpen"
			:title="__('New Supplier')"
			:type-label="__('Supplier type')"
			:type-options="SUPPLIER_TYPES"
			:initial="supplierModalInitial"
			:server-error="supplierModalError"
			@save="onSupplierSave"
			@close="supplierModalOpen = false"
		/>
	</DeskPage>
</template>
