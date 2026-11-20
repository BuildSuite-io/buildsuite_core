<script setup>
// Supplier Quotation Comparison — a Procurement report (buildsuite_core.api.rfq.
// supplier_quotation_comparison). For one request for quotation: every item asked for down
// the side, every submitted quotation across the top, the lowest rate on each row marked. The
// totals say who is cheapest overall, and what the cheapest basket would cost if each item
// were bought from whoever quoted it lowest — often less than any single supplier's total.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ProcurementStatusPill from "@/components/procurement/ProcurementStatusPill.vue";
import { usePermissions } from "@/composables/usePermissions";
import { getComparisonRequests, getSupplierQuotationComparison } from "@/data/rfqApi";
import { showToast } from "@/utils/appToast";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const route = useRoute();
const router = useRouter();
const { canCreate } = usePermissions();

const requests = ref([]);
const rfqId = ref(route.query.rfq || "");
const cmp = ref(null);
const loading = ref(false);
const showAmounts = ref(false);

const rfqOptions = computed(() =>
	requests.value.map((r) => ({
		value: r.name,
		label: r.name,
		hint: [r.subject, __("{0} quoted", [r.quoted])].filter(Boolean).join(" · "),
	}))
);

onMounted(async () => {
	try {
		requests.value = (await getComparisonRequests()) || [];
		// Nothing asked for in the URL: open on the latest request that has a quotation to compare.
		if (!rfqId.value)
			rfqId.value = (requests.value.find((r) => r.quoted) || requests.value[0])?.name || "";
	} catch (err) {
		showToast(err.message || __("Failed to load requests for quotation"), "error");
	}
});

watch(
	rfqId,
	async (id) => {
		if ((route.query.rfq || "") !== (id || ""))
			router.replace({ query: id ? { rfq: id } : {} });
		cmp.value = null;
		if (!id) return;
		loading.value = true;
		try {
			cmp.value = await getSupplierQuotationComparison(id);
		} catch (err) {
			showToast(err.message || __("Failed to load the comparison"), "error");
		} finally {
			loading.value = false;
		}
	},
	{ immediate: true }
);

const several = computed(() => (cmp.value?.totals.length || 0) > 1);
const spread = (r) => (r.low && r.high > r.low ? ((r.high - r.low) / r.low) * 100 : 0);
const isLowest = (r, c) => c && c.rate === r.low;
const bestTotal = computed(
	() => cmp.value?.totals.find((t) => t.quotation === cmp.value.best_quotation) || null
);
const basketSaving = computed(() =>
	bestTotal.value ? +(bestTotal.value.value - cmp.value.basket).toFixed(2) : 0
);

function createPo(quotation) {
	router.push(`/procurement/purchase-orders/new?sq=${encodeURIComponent(quotation)}`);
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Supplier quotation comparison") },
];
</script>

