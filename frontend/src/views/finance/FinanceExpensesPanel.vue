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
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Expenses" }];
const tab = ref("all");
const tabs = [
	{ id: "toverify", label: "To Verify" },
	{ id: "all", label: "All Expenses" },
];
const rows = computed(() => (tab.value === "toverify" ? fin.expensesToVerify : fin.expenses));

const form = reactive({ open: false, date: new Date().toISOString().slice(0, 10), description: "", amount: 0, project: "", expense_account: "", cost_type: "Overhead", paid_from: "" });
function create() {
	if (!form.description.trim() || !(Number(form.amount) > 0)) return;
	fin.addExpense({ date: form.date, description: form.description, amount: Number(form.amount), project: form.project, expense_account: form.expense_account, cost_type: form.cost_type, paid_from: form.paid_from, holder: "USR-005" });
	form.open = false;
}
</script>

<template>
	<DeskPage title="Expenses" :breadcrumbs="breadcrumbs">
		<template #actions><button class="desk-save-btn" @click="form.open = true">+ Log Expense</button></template>
		<div class="border-b border-ink-200 flex mb-4">
			<button v-for="t in tabs" :key="t.id" class="px-3 py-2 text-xs font-medium" :class="tab === t.id ? 'text-brand-600' : 'text-ink-600'" :style="tab === t.id ? 'border-bottom:2px solid currentColor;margin-bottom:-1px;' : 'border-bottom:2px solid transparent;margin-bottom:-1px;'" @click="tab = t.id">{{ t.label }}</button>
		</div>
		<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Description</th><th class="text-left px-3 py-2">Account</th><th class="text-left px-3 py-2">Cost type</th><th class="text-right px-3 py-2">Amount</th><th class="text-left px-3 py-2">Status</th><th></th></tr>
				</thead>
				<tbody>
					<tr v-for="e in rows" :key="e.id" class="border-t border-ink-100">
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(e.date) }}</td>
						<td class="px-3 py-2 text-ink-900">{{ e.description }}</td>
						<td class="px-3 py-2 text-ink-500">{{ e.expense_account }}</td>
						<td class="px-3 py-2 text-ink-600">{{ e.cost_type }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(e.amount) }}</td>
						<td class="px-3 py-2"><StatusBadge :status="e.status" /></td>
						<td class="px-3 py-2 text-right"><button v-if="e.status === 'Draft'" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="fin.submitExpense(e.id)">Verify</button></td>
					</tr>
					<tr v-if="!rows.length"><td colspan="7" class="px-3 py-4 text-center text-ink-400 italic">No expenses.</td></tr>
				</tbody>
			</table>
		</div>

		<div v-if="form.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="form.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-lg p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">Log expense</h3>
				<div class="grid grid-cols-2 gap-3">
					<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
					<DeskField label="Amount" required><DeskInput v-model.number="form.amount" type="number" /></DeskField>
					<DeskField label="Description" required class="col-span-2"><DeskInput v-model="form.description" /></DeskField>
					<DeskField label="Project"><DeskSelect v-model="form.project"><option value="">—</option><option v-for="p in fin.projects" :key="p.id" :value="p.id">{{ p.name }}</option></DeskSelect></DeskField>
					<DeskField label="Cost type"><DeskSelect v-model="form.cost_type"><option>Material</option><option>Labour</option><option>Plant &amp; Machinery</option><option>Subcontract</option><option>Overhead</option></DeskSelect></DeskField>
					<DeskField label="Expense account"><DeskInput v-model="form.expense_account" /></DeskField>
					<DeskField label="Paid from"><DeskSelect v-model="form.paid_from"><option value="">—</option><option v-for="a in fin.financeAccounts" :key="a.id" :value="a.id">{{ a.name }}</option></DeskSelect></DeskField>
				</div>
				<div class="flex justify-end gap-2 mt-5"><button class="desk-btn" @click="form.open = false">Cancel</button><button class="desk-save-btn" @click="create">Log</button></div>
			</div>
		</div>
	</DeskPage>
</template>
