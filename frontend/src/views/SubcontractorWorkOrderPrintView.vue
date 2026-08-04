<script setup>
// Subcontractor Work Order — printable document rendered inside the SPA.
//
// Mirrors the prototype's in-app print workflow: the WO detail's "Print / PDF"
// button routes here; a sticky control bar (Back + Export PDF, both hidden in
// print) sits above a Vue-styled document surface. PDF export is `window.print()`
// + the global @media print rules in style.css, which hide DeskShell chrome
// (.print:hidden / aside / header.h-12), force a white page and set A4. The
// browser's own "Save as PDF" does the export — no new dependency.
//
// The layout is the visual twin of the seeded Frappe "Subcontractor Work Order"
// Print Format + "BuildSuite Standard" Letter Head (used for Desk/server PDF).

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { getWoPrintData } from "@/data/subcontractApi";
import { showToast } from "@/utils/appToast";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtINR, fmtDate } from "@/utils/format";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();

const wo = ref(null);
const loading = ref(true);

const sub = computed(() => wo.value?.subcontractor_detail || null);
const proj = computed(() => wo.value?.project_detail || null);
const company = computed(() => wo.value?.company || null);

const retentionAmount = computed(() => {
	if (!wo.value) return 0;
	return ((Number(wo.value.total_value) || 0) * (Number(wo.value.retention_percent) || 0)) / 100;
});
const netOfRetention = computed(
	() => (Number(wo.value?.total_value) || 0) - retentionAmount.value
);

