<script setup>
// Project Finance › Invoice form — a full PAGE (not a modal), for create
// (/project-finance/invoices/new) and edit of a Draft (/project-finance/invoices/:id/edit;
// a non-Draft bounces to the detail page). Saves a draft Sales Invoice via api.invoice.
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { getInvoice, saveInvoice, listInvoiceTaxTemplates } from "@/data/invoiceApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { activeCompanyFilter } from "@/composables/useActiveCompany";
import { fmtINR } from "@/utils/format";

const props = defineProps({ id: { type: String, default: "" } });
const router = useRouter();
const companyFilter = activeCompanyFilter();
const isEdit = computed(() => !!props.id);

function newLine() {
	return { description: "", qty: 1, rate: null };
}
const form = reactive({
	customer: "",
	project: "",
	date: new Date().toISOString().slice(0, 10),
	due_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
	taxes_and_charges: "",
	lines: [newLine()],
	saving: false,
});
const taxTemplates = ref([]);
const loading = ref(isEdit.value);

listInvoiceTaxTemplates()
	.then((r) => (taxTemplates.value = r || []))
	.catch(() => {});

if (isEdit.value) {
	getInvoice(props.id)
		.then((inv) => {
			if (inv.docstatus !== 0) {
				router.replace(`/project-finance/invoices/${props.id}`);
				return;
			}
			Object.assign(form, {
				customer: inv.customer,
				project: inv.project || "",
				date: inv.date,
				due_date: inv.due_date || "",
				taxes_and_charges: inv.taxes_and_charges || "",
				lines: (inv.items || []).map((l) => ({ description: l.description, qty: l.qty ?? 1, rate: l.rate })),
			});
			if (!form.lines.length) form.lines = [newLine()];
		})
		.catch((err) => showToast(err.message || "Failed to load invoice", "error"))
		.finally(() => (loading.value = false));
}

const subtotal = computed(() => form.lines.reduce((a, l) => a + (Number(l.qty) || 0) * (Number(l.rate) || 0), 0));

const breadcrumbs = computed(() => [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Invoices", to: "/project-finance/invoices" },
	{ label: isEdit.value ? `Edit ${props.id}` : "New" },
]);

function goBack() {
	router.push(isEdit.value ? `/project-finance/invoices/${props.id}` : "/project-finance/invoices");
}
async function save() {
	if (!form.customer) return showToast("Pick a customer.", "error");
	const lines = form.lines.filter((l) => Number(l.rate) > 0);
	if (!lines.length) return showToast("Add at least one line with an amount.", "error");
	form.saving = true;
	try {
		const res = await saveInvoice({
			name: isEdit.value ? props.id : undefined,
			customer: form.customer,
			project: form.project || undefined,
			date: form.date,
			due_date: form.due_date || undefined,
			taxes_and_charges: form.taxes_and_charges || undefined,
			items: lines.map((l) => ({ description: l.description, qty: Number(l.qty) || 1, rate: Number(l.rate) })),
		});
		showToast(isEdit.value ? "Invoice updated." : "Invoice saved as draft.");
		router.push(`/project-finance/invoices/${res.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		form.saving = false;
	}
}
</script>

<template>
	<DeskPage :title="isEdit ? `Edit ${id}` : 'New invoice'" :breadcrumbs="breadcrumbs">
		<template #actions>
			<div class="flex items-center gap-2">
				<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="goBack">Cancel</button>
				<button type="button" class="text-xs desk-save-btn" :disabled="form.saving || loading" @click="save">{{ form.saving ? "Saving…" : isEdit ? "Save" : "Save as draft" }}</button>
			</div>
		</template>

		<div v-if="loading" class="py-16 text-center text-sm text-ink-400">Loading…</div>
		<div v-else class="max-w-3xl space-y-4">
			<section class="bg-white border border-ink-200 rounded-lg p-4 space-y-3">
				<div class="grid grid-cols-2 gap-3">
					<DeskField label="Customer" required><DeskLinkPicker v-model="form.customer" doctype="Customer" label-field="customer_name" value-field="name" placeholder="Pick a customer…" /></DeskField>
					<DeskField label="Project"><DeskLinkPicker v-model="form.project" doctype="Project" label-field="project_name" value-field="name" :filters="companyFilter" placeholder="Optional…" /></DeskField>
				</div>
				<div class="grid grid-cols-3 gap-3">
					<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
					<DeskField label="Due date"><DeskInput v-model="form.due_date" type="date" /></DeskField>
					<DeskField label="Tax"><DeskSelect v-model="form.taxes_and_charges"><option value="">No tax</option><option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.title || t.name }}</option></DeskSelect></DeskField>
				</div>
			</section>

			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">Items</h3></div>
				<table class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px]"><tr><th class="text-left px-3 py-2">Description</th><th class="text-right px-3 py-2 w-16">Qty</th><th class="text-right px-3 py-2 w-28">Rate</th><th class="text-right px-3 py-2 w-28">Amount</th><th class="w-8"></th></tr></thead>
					<tbody>
						<tr v-for="(l, idx) in form.lines" :key="idx" class="border-t border-ink-100">
							<td class="px-2 py-1"><input v-model="l.description" type="text" placeholder="What is billed?" class="w-full px-1.5 py-1 border border-transparent hover:border-ink-200 focus:border-brand-400 rounded focus:outline-none" /></td>
							<td class="px-2 py-1"><input v-model.number="l.qty" type="number" min="0" class="w-full text-right px-1.5 py-1 border border-transparent hover:border-ink-200 focus:border-brand-400 rounded focus:outline-none tabular-nums" /></td>
							<td class="px-2 py-1"><input v-model.number="l.rate" type="number" min="0" placeholder="0" class="w-full text-right px-1.5 py-1 border border-transparent hover:border-ink-200 focus:border-brand-400 rounded focus:outline-none tabular-nums" /></td>
							<td class="px-3 py-1 text-right tabular-nums text-ink-700">{{ fmtINR((Number(l.qty) || 0) * (Number(l.rate) || 0)) }}</td>
							<td class="px-2 py-1 text-center"><button v-if="form.lines.length > 1" type="button" class="text-ink-400 hover:text-danger-600" @click="form.lines.splice(idx, 1)">✕</button></td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="border-t border-ink-200 bg-ink-50/40">
							<td colspan="3" class="px-3 py-2"><button type="button" class="text-[11px] text-brand-700 hover:underline" @click="form.lines.push(newLine())">+ Add line</button></td>
							<td class="px-3 py-2 text-right tabular-nums font-semibold text-ink-900">{{ fmtINR(subtotal) }}</td>
							<td></td>
						</tr>
					</tfoot>
				</table>
			</section>
			<p class="text-[11px] text-ink-400">Any tax is applied on save; the subtotal above is before tax.</p>
		</div>
	</DeskPage>
</template>
