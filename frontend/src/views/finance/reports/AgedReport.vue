<script setup>
import { computed, reactive, ref, onMounted } from "vue";

import DeskInput from "@/components/desk/DeskInput.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { getReceivablesPayables } from "@/data/financeReportApi";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Receivables & Payables" },
];
const BUCKETS = ["Current", "0-30", "31-60", "61-90", "90+"];

const allRecv = ref([]);
const allPay = ref([]);
const loading = ref(true);
const error = ref("");

onMounted(async () => {
	try {
		const d = await getReceivablesPayables();
		allRecv.value = d.receivables || [];
		allPay.value = d.payables || [];
	} catch (e) {
		error.value = e.message || "Failed to load.";
	} finally {
		loading.value = false;
	}
});

const BLANK = { q: "", bucket: "", side: "" };
const f = reactive({ ...BLANK });
const anyFilter = computed(() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]));
function clearFilters() {
	Object.assign(f, BLANK);
}
const keep = (r) =>
	(!f.q ||
		String(r.party || "")
			.toLowerCase()
			.includes(f.q.trim().toLowerCase()) ||
		String(r.id || "")
			.toLowerCase()
			.includes(f.q.trim().toLowerCase())) &&
	(!f.bucket || r.bucket === f.bucket);
const byBucket = (a, b) => BUCKETS.indexOf(b.bucket) - BUCKETS.indexOf(a.bucket);

const receivables = computed(() => allRecv.value.filter(keep).slice().sort(byBucket));
const payables = computed(() =>
	allPay.value
		.filter((r) => r.outstanding > 0.01)
		.filter(keep)
		.slice()
		.sort(byBucket)
);

function bucketCls(b) {
	return b === "Current"
		? "bg-ink-100 text-ink-500"
		: b === "0-30"
		? "bg-warning-50 text-warning-700"
		: b === "31-60"
		? "bg-warning-100 text-warning-700"
		: "bg-danger-50 text-danger-700";
}
function bucketTotals(rows) {
	const m = Object.fromEntries(BUCKETS.map((b) => [b, 0]));
	for (const r of rows) m[r.bucket] += Number(r.outstanding) || 0;
	return m;
}
const recvTotals = computed(() => bucketTotals(receivables.value));
const payTotals = computed(() => bucketTotals(payables.value));
const recvTotal = computed(() =>
	receivables.value.reduce((a, r) => a + (Number(r.outstanding) || 0), 0)
);
const payTotal = computed(() =>
	payables.value.reduce((a, r) => a + (Number(r.outstanding) || 0), 0)
);
const showRecv = computed(() => f.side !== "payables");
const showPay = computed(() => f.side !== "receivables");
const shownCount = computed(
	() =>
		(showRecv.value ? receivables.value.length : 0) +
		(showPay.value ? payables.value.length : 0)
);
</script>