function generatedOnLabel() {
	return new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

function printDoc() {
	window.print();
}
function backToWO() {
	router.push(`/subcontractor-work-orders/${props.id}`);
}

async function load() {
	loading.value = true;
	try {
		wo.value = await getWoPrintData(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load work order", "error");
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
					@click="backToWO"
					class="text-xs text-ink-600 hover:text-ink-900 flex items-center gap-1"
				>
					<span>←</span><span>Back to work order</span>
				</button>
				<button
					v-if="wo"
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
						<path
							d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
						/>
						<rect x="6" y="14" width="12" height="8" />
					</svg>
					<span>Export PDF</span>
				</button>
			</div>
		</header>

		<!-- ===== Document ===== -->
		<main v-if="wo" class="report-content max-w-4xl mx-auto px-6 py-8 text-ink-900">
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
					<div class="text-xl font-bold tracking-wide">WORK ORDER</div>
					<div class="text-sm font-medium text-ink-700 mt-0.5">{{ wo.name }}</div>
					<div class="text-xs text-ink-500 mt-0.5">{{ fmtDate(wo.date) }}</div>
					<div class="mt-1 flex justify-end"><StatusBadge :status="wo.status" /></div>
				</div>
			</section>

			<!-- Party blocks -->
			<section class="report-section grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
				<div class="border border-ink-200 rounded-lg p-4">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1.5">
						Issued by
					</div>
					<div class="text-sm font-semibold">{{ company || "—" }}</div>
					<div class="text-xs text-ink-400 italic mt-0.5">
						Address — to be configured
					</div>
				</div>
				<div class="border border-ink-200 rounded-lg p-4">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1.5">
						To — Subcontractor
					</div>
					<div class="text-sm font-semibold">
						{{ wo.subcontractor_name || wo.subcontractor || "—" }}
					</div>
					<div v-if="sub?.trade" class="text-xs text-ink-600 mt-0.5">
						{{ sub.trade }}
					</div>
					<div class="text-xs text-ink-600 mt-1 space-y-0.5">
						<div v-if="sub?.contact_person">Attn: {{ sub.contact_person }}</div>
						<div v-if="sub?.phone || sub?.email">
							<span v-if="sub?.phone">{{ sub.phone }}</span>
							<span v-if="sub?.phone && sub?.email"> · </span>
							<span v-if="sub?.email">{{ sub.email }}</span>
						</div>
						<div v-if="sub?.tax_id || sub?.secondary_tax_id" class="text-ink-500">
							<span v-if="sub?.tax_id">Tax ID: {{ sub.tax_id }}</span>
							<span v-if="sub?.tax_id && sub?.secondary_tax_id"> · </span>
							<span v-if="sub?.secondary_tax_id"
								>Sec. Tax ID: {{ sub.secondary_tax_id }}</span
							>
						</div>
					</div>
				</div>
			</section>

			<!-- Meta strip -->
			<section class="report-section grid grid-cols-2 md:grid-cols-4 gap-3 mb-6 text-xs">
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						Against project
					</div>
					<div class="font-medium mt-0.5">{{ wo.project_name || wo.project }}</div>
					<div class="text-ink-500">
						{{ proj?.custom_project_id
						}}<span v-if="proj?.location"> · {{ proj.location }}</span>
					</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Client</div>
					<div class="font-medium mt-0.5">{{ proj?.customer || "—" }}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						Delivery type
					</div>
					<div class="font-medium mt-0.5">{{ wo.delivery_type || "—" }}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Retention</div>
					<div class="font-medium mt-0.5">{{ wo.retention_percent || 0 }}%</div>
				</div>
			</section>

			<!-- Schedule of values -->
			<section class="report-section mb-6">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
					Schedule of values
				</h2>
				<table class="w-full text-xs border border-ink-200 rounded-lg overflow-hidden">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2 w-8">#</th>
							<th class="text-left px-3 py-2">Scope of work</th>
							<th class="text-left px-3 py-2">Cost code</th>
							<th class="text-right px-3 py-2">Qty</th>
							<th class="text-left px-3 py-2">UOM</th>
							<th class="text-right px-3 py-2">Rate</th>
							<th class="text-right px-3 py-2">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(line, idx) in wo.lines"
							:key="line.name || idx"
							class="border-t border-ink-100 align-top"
						>
							<td class="px-3 py-2 text-ink-500">{{ idx + 1 }}</td>
							<td class="px-3 py-2">{{ line.scope }}</td>
							<td class="px-3 py-2 text-ink-600">
								{{ line.cost_code_label || "—" }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ line.qty }}</td>
							<td class="px-3 py-2">{{ line.uom }}</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ fmtINR(line.rate) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums font-medium">
								{{ fmtINR(line.amount) }}
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-ink-200 bg-ink-50">
							<td
								colspan="6"
								class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-ink-700"
							>
								Total order value
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-sm font-semibold">
								{{ fmtINR(wo.total_value) }}
							</td>
						</tr>
					</tfoot>
				</table>
			</section>

			<!-- Totals + terms -->
			<section class="report-section grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
				<!-- Terms print only when the WO has them — no heading, no default
				     boilerplate when the field is empty. -->
				<div v-if="wo.terms" class="text-xs text-ink-600">
					<h3
						class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-1.5"
					>
						Terms &amp; conditions
					</h3>
					<div class="whitespace-pre-line leading-relaxed">{{ wo.terms }}</div>
				</div>
				<div
					class="border border-ink-200 rounded-lg p-4 text-xs self-start md:col-start-2"
				>
					<div class="flex justify-between py-1">
						<span class="text-ink-500">Total order value</span>
						<span class="tabular-nums font-medium">{{ fmtINR(wo.total_value) }}</span>
					</div>
					<div class="flex justify-between py-1">
						<span class="text-ink-500">Retention ({{ wo.retention_percent }}%)</span>
						<span class="tabular-nums text-danger-700"
							>− {{ fmtINR(retentionAmount) }}</span
						>
					</div>
					<div class="flex justify-between py-1.5 border-t border-ink-200 mt-1">
						<span class="font-semibold">Net of retention</span>
						<span class="tabular-nums font-semibold">{{
							fmtINR(netOfRetention)
						}}</span>
					</div>
				</div>
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
						For {{ wo.subcontractor_name || wo.subcontractor || "—" }}
					</div>
					<div class="text-[10px] text-ink-400 mt-0.5">Accepted · Date</div>
				</div>
			</section>

			<!-- Footer -->
			<div class="text-[10px] text-ink-400 text-center pt-3 border-t border-ink-100">
				Generated on {{ generatedOnLabel() }} · {{ wo.name }}
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
				No work order with id <span class="font-mono">{{ id }}</span
				>.
			</div>
			<button @click="backToWO" class="text-xs text-brand-700 hover:underline">
				← Back to work order
			</button>
		</main>
	</div>
</template>
