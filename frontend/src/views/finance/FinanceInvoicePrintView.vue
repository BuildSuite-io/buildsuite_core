<script setup>
// Sales Invoice — printable document rendered inside the SPA (mirrors the
// Subcontractor Work Order print workflow). The invoice detail's Print/PDF button
// routes here; a sticky control bar (Back + Export PDF, both hidden in print) sits
// above a Vue-styled invoice. PDF export is window.print() + the global @media print
// rules in style.css (hide chrome, white A4). Data comes from the same getInvoice the
// detail screen uses — no new backend endpoint.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getInvoice } from "@/data/invoiceApi";
import { showToast } from "@/utils/appToast";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();

const inv = ref(null);
const loading = ref(true);

const state = computed(() => {
	if (!inv.value) return "";
	return { 0: "Draft", 1: "Submitted", 2: "Cancelled" }[inv.value.docstatus] || "Draft";
});
const payment = computed(
	() => inv.value?.payment || { invoiced: 0, received: 0, outstanding: 0, status: "Draft" }
);
const discountLabel = computed(() =>
	inv.value?.additional_discount_on === "Grand Total"
		? "Discount (on grand total)"
		: "Discount (on net total)"
);

function generatedOnLabel() {
	return new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}
function printDoc() {
	window.print();
}
function backToInvoice() {
	router.push(`/project-finance/invoices/${props.id}`);
}

