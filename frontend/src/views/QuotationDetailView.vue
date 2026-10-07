<script setup>
import { computed, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useConfirm } from "@/composables/useConfirm";
import { usePageTitle } from "@/composables/usePageTitle";
import { showToast } from "@/utils/appToast";
import { fmtCurrency, fmtDate, daysBetween } from "@/utils/format";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import StatusBadge from "@/components/StatusBadge.vue";

const props = defineProps({ id: String });
const adapter = createDataAdapter(useDataStore());
const router = useRouter();
const confirmDialog = useConfirm();

// The id can change without the component being torn down (one quotation linking to another),
// so the read follows the id rather than being taken once in setup().
const resource = ref(null);
watch(() => props.id, (id) => (resource.value = adapter.read("Quotation", id)), {
	immediate: true,
});

const doc = computed(() => resource.value?.doc || null);

const subtitle = computed(() =>
	[props.id, doc.value?.party_name, doc.value?.customer_type].filter(Boolean).join(" · "),
);

// Counted from today: what is left is the number worth acting on.
const daysLeft = computed(() => {
	const validTill = doc.value?.valid_till;
	if (!validTill) return null;
	return daysBetween(new Date().toISOString().slice(0, 10), validTill);
});

const validityNote = computed(() => {
	const n = daysLeft.value;
	if (n === null) return "";
	if (n < 0) {
		const d = -n;
		return d === 1 ? __("expired {0} day ago", [d]) : __("expired {0} days ago", [d]);
	}
	if (n === 0) return __("expires today");
	return n === 1 ? __("{0} day left", [n]) : __("{0} days left", [n]);
});

const lines = computed(() => doc.value?.items || []);

const lineCount = computed(() => {
	const n = lines.value.length;
	return n === 1 ? __("{0} line", [n]) : __("{0} lines", [n]);
});

const busy = ref(false);

async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete {0}?", [props.id]),
		message: __("This cannot be undone."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		await adapter.remove("Quotation", props.id);
		router.push("/quotations");
	} catch (err) {
		showToast(err.message || __("Could not delete the quotation"), "error");
	} finally {
		busy.value = false;
	}
}

usePageTitle(() => doc.value?.title || props.id);

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Estimation"), to: "/estimation" },
	{ label: __("Quotations"), to: "/quotations" },
	{ label: props.id },
]);
</script>