<template>
	<DeskPage title="Receivables & Payables" :breadcrumbs="breadcrumbs">
		<div v-if="loading" class="text-sm text-ink-500 italic py-10 text-center">Loading…</div>
		<div v-else-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<div v-else class="space-y-6">
			<ReportFilters
				:active="anyFilter"
				:shown="shownCount"
				noun="rows"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Find</span
					>
					<DeskInput v-model="f.q" placeholder="Party or document…" class="!w-52" />
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Bucket</span
					>
					<DeskSelect v-model="f.bucket" class="!w-32">
						<option value="">All</option>
						<option v-for="b in BUCKETS" :key="b" :value="b">{{ b }}</option>
					</DeskSelect>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Show</span
					>
					<DeskSelect v-model="f.side" class="!w-40">
						<option value="">Both</option>
						<option value="receivables">Receivables only</option>
						<option value="payables">Payables only</option>
					</DeskSelect>
				</label>
			</ReportFilters>

			<!-- Receivables -->
			<section v-if="showRecv">
				<div class="flex items-center justify-between mb-2">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Receivables (aged)
					</h3>
					<div class="text-sm">
						<span class="text-ink-500">Total</span>
						<span class="font-semibold text-ink-900 tabular-nums">
							{{ fmtINR(recvTotal) }}</span
						>
					</div>
				</div>
				<div class="grid grid-cols-5 gap-2 mb-2">
					<div
						v-for="b in BUCKETS"
						:key="b"
						class="bg-white border border-ink-200 rounded-md px-2 py-1.5 text-center"
					>
						<div class="text-[9px] uppercase tracking-wider text-ink-500">{{ b }}</div>
						<div class="text-xs font-semibold text-ink-900 tabular-nums">
							{{ fmtINR(recvTotals[b]) }}
						</div>
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<table v-if="receivables.length" class="w-full text-xs">
						<thead
							class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-100"
						>
							<tr>
								<th class="text-left px-4 py-2">Customer</th>
								<th class="text-left px-4 py-2">Due</th>
								<th class="text-left px-4 py-2">Bucket</th>
								<th class="text-right px-4 py-2">Outstanding</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="r in receivables"
								:key="r.id"
								class="border-b border-ink-100 last:border-0"
							>
								<td class="px-4 py-2 text-ink-900">{{ r.party }}</td>
								<td class="px-4 py-2 text-ink-500">{{ fmtDate(r.due) }}</td>
								<td class="px-4 py-2">
									<span
										class="text-[10px] px-1.5 py-0.5 rounded-full"
										:class="bucketCls(r.bucket)"
										>{{ r.bucket }}</span
									>
								</td>
								<td
									class="px-4 py-2 text-right tabular-nums font-medium text-ink-900"
								>
									{{ fmtINR(r.outstanding) }}
								</td>
							</tr>
						</tbody>
					</table>
					<div v-else class="px-4 py-6 text-center text-xs text-ink-400 italic">
						No outstanding receivables.
					</div>
				</div>
			</section>

			<!-- Payables -->
			<section v-if="showPay">
				<div class="flex items-center justify-between mb-2">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Payables (aged)
					</h3>
					<div class="text-sm">
						<span class="text-ink-500">Total</span>
						<span class="font-semibold text-ink-900 tabular-nums">
							{{ fmtINR(payTotal) }}</span
						>
					</div>
				</div>
				<div class="grid grid-cols-5 gap-2 mb-2">
					<div
						v-for="b in BUCKETS"
						:key="b"
						class="bg-white border border-ink-200 rounded-md px-2 py-1.5 text-center"
					>
						<div class="text-[9px] uppercase tracking-wider text-ink-500">{{ b }}</div>
						<div class="text-xs font-semibold text-ink-900 tabular-nums">
							{{ fmtINR(payTotals[b]) }}
						</div>
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<table v-if="payables.length" class="w-full text-xs">
						<thead
							class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-100"
						>
							<tr>
								<th class="text-left px-4 py-2">Supplier</th>
								<th class="text-left px-4 py-2">Due</th>
								<th class="text-left px-4 py-2">Bucket</th>
								<th class="text-right px-4 py-2">Retention</th>
								<th class="text-right px-4 py-2">Outstanding</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="r in payables"
								:key="r.kind + r.id"
								class="border-b border-ink-100 last:border-0"
							>
								<td class="px-4 py-2">
									<div class="flex items-center gap-1.5">
										<span class="text-ink-900">{{ r.party }}</span>
										<span
											v-if="r.kind === 'subcontractor'"
											class="text-[9px] px-1.5 py-0.5 bg-info-50 text-info-700 rounded-full uppercase tracking-wider"
											>Subcontractor</span
										>
									</div>
								</td>
								<td class="px-4 py-2 text-ink-500">{{ fmtDate(r.due) }}</td>
								<td class="px-4 py-2">
									<span
										class="text-[10px] px-1.5 py-0.5 rounded-full"
										:class="bucketCls(r.bucket)"
										>{{ r.bucket }}</span
									>
								</td>
								<td class="px-4 py-2 text-right tabular-nums text-ink-500">
									{{ r.retention > 0 ? fmtINR(r.retention) : "—" }}
								</td>
								<td
									class="px-4 py-2 text-right tabular-nums font-medium text-ink-900"
								>
									{{ fmtINR(r.outstanding) }}
								</td>
							</tr>
						</tbody>
					</table>
					<div v-else class="px-4 py-6 text-center text-xs text-ink-400 italic">
						No outstanding payables.
					</div>
				</div>
			</section>
		</div>
	</DeskPage>
</template>
