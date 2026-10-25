<script setup>
// Rows of a payment schedule (BuildSuite Payment Milestone), as typed on a
// payment term template — later also on a quotation or tender. Ported from the
// demo's PaymentScheduleEditor. Emits the whole array on every change.
//
// "Stage or timing" depends on Payable: a stage name for "Stage completes",
// a day count for "On a date", fixed text for the other two.

import { computed } from "vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { fmtCurrency } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({
	rows: { type: Array, default: () => [] },
	// Price before tax; null hides the Amount column (a template has no price).
	base: { type: Number, default: null },
	// The offer's currency; unset falls back to the app's display currency.
	currency: { type: String, default: undefined },
});
const emit = defineEmits(["update:rows"]);

// Payable options come from the doctype, so a new one needs no frontend change.
const { selectOptions } = useDoctypeMeta("BuildSuite Payment Milestone");
const payableOptions = computed(() => selectOptions("payable"));

const TIMING_TEXT = {
	"On signing": __("When the contract is signed"),
	"Running bills": __("Billed as running bills on measured work"),
};

const total = computed(() => props.rows.reduce((a, r) => a + (Number(r.percentage) || 0), 0));
const totalOk = computed(() => Math.abs(total.value - 100) < 0.01);
const showAmount = computed(() => props.base != null);

// Shares are rounded to the cent. Rounded shares rarely add back to the price, so
// when the milestones total 100% the last one takes the difference.
const toCents = (v) => Math.round(v * 100) / 100;
const amounts = computed(() => {
	const base = props.base || 0;
	const list = props.rows.map((r) => toCents((base * (Number(r.percentage) || 0)) / 100));
	if (list.length && totalOk.value) {
		const rest = list.slice(0, -1).reduce((a, b) => a + b, 0);
		list[list.length - 1] = toCents(base - rest);
	}
	return list;
});
const amountTotal = computed(() => toCents(amounts.value.reduce((a, b) => a + b, 0)));

function setRow(i, patch) {
	emit(
		"update:rows",
		props.rows.map((r, j) => (j === i ? { ...r, ...patch } : r))
	);
}
function setDays(i, value) {
	setRow(i, { days_after_project_start: value === "" ? null : Number(value) });
}
function addRow() {
	emit("update:rows", [
		...props.rows,
		{
			payment_milestone: "",
			payable: "Stage completes",
			stage: null,
			days_after_project_start: null,
			percentage: Math.max(0, +(100 - total.value).toFixed(2)),
			client_sign_off: 0,
		},
	]);
}
function removeRow(i) {
	emit(
		"update:rows",
		props.rows.filter((_, j) => j !== i)
	);
}
</script>

<template>
	<div class="border border-ink-200 overflow-x-auto" style="border-radius: 8px">
		<table class="w-full text-sm min-w-[720px]">
			<thead class="bg-ink-50 border-b border-ink-200">
				<tr class="text-[11px] uppercase tracking-wider text-ink-500 text-left">
					<th class="px-3 py-2 font-medium">{{ __("Milestone") }}</th>
					<th class="px-3 py-2 font-medium w-48">{{ __("Payable") }}</th>
					<th class="px-3 py-2 font-medium">{{ __("Stage or timing") }}</th>
					<th class="px-3 py-2 font-medium w-20 text-right">%</th>
					<th v-if="showAmount" class="px-3 py-2 font-medium w-32 text-right">
						{{ __("Amount") }}
					</th>
					<th class="px-3 py-2 font-medium w-24 text-center">
						{{ __("Client sign-off") }}
					</th>
					<th class="w-10"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-if="!rows.length">
					<td :colspan="showAmount ? 7 : 6" class="px-3 py-4 text-sm text-ink-500">
						{{ __("No milestones yet.") }}
					</td>
				</tr>
				<tr
					v-for="(r, i) in rows"
					:key="r.name || i"
					class="border-b border-ink-100 last:border-0 align-top"
				>
					<td class="px-3 py-2">
						<input
							:value="r.payment_milestone"
							class="desk-input"
							:placeholder="__('e.g. Structure complete')"
							@change="(e) => setRow(i, { payment_milestone: e.target.value })"
						/>
					</td>
					<td class="px-3 py-2">
						<select
							:value="r.payable"
							class="desk-input"
							@change="(e) => setRow(i, { payable: e.target.value })"
						>
							<option v-for="p in payableOptions" :key="p" :value="p">
								{{ __(p) }}
							</option>
						</select>
					</td>
					<td class="px-3 py-2">
						<input
							v-if="r.payable === 'Stage completes'"
							:value="r.stage"
							class="desk-input"
							:placeholder="__('e.g. Foundation')"
							@change="(e) => setRow(i, { stage: e.target.value || null })"
						/>
						<div v-else-if="r.payable === 'On a date'" class="flex items-center gap-2">
							<input
								type="number"
								min="0"
								:value="r.days_after_project_start ?? ''"
								class="desk-input w-24"
								@change="(e) => setDays(i, e.target.value)"
							/>
							<span class="text-xs text-ink-500 whitespace-nowrap">{{
								__("days after the project starts")
							}}</span>
						</div>
						<span v-else class="text-ink-700">{{ TIMING_TEXT[r.payable] }}</span>
					</td>
					<td class="px-3 py-2 text-right">
						<input
							type="number"
							min="0"
							max="100"
							step="0.5"
							:value="r.percentage"
							class="desk-input text-right"
							@change="(e) => setRow(i, { percentage: Number(e.target.value) || 0 })"
						/>
					</td>
					<td
						v-if="showAmount"
						class="px-3 py-2 text-right tabular-nums text-ink-900 whitespace-nowrap"
					>
						{{ fmtCurrency(amounts[i], currency) }}
					</td>
					<td class="px-3 py-2 text-center">
						<input
							type="checkbox"
							:checked="!!r.client_sign_off"
							class="accent-brand-600"
							:aria-label="__('Client sign-off')"
							@change="
								(e) => setRow(i, { client_sign_off: e.target.checked ? 1 : 0 })
							"
						/>
					</td>
					<td class="px-2 py-2 text-center">
						<button
							type="button"
							class="text-ink-400 hover:text-danger-700 text-sm px-1"
							:aria-label="__('Remove')"
							@click="removeRow(i)"
						>
							✕
						</button>
					</td>
				</tr>
			</tbody>
			<tfoot class="border-t border-ink-200 bg-ink-50">
				<tr>
					<td class="px-3 py-2" colspan="3">
						<button
							type="button"
							class="text-xs text-brand-700 hover:underline"
							@click="addRow"
						>
							{{ __("+ Add milestone") }}
						</button>
					</td>
					<td
						class="px-3 py-2 text-right tabular-nums font-semibold"
						:class="!rows.length || totalOk ? 'text-ink-900' : 'text-danger-700'"
					>
						{{ +total.toFixed(2) }}%
					</td>
					<td
						v-if="showAmount"
						class="px-3 py-2 text-right tabular-nums font-semibold text-ink-900 whitespace-nowrap"
					>
						{{ fmtCurrency(amountTotal, currency) }}
					</td>
					<td colspan="2"></td>
				</tr>
			</tfoot>
		</table>
	</div>
</template>
