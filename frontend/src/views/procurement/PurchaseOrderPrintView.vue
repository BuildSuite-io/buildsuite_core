<script setup>
// Purchase Order — printable document rendered inside the SPA (prototype S234).
//
// Mirrors the Subcontractor Work Order print workflow: the PO detail's "Print /
// PDF" button routes here; a sticky control bar (Back + Export PDF, both hidden
// in print) sits above a Vue-styled document surface. PDF export is
// `window.print()` + the global @media print rules in style.css, which hide the
// DeskShell chrome (.print:hidden / aside / header.h-12), force a white page and
// set A4. The browser's own "Save as PDF" does the export — no new dependency.
//
// The layout is the visual twin of the seeded Frappe "Purchase Order" Print
// Format + "BuildSuite Standard" Letter Head (used for Desk/server PDF).

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getPoPrintData } from "@/data/procurementApi";
import { showToast } from "@/utils/appToast";
import { fmtINR, fmtDate } from "@/utils/format";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();

const po = ref(null);
const loading = ref(true);

const sup = computed(() => po.value?.supplier_detail || null);
const proj = computed(() => po.value?.project_detail || null);
const company = computed(() => po.value?.company || null);

function generatedOnLabel() {
	return new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

function printDoc() {
	window.print();
}
function backToPo() {
	router.push(`/procurement/purchase-orders/${props.id}`);
}

async function load() {
	loading.value = true;
	try {
		po.value = await getPoPrintData(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load purchase order", "error");
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
					@click="backToPo"
					class="text-xs text-ink-600 hover:text-ink-900 flex items-center gap-1"
				>
					<span>←</span><span>Back to purchase order</span>
				</button>
				<button
					v-if="po"
					@click="printDoc"
					class="ml-auto text-xs px-3 py-1.5 rounded bg-ink-900 text-white hover:bg-ink-800 flex items-center gap-1.5"
					title="Opens the browser print dialog. Pick 'Save as PDF' to export."
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
						<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
						<rect x="6" y="14" width="12" height="8" />
					</svg>
					<span>Export PDF</span>
				</button>
			</div>
		</header>

		<!-- ===== Document ===== -->
		<main v-if="po" class="report-content max-w-4xl mx-auto px-6 py-8 text-ink-900">
			<!-- Letterhead -->
			<section
				class="report-section flex items-start justify-between gap-6 pb-4 mb-6 border-b-2 border-ink-300"
			>
				<div class="min-w-0">
					<div class="flex items-center gap-3">
						<div
							class="w-12 h-12 rounded border border-dashed border-ink-300 flex items-center justify-center text-[9px] text-ink-400 flex-shrink-0"
						>
							LOGO
						</div>
						<div class="min-w-0">
							<div class="text-lg font-semibold truncate">{{ company || "—" }}</div>
							<div class="text-[11px] text-ink-400 italic">
								Registered address · GSTIN — to be configured (Letter Head)
							</div>
						</div>
					</div>
				</div>
				<div class="text-right flex-shrink-0">
					<div class="text-xl font-bold tracking-wide">PURCHASE ORDER</div>
					<div class="text-sm font-medium text-ink-700 mt-0.5">{{ po.name }}</div>
					<div class="text-xs text-ink-500 mt-0.5">{{ fmtDate(po.transaction_date) }}</div>
				</div>
			</section>

			<!-- Party blocks -->
			<section class="report-section grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
				<div class="border border-ink-200 rounded-lg p-4">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1.5">
						Ordered by
					</div>
					<div class="text-sm font-semibold">{{ company || "—" }}</div>
					<div class="text-xs text-ink-400 italic mt-0.5">Address — to be configured</div>
				</div>
				<div class="border border-ink-200 rounded-lg p-4">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1.5">
						To — Supplier
					</div>
					<div class="text-sm font-semibold">{{ po.supplier_name || po.supplier }}</div>
					<div v-if="sup" class="text-xs text-ink-600 mt-1 space-y-0.5">
						<div v-if="sup.contact_person">Attn: {{ sup.contact_person }}</div>
						<div v-if="sup.phone || sup.email">
							<span v-if="sup.phone">{{ sup.phone }}</span>
							<span v-if="sup.phone && sup.email"> · </span>
							<span v-if="sup.email">{{ sup.email }}</span>
						</div>
						<div v-if="sup.tax_id" class="text-ink-500">Tax ID: {{ sup.tax_id }}</div>
					</div>
				</div>
			</section>

			<!-- Meta strip -->
			<section class="report-section grid grid-cols-2 md:grid-cols-3 gap-3 mb-6 text-xs">
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						Deliver to project
					</div>
					<div class="font-medium mt-0.5">{{ po.project_name || po.project }}</div>
					<div class="text-ink-500">
						{{ proj?.custom_project_id
						}}<span v-if="proj?.location"> · {{ proj.location }}</span>
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Required by</div>
					<div class="font-medium mt-0.5">
						{{ po.schedule_date ? fmtDate(po.schedule_date) : "—" }}
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Order date</div>
					<div class="font-medium mt-0.5">{{ fmtDate(po.transaction_date) }}</div>
				</div>
			</section>

			<!-- Order lines -->
			<section class="report-section mb-6">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
					Order items
				</h2>
				<table class="w-full text-xs border border-ink-200 rounded-lg overflow-hidden">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2 w-8">#</th>
							<th class="text-left px-3 py-2">Item</th>
							<th class="text-right px-3 py-2">Qty</th>
							<th class="text-left px-3 py-2">UOM</th>
							<th class="text-right px-3 py-2">Rate</th>
							<th class="text-right px-3 py-2">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(line, idx) in po.items"
							:key="line.name || idx"
							class="border-t border-ink-100 align-top"
						>
							<td class="px-3 py-2 text-ink-500">{{ idx + 1 }}</td>
							<td class="px-3 py-2">
								{{ line.item_name || line.item_code }}
								<div
									v-if="line.description && line.description !== line.item_name"
									class="text-[10px] text-ink-500 mt-0.5"
								>
									{{ line.description }}
								</div>
							</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ line.qty }}</td>
							<td class="px-3 py-2">{{ line.uom }}</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(line.rate) }}</td>
							<td class="px-3 py-2 text-right tabular-nums font-medium">
								{{ fmtINR(line.amount) }}
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-ink-200 bg-ink-50">
							<td
								colspan="5"
								class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-ink-700"
							>
								Total order value
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-sm font-semibold">
								{{ fmtINR(po.grand_total) }}
							</td>
						</tr>
					</tfoot>
				</table>
			</section>

			<!-- Terms — the PO's own terms print when set; the generic boilerplate is
			     the no-terms fallback. -->
			<section class="report-section mb-8 text-xs text-ink-600">
				<h3 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-1.5">
					Terms &amp; conditions
				</h3>
				<div v-if="po.terms" class="whitespace-pre-line leading-relaxed">{{ po.terms }}</div>
				<ul v-else class="list-disc pl-4 space-y-1 leading-relaxed">
					<li>
						Deliver to the project site named above{{
							po.schedule_date ? ` on or before ${fmtDate(po.schedule_date)}` : ""
						}}. Part deliveries are accepted against this order.
					</li>
					<li>
						Each delivery must carry a challan quoting this PO number; quantities are
						confirmed at site on receipt.
					</li>
					<li>
						Material not conforming to the ordered specification may be rejected at site at
						the supplier's cost.
					</li>
					<li>Invoices must reference this PO and the site-acknowledged receipt quantities.</li>
				</ul>
			</section>

			<!-- Signatures -->
			<section class="report-section grid grid-cols-2 gap-8 mb-6">
				<div>
					<div class="border-t border-ink-400 pt-1.5 mt-10 text-xs text-ink-600">
						For {{ company || "—" }}
					</div>
					<div class="text-[10px] text-ink-400 mt-0.5">Authorised signatory · Date</div>
				</div>
				<div>
					<div class="border-t border-ink-400 pt-1.5 mt-10 text-xs text-ink-600">
						For {{ po.supplier_name || po.supplier }}
					</div>
					<div class="text-[10px] text-ink-400 mt-0.5">Acknowledged · Date</div>
				</div>
			</section>

			<!-- Footer -->
			<div class="text-[10px] text-ink-400 text-center pt-3 border-t border-ink-100">
				Generated on {{ generatedOnLabel() }} · {{ po.name }}
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
				No purchase order with id <span class="font-mono">{{ id }}</span>.
			</div>
			<button @click="backToPo" class="text-xs text-brand-700 hover:underline">
				← Back to purchase order
			</button>
		</main>
	</div>
</template>