<template>
	<DeskPage
		:title="__('Supplier quotation comparison')"
		:subtitle="__('Item by item, across every supplier who quoted for a request.')"
		:breadcrumbs="breadcrumbs"
		printable
	>
		<div class="flex items-center gap-3 flex-wrap mb-4 print:hidden">
			<div class="w-96" data-test="sqc-request">
				<DeskSearchableSelect
					v-model="rfqId"
					:options="rfqOptions"
					:placeholder="__('— Pick a request for quotation —')"
					:search-placeholder="__('Search requests…')"
				/>
			</div>
			<label class="flex items-center gap-1.5 text-xs text-ink-600 cursor-pointer">
				<input v-model="showAmounts" type="checkbox" />
				{{ __("Show amounts as well as rates") }}
			</label>
		</div>

		<div
			v-if="!cmp"
			class="bg-white border border-ink-200 rounded-lg px-4 py-10 text-center text-sm text-ink-500"
		>
			{{
				loading
					? __("Loading comparison…")
					: requests.length
					? __(
							"Pick a submitted request for quotation to compare what its suppliers quoted."
					  )
					: __(
							"No submitted request for quotation yet. Raise one, record what the suppliers quote, and compare them here."
					  )
			}}
		</div>

		<template v-else>
			<!-- Summary strip -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						{{ __("Request") }}
					</div>
					<DeskLink :to="`/procurement/rfqs/${cmp.rfq.name}`" class="text-sm">{{
						cmp.rfq.name
					}}</DeskLink>
					<div class="text-[10px] text-ink-500 truncate">
						{{ cmp.rfq.project_name || cmp.rfq.project }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						{{ __("Quotations") }}
					</div>
					<div class="text-sm font-semibold text-ink-900 mt-0.5">
						{{ __("{0} of {1} suppliers", [cmp.totals.length, cmp.rfq.suppliers]) }}
					</div>
					<div v-if="cmp.pending.length" class="text-[10px] text-warning-700">
						{{ __("Waiting on {0}", [cmp.pending.join(", ")]) }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						{{ __("Lowest single supplier") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums mt-0.5"
						data-test="sqc-best"
					>
						{{ bestTotal ? fmtINR(bestTotal.value) : "—" }}
					</div>
					<div v-if="bestTotal" class="text-[10px] text-ink-500 truncate">
						{{ bestTotal.supplier_name }}
					</div>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						{{ __("Lowest rate on every item") }}
					</div>
					<div
						class="text-base font-semibold text-ink-900 tabular-nums mt-0.5"
						data-test="sqc-basket"
					>
						{{ cmp.totals.length ? fmtINR(cmp.basket) : "—" }}
					</div>
					<div v-if="basketSaving > 0" class="text-[10px] text-success-700">
						{{ __("{0} less, split across suppliers", [fmtINR(basketSaving)]) }}
					</div>
				</div>
			</div>

			<div
				v-if="!cmp.totals.length"
				class="bg-white border border-ink-200 rounded-lg px-4 py-10 text-center text-sm text-ink-500"
			>
				{{ __("No supplier has a submitted quotation against this request yet.") }}
				<DeskLink :to="`/procurement/rfqs/${cmp.rfq.name}`">{{
					__("Record one from the request's page →")
				}}</DeskLink>
			</div>

			<section
				v-else
				class="bg-white border border-ink-200 rounded-lg overflow-x-auto"
				data-test="sqc-table"
			>
				<table class="w-full text-xs">
					<thead>
						<tr
							class="bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500"
						>
							<th class="text-left px-3 py-2" style="min-width: 220px">
								{{ __("Item") }}
							</th>
							<th class="text-right px-3 py-2 whitespace-nowrap">{{ __("Qty") }}</th>
							<th
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="text-right px-3 py-2 align-top normal-case tracking-normal"
								style="min-width: 160px"
							>
								<DeskLink
									:to="`/procurement/supplier-quotations/${t.quotation}`"
									class="text-xs font-semibold"
									>{{ t.supplier_name }}</DeskLink
								>
								<div class="text-[10px] text-ink-500 font-normal">
									{{ t.quotation
									}}<template v-if="t.valid_till">
										·
										{{
											__("valid till {0}", [fmtDate(t.valid_till)])
										}}</template
									>
								</div>
								<ProcurementStatusPill
									v-if="t.status !== 'Submitted'"
									:status="t.status"
									kind="quotation"
									class="!text-[10px] mt-0.5 inline-block"
								/>
							</th>
							<th class="text-right px-3 py-2 whitespace-nowrap">
								{{ __("Spread") }}
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="r in cmp.rows"
							:key="r.name"
							class="border-b border-ink-100 align-top"
							data-test="sqc-row"
						>
							<td class="px-3 py-2.5">
								<span class="text-ink-900">{{ r.item_name || r.item_code }}</span>
								<span
									v-if="r.description"
									class="block text-[11px] text-ink-500 mt-0.5"
									>{{ r.description }}</span
								>
							</td>
							<td
								class="px-3 py-2.5 text-right tabular-nums text-ink-700 whitespace-nowrap"
							>
								{{ r.qty }} <span class="text-ink-500">{{ r.uom }}</span>
							</td>
							<td
								v-for="(c, i) in r.cells"
								:key="i"
								class="px-3 py-2.5 text-right"
								:class="isLowest(r, c) && several ? 'bg-success-50' : ''"
							>
								<template v-if="c">
									<span
										class="tabular-nums"
										:class="
											isLowest(r, c) && several
												? 'text-success-700 font-semibold'
												: 'text-ink-900'
										"
										>{{ fmtINR(c.rate) }}</span
									>
									<span
										v-if="isLowest(r, c) && several"
										class="ml-1 text-[10px] text-success-700"
										data-test="sqc-lowest"
										>{{ __("Lowest") }}</span
									>
									<div
										v-if="showAmounts"
										class="text-[11px] text-ink-600 tabular-nums"
									>
										{{ fmtINR(c.amount) }}
									</div>
									<div
										v-if="c.lead_time_days != null"
										class="text-[10px] text-ink-500"
									>
										{{ __("{0} days", [c.lead_time_days]) }}
									</div>
								</template>
								<span v-else class="text-ink-400">{{ __("Not quoted") }}</span>
							</td>
							<td
								class="px-3 py-2.5 text-right tabular-nums text-ink-600 whitespace-nowrap"
							>
								{{ spread(r) ? spread(r).toFixed(1) + "%" : "—" }}
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-ink-200">
							<td
								colspan="2"
								class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-ink-700"
							>
								{{ __("Net total") }}
							</td>
							<td
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="px-3 py-2 text-right tabular-nums font-semibold"
								:class="
									t.quotation === cmp.best_quotation && several
										? 'text-success-700'
										: 'text-ink-900'
								"
							>
								{{ fmtINR(t.value) }}
								<div
									v-if="!t.complete"
									class="text-[10px] font-normal text-warning-700"
								>
									{{ __("Not every item quoted") }}
								</div>
							</td>
							<td></td>
						</tr>
						<tr>
							<td
								colspan="2"
								class="px-3 py-1.5 text-right text-[11px] text-ink-600"
							>
								{{ __("Taxes") }}
							</td>
							<td
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="px-3 py-1.5 text-right tabular-nums text-ink-700"
							>
								{{ fmtINR(t.tax) }}
							</td>
							<td></td>
						</tr>
						<tr class="bg-ink-50">
							<td
								colspan="2"
								class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-ink-700"
							>
								{{ __("Grand total") }}
							</td>
							<td
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="px-3 py-2 text-right tabular-nums font-semibold text-ink-900"
							>
								{{ fmtINR(t.grand_total) }}
							</td>
							<td></td>
						</tr>
						<tr>
							<td
								colspan="2"
								class="px-3 py-1.5 text-right text-[11px] text-ink-600"
							>
								{{ __("Lowest on") }}
							</td>
							<td
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="px-3 py-1.5 text-right text-ink-700"
							>
								{{ __("{0} of {1} items", [t.lowest_on, cmp.rows.length]) }}
							</td>
							<td></td>
						</tr>
						<tr v-if="cmp.totals.some((t) => t.payment_terms)">
							<td
								colspan="2"
								class="px-3 py-1.5 text-right text-[11px] text-ink-600"
							>
								{{ __("Payment terms") }}
							</td>
							<td
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="px-3 py-1.5 text-right text-ink-700"
							>
								{{ t.payment_terms || "—" }}
							</td>
							<td></td>
						</tr>
						<tr v-if="canCreate('purchaseOrder')" class="print:hidden">
							<td colspan="2"></td>
							<td
								v-for="t in cmp.totals"
								:key="t.quotation"
								class="px-3 py-2 text-right"
							>
								<button
									type="button"
									class="text-brand-700 hover:underline"
									@click="createPo(t.quotation)"
								>
									{{ __("Create purchase order →") }}
								</button>
							</td>
							<td></td>
						</tr>
					</tfoot>
				</table>
			</section>
		</template>
	</DeskPage>
</template>