<template>
	<DeskPage v-if="doc" :title="doc.title || id" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink :to="`/quotations/${encodeURIComponent(id)}/print`"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px">
				{{ __("Print / PDF") }}
			</RouterLink>
			<RouterLink :to="`/quotations/${encodeURIComponent(id)}/edit`"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px">
				{{ __("Edit") }}
			</RouterLink>
			<button type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px" :disabled="busy" @click="onDelete">
				{{ __("Delete") }}
			</button>
		</template>

		<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Issued") }}
				</div>
				<div class="text-sm font-medium text-ink-900">
					{{ doc.transaction_date ? fmtDate(doc.transaction_date) : "—" }}
				</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Valid to") }}
				</div>
				<div class="text-sm font-medium text-ink-900">
					{{ doc.valid_till ? fmtDate(doc.valid_till) : "—" }}
				</div>
				<div v-if="validityNote" class="text-[10px]"
					:class="daysLeft < 0 ? 'text-warning-700' : 'text-ink-500'">
					{{ validityNote }}
				</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Value") }}
				</div>
				<div class="text-sm font-semibold text-ink-900 tabular-nums">
					{{ fmtCurrency(doc.grand_total, doc.currency) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ __("incl. tax") }}</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Prepared by") }}
				</div>
				<div class="text-sm text-ink-900 truncate">{{ doc.owner || "—" }}</div>
			</div>

			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Project") }}
				</div>
				<RouterLink v-if="doc.project" :to="`/projects/${encodeURIComponent(doc.project)}`"
					class="text-sm text-brand-700 hover:underline">
					{{ doc.project }}
				</RouterLink>
				<div v-else class="text-sm text-ink-400">{{ __("Not linked yet") }}</div>
			</div>
		</div>

		<div class="text-xs text-ink-500 mb-2">{{ lineCount }}</div>

		<div class="border border-ink-200 overflow-hidden" style="border-radius: 8px">
			<div class="overflow-x-auto">
				<table class="w-full text-sm" style="min-width: 760px">
					<thead>
						<tr class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500">
							<th class="text-left font-medium px-3 py-2 w-24">{{ __("Source") }}</th>
							<th class="text-left font-medium px-3 py-2">{{ __("Description") }}</th>
							<th class="text-left font-medium px-3 py-2 w-28">{{ __("Unit") }}</th>
							<th class="text-right font-medium px-3 py-2 w-28">{{ __("Qty") }}</th>
							<th class="text-right font-medium px-3 py-2 w-32">{{ __("Rate") }}</th>
							<th class="text-right font-medium px-3 py-2 w-36">{{ __("Amount") }}</th>
						</tr>
					</thead>

					<tbody>
						<tr v-for="(l, i) in lines" :key="l.name || i" class="border-b border-ink-100">
							<td class="px-3 py-2">
								<StatusBadge :status="l.source" size="xs" />
							</td>
							<td class="px-3 py-2">
								<div class="text-ink-900">{{ l.item_name }}</div>
								<div v-if="l.code || l.source_ref" class="text-[10px] font-mono text-ink-500">
									{{ [l.code, l.source_ref].filter(Boolean).join(" · ") }}
								</div>
							</td>
							<td class="px-3 py-2 text-ink-700">{{ l.uom }}</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ l.qty }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ fmtCurrency(l.rate, doc.currency) }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">
								{{ fmtCurrency(l.amount, doc.currency) }}
							</td>
						</tr>

						<tr v-if="!lines.length">
							<td colspan="6" class="px-3 py-6 text-center text-ink-500 text-xs">
								{{ __("No lines on this quotation.") }}
							</td>
						</tr>
					</tbody>

					<tfoot>
						<tr v-if="lines.length" class="border-t-2 border-ink-200 bg-ink-50">
							<td colspan="5"
								class="px-3 py-2 text-right text-[11px] font-semibold text-ink-600 uppercase tracking-wider">
								{{ __("Net total") }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900">
								{{ fmtCurrency(doc.net_total, doc.currency) }}
							</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
			<div class="lg:col-span-2 border border-ink-200 overflow-hidden" style="border-radius: 8px">
				<header
					class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between">
					<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
						{{ __("Terms & conditions") }}
					</div>
					<span class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600" style="border-radius: 9999px">
						{{ doc.tc_name ? __("Template") : __("Manual") }}
					</span>
				</header>
				<div class="p-4">
					<p v-if="doc.terms" class="text-sm text-ink-700 whitespace-pre-line leading-relaxed">
						{{ doc.terms }}
					</p>
					<p v-else class="text-sm text-ink-400">{{ __("No terms recorded.") }}</p>
				</div>
			</div>

			<div class="border border-ink-200 overflow-hidden self-start" style="border-radius: 8px">
				<header class="px-4 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100">
					<div class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
						{{ __("Pricing") }}
					</div>
				</header>
				<div class="p-4 space-y-2 text-sm">
					<div class="flex justify-between">
						<span class="text-ink-600">{{ __("Net total") }}</span>
						<span class="tabular-nums text-ink-900">
							{{ fmtCurrency(doc.net_total, doc.currency) }}
						</span>
					</div>
					<div v-if="doc.taxes?.length" class="flex justify-between">
						<span class="text-ink-600">{{ __("Tax") }}</span>
						<span class="tabular-nums text-ink-900">
							{{ fmtCurrency(doc.total_taxes_and_charges, doc.currency) }}
						</span>
					</div>
					<div class="flex justify-between border-t border-ink-200 pt-2 font-semibold">
						<span class="text-ink-900">{{ __("Total") }}</span>
						<span class="tabular-nums text-ink-900">
							{{ fmtCurrency(doc.grand_total, doc.currency) }}
						</span>
					</div>
				</div>
			</div>
		</div>
		<div v-if="doc.internal_note" class="mt-4 bg-ink-50 border border-ink-200 px-4 py-3"
			style="border-radius: 8px">
			<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">
				{{ __("Internal note — not printed") }}
			</div>
			<p class="text-sm text-ink-700 whitespace-pre-line">{{ doc.internal_note }}</p>
		</div>
	</DeskPage>

	<DeskPage v-else-if="resource?.doc === null" :title="__('Quotation not found')"
		:breadcrumbs="breadcrumbs">
		<p class="text-sm text-ink-600">
			{{ __("No quotation with that id.") }}
			<RouterLink to="/quotations" class="desk-link">{{ __("Back to the register →") }}</RouterLink>
		</p>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">{{ __("Loading quotation…") }}</div>
</template>