async function load() {
	loading.value = true;
	try {
		inv.value = await getInvoice(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load invoice", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });
</script>

<template>
	<div class="bg-white min-h-full report-root">
		<!-- ===== Control bar (hidden in print) ===== -->
		<header class="border-b border-ink-200 bg-white sticky top-0 z-10 print:hidden">
			<div class="max-w-4xl mx-auto px-6 py-3 flex items-center gap-3">
				<button
					class="text-xs text-ink-600 hover:text-ink-900 flex items-center gap-1"
					@click="backToInvoice"
				>
					<span>←</span><span>Back to invoice</span>
				</button>
				<div class="ml-auto flex items-center gap-2">
					<StatusBadge v-if="inv" :status="state" size="xs" />
					<button
						v-if="inv"
						class="text-xs px-3 py-1.5 rounded bg-ink-900 text-white hover:bg-ink-800 flex items-center gap-1.5"
						title="Opens the browser print dialog. Pick 'Save as PDF' to export."
						@click="printDoc"
					>
						<svg
							class="w-3.5 h-3.5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<polyline points="6 9 6 2 18 2 18 9" />
							<path
								d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
							/>
							<rect x="6" y="14" width="12" height="8" />
						</svg>
						<span>Export PDF</span>
					</button>
				</div>
			</div>
		</header>

		<!-- ===== Document ===== -->
		<main v-if="inv" class="report-content max-w-4xl mx-auto px-6 py-8 text-ink-900">
			<!-- Letterhead -->
			<section
				class="report-section flex items-start justify-between gap-6 pb-4 mb-6 border-b-2 border-ink-300"
			>
				<div class="flex items-center gap-3 min-w-0">
					<div
						class="w-12 h-12 rounded border border-dashed border-ink-300 flex items-center justify-center text-[9px] text-ink-400 flex-shrink-0"
					>
						LOGO
					</div>
					<div class="min-w-0">
						<div class="text-lg font-semibold truncate">{{ inv.company || "—" }}</div>
						<div class="text-[11px] text-ink-400 italic">
							Registered address · GSTIN — to be configured (Letter Head)
						</div>
					</div>
				</div>
				<div class="text-right flex-shrink-0">
					<div class="text-xl font-bold tracking-wide">TAX INVOICE</div>
					<div
						v-if="state === 'Draft'"
						class="text-[11px] font-bold text-warning-700 uppercase tracking-widest mt-0.5"
					>
						Draft — not posted
					</div>
					<div
						v-else-if="state === 'Cancelled'"
						class="text-[11px] font-bold text-danger-700 uppercase tracking-widest mt-0.5"
					>
						Cancelled
					</div>
				</div>
			</section>

			<!-- Bill-to + meta -->
			<section class="report-section grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
				<div>
					<div
						class="text-[10px] uppercase tracking-wider text-ink-500 font-semibold mb-1"
					>
						Bill to
					</div>
					<div class="text-sm font-semibold">
						{{ inv.customer_name || inv.customer }}
					</div>
					<div v-if="inv.customer_gstin" class="text-xs text-ink-600 font-mono mt-0.5">
						GSTIN: {{ inv.customer_gstin }}
					</div>
					<div class="text-[11px] text-ink-400 italic mt-0.5">
						Postal address — from Address record
					</div>
				</div>
				<div class="text-sm md:justify-self-end w-full md:w-64">
					<div class="grid grid-cols-2 gap-y-1">
						<span class="text-ink-500 text-xs">Invoice no.</span>
						<span class="text-ink-900 font-mono text-xs text-right">{{
							inv.name
						}}</span>
						<span class="text-ink-500 text-xs">Invoice date</span>
						<span class="text-ink-900 text-xs text-right">{{
							fmtDate(inv.date)
						}}</span>
						<span class="text-ink-500 text-xs">Due date</span>
						<span class="text-ink-900 text-xs text-right">{{
							fmtDate(inv.due_date)
						}}</span>
						<template v-if="inv.project">
							<span class="text-ink-500 text-xs">Project</span>
							<span class="text-ink-900 text-xs text-right">{{
								inv.project_name || inv.project
							}}</span>
						</template>
					</div>
				</div>
			</section>

			<!-- Lines -->
			<section class="report-section mb-6">
				<table class="w-full text-sm">
					<thead>
						<tr
							class="border-y border-ink-300 text-[10px] uppercase tracking-wider text-ink-500"
						>
							<th class="text-left py-2 pr-2 w-8">#</th>
							<th class="text-left py-2 pr-2">Description</th>
							<th class="text-right py-2 px-2 w-20">Qty</th>
							<th class="text-right py-2 px-2 w-28">Rate</th>
							<th class="text-right py-2 pl-2 w-32">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(l, i) in inv.items" :key="i" class="border-b border-ink-100">
							<td class="py-2 pr-2 text-ink-500 text-xs align-top">{{ i + 1 }}</td>
							<td class="py-2 pr-2 text-ink-900">{{ l.description }}</td>
							<td class="py-2 px-2 text-right tabular-nums text-ink-700">
								{{ l.qty }}
							</td>
							<td class="py-2 px-2 text-right tabular-nums text-ink-700">
								{{ fmtINR(l.rate) }}
							</td>
							<td class="py-2 pl-2 text-right tabular-nums text-ink-900">
								{{ fmtINR(l.amount) }}
							</td>
						</tr>
					</tbody>
				</table>
			</section>

			<!-- Totals waterfall -->
			<section class="report-section flex justify-end mb-8">
				<div class="w-80 text-sm space-y-1">
					<div class="flex justify-between text-ink-600">
						<span>Net total</span
						><span class="tabular-nums">{{ fmtINR(inv.net_total) }}</span>
					</div>
					<div
						v-if="(inv.discount_amount || 0) > 0"
						class="flex justify-between text-ink-600"
					>
						<span>{{ discountLabel }}</span>
						<span class="tabular-nums">− {{ fmtINR(inv.discount_amount) }}</span>
					</div>
					<div
						v-for="(row, i) in inv.taxes || []"
						:key="i"
						class="flex justify-between text-ink-600"
					>
						<span>{{ row.description || row.account_head }} ({{ row.rate }}%)</span>
						<span class="tabular-nums">{{ fmtINR(row.tax_amount) }}</span>
					</div>
					<div
						class="flex justify-between font-semibold text-ink-900 border-t border-ink-300 pt-1.5"
					>
						<span>Invoice total</span
						><span class="tabular-nums">{{ fmtINR(inv.grand_total) }}</span>
					</div>
					<template v-if="state === 'Submitted'">
						<div class="flex justify-between text-ink-600">
							<span>Received</span
							><span class="tabular-nums">{{ fmtINR(payment.received) }}</span>
						</div>
						<div
							class="flex justify-between font-semibold"
							:class="
								payment.outstanding > 0.01 ? 'text-danger-700' : 'text-success-700'
							"
						>
							<span>Balance due</span>
							<span class="tabular-nums">{{ fmtINR(payment.outstanding) }}</span>
						</div>
					</template>
				</div>
			</section>

			<!-- Terms -->
			<section class="report-section mb-10">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-semibold mb-1">
					Terms
				</div>
				<p
					v-if="inv.terms"
					class="text-xs text-ink-600 leading-relaxed whitespace-pre-line"
				>
					{{ inv.terms }}
				</p>
				<p v-else class="text-xs text-ink-600 leading-relaxed">
					Payment due by {{ fmtDate(inv.due_date) }}. This is a computer-generated
					invoice.
				</p>
			</section>

			<!-- Signatures -->
			<section class="report-section grid grid-cols-2 gap-16">
				<div class="pt-10 border-t border-ink-300 text-xs text-ink-600">Prepared by</div>
				<div class="pt-10 border-t border-ink-300 text-xs text-ink-600 text-right">
					For {{ inv.company || "Company" }} — Authorised signatory
				</div>
			</section>

			<div class="text-[10px] text-ink-400 text-center mt-8 pt-3 border-t border-ink-100">
				Generated on {{ generatedOnLabel() }} · {{ inv.name }}
			</div>
		</main>

		<!-- Loading / not found -->
		<main
			v-else-if="loading"
			class="max-w-4xl mx-auto px-6 py-16 text-center text-sm text-ink-500"
		>
			Loading…
		</main>
		<main v-else class="max-w-4xl mx-auto px-6 py-16 text-center">
			<div class="text-sm text-ink-700 mb-2">
				No invoice with id <span class="font-mono">{{ id }}</span
				>.
			</div>
			<button class="text-xs text-brand-700 hover:underline" @click="backToInvoice">
				← Back to invoice
			</button>
		</main>
	</div>
</template>
