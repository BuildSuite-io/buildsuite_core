<script setup>
import { computed, reactive, ref } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Invoices" }];
const rows = computed(() => fin.invoices);

const form = reactive({ open: false, customer: "", project: "", date: new Date().toISOString().slice(0, 10), due_date: "", gst_rate: 18, description: "", amount: 0 });
function createInvoice() {
	if (!form.customer || !(Number(form.amount) > 0)) return;
	fin.addInvoice({ customer: form.customer, project: form.project, date: form.date, due_date: form.due_date, gst_rate: Number(form.gst_rate), lines: [{ id: "l", description: form.description, amount: Number(form.amount) }] });
	form.open = false;
}

const pay = reactive({ open: false, inv: null, amount: 0, account: "" });
function openReceive(inv) { Object.assign(pay, { open: true, inv, amount: fin.invoiceOutstanding(inv), account: fin.financeAccounts[0]?.id || "" }); }
function receive() {
	if (!(Number(pay.amount) > 0) || !pay.account) return;
	fin.addInvoiceReceipt(pay.inv.id, pay.amount, pay.account);
	pay.open = false;
}
</script>

<template>
	<DeskPage title="Invoices" :breadcrumbs="breadcrumbs">
		<template #actions><button class="desk-save-btn" @click="form.open = true">+ New Invoice</button></template>
		<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr><th class="text-left px-3 py-2">Invoice</th><th class="text-left px-3 py-2">Customer</th><th class="text-left px-3 py-2">Project</th><th class="text-left px-3 py-2">Due</th><th class="text-left px-3 py-2">Aging</th><th class="text-right px-3 py-2">Total</th><th class="text-right px-3 py-2">Outstanding</th><th class="text-left px-3 py-2">Status</th><th></th></tr>
				</thead>
				<tbody>
					<tr v-for="i in rows" :key="i.id" class="border-t border-ink-100">
						<td class="px-3 py-2 font-mono text-[11px]">{{ i.id }}</td>
						<td class="px-3 py-2 text-ink-900">{{ fin.customerById(i.customer)?.name || i.customer }}</td>
						<td class="px-3 py-2 text-ink-500">{{ fin.projectName(i.project) }}</td>
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(i.due_date) }}</td>
						<td class="px-3 py-2 text-ink-600">{{ fin.agingBucket(i.due_date) }}</td>
						<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(i.total) }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(fin.invoiceOutstanding(i)) }}</td>
						<td class="px-3 py-2"><StatusBadge :status="i.workflow_state" /></td>
						<td class="px-3 py-2 text-right"><button v-if="fin.invoiceOutstanding(i) > 0.5" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="openReceive(i)">Receive</button></td>
					</tr>
				</tbody>
			</table>
		</div>

		<div v-if="form.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="form.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-lg p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">New invoice</h3>
				<div class="grid grid-cols-2 gap-3">
					<DeskField label="Customer" required><DeskSelect v-model="form.customer"><option value="">—</option><option v-for="c in fin.customers" :key="c.id" :value="c.id">{{ c.name }}</option></DeskSelect></DeskField>
					<DeskField label="Project"><DeskSelect v-model="form.project"><option value="">—</option><option v-for="p in fin.projects" :key="p.id" :value="p.id">{{ p.name }}</option></DeskSelect></DeskField>
					<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
					<DeskField label="Due date"><DeskInput v-model="form.due_date" type="date" /></DeskField>
					<DeskField label="GST %"><DeskInput v-model.number="form.gst_rate" type="number" /></DeskField>
					<DeskField label="Amount" required><DeskInput v-model.number="form.amount" type="number" /></DeskField>
					<DeskField label="Description" class="col-span-2"><DeskInput v-model="form.description" /></DeskField>
				</div>
				<div class="flex justify-end gap-2 mt-5"><button class="desk-btn" @click="form.open = false">Cancel</button><button class="desk-save-btn" @click="createInvoice">Create</button></div>
			</div>
		</div>

		<div v-if="pay.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="pay.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-sm p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">Receive payment</h3>
				<div class="space-y-3">
					<DeskField label="Amount"><DeskInput v-model.number="pay.amount" type="number" /></DeskField>
					<DeskField label="Into account"><DeskSelect v-model="pay.account"><option v-for="a in fin.financeAccounts" :key="a.id" :value="a.id">{{ a.name }}</option></DeskSelect></DeskField>
				</div>
				<div class="flex justify-end gap-2 mt-5"><button class="desk-btn" @click="pay.open = false">Cancel</button><button class="desk-save-btn" @click="receive">Receive</button></div>
			</div>
		</div>
	</DeskPage>
</template>
