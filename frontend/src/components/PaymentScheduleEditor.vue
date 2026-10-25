<script setup>
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { __ } from "@/utils/translate";

const props = defineProps({
	rows: { type: Array, default: () => [] },
	editable: { type: Boolean, default: false },
	stageOptions: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:rows"]);

const TRIGGERS = [
	{ value: "signing", label: "On signing" },
	{ value: "stage", label: "Stage completes" },
	{ value: "date", label: "On a date" },
	{ value: "running", label: "Running bills" },
];
const total = () => props.rows.reduce((sum, row) => sum + (Number(row.percent) || 0), 0);
const isTotalValid = () => Math.abs(total() - 100) < 0.01;

function setRow(index, patch) {
	emit(
		"update:rows",
		props.rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row))
	);
}

function addRow() {
	emit("update:rows", [
		...props.rows,
		{
			milestone: "",
			percent: Math.max(0, +(100 - total()).toFixed(2)),
			trigger: "stage",
			stage_key: null,
			days_after: null,
			certify: false,
		},
	]);
}

function removeRow(index) {
	emit(
		"update:rows",
		props.rows.filter((_, rowIndex) => rowIndex !== index)
	);
}

function stageLabel(row) {
	if (!row.stage_key) return __("No stage picked");
	return (
		props.stageOptions.find((option) => option.value === row.stage_key)?.label || row.stage_key
	);
}
</script>

<template>
	<div class="border border-ink-200 overflow-x-auto" style="border-radius: 8px">
		<table class="w-full text-sm min-w-[640px]">
			<thead class="bg-ink-50 border-b border-ink-200">
				<tr class="text-[11px] uppercase tracking-wider text-ink-500 text-left">
					<th class="px-3 py-2 font-medium">{{ __("Milestone") }}</th>
					<th class="px-3 py-2 font-medium w-40">{{ __("Payable") }}</th>
					<th class="px-3 py-2 font-medium">{{ __("Stage or timing") }}</th>
					<th class="px-3 py-2 font-medium w-20 text-right">{{ __("Percent") }}</th>
					<th class="px-3 py-2 font-medium w-24 text-center">
						{{ __("Client sign-off") }}
					</th>
					<th v-if="editable" class="w-10"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-if="!rows.length">
					<td :colspan="editable ? 6 : 5" class="px-3 py-4 text-sm text-ink-500">
						{{ __("No milestones yet.") }}
					</td>
				</tr>
				<tr
					v-for="(row, index) in rows"
					:key="row.id || index"
					class="border-b border-ink-100 last:border-0 align-top"
				>
					<td class="px-3 py-2">
						<input
							v-if="editable"
							:value="row.milestone"
							class="desk-input"
							:placeholder="__('e.g. Structure complete')"
							@change="(event) => setRow(index, { milestone: event.target.value })"
						/>
						<span v-else class="text-ink-900">{{ row.milestone }}</span>
					</td>
					<td class="px-3 py-2">
						<select
							v-if="editable"
							:value="row.trigger"
							class="desk-input"
							@change="(event) => setRow(index, { trigger: event.target.value })"
						>
							<option
								v-for="trigger in TRIGGERS"
								:key="trigger.value"
								:value="trigger.value"
							>
								{{ __(trigger.label) }}
							</option>
						</select>
						<span v-else class="text-ink-700">
							{{
								__(
									TRIGGERS.find((trigger) => trigger.value === row.trigger)
										?.label || row.trigger
								)
							}}
						</span>
					</td>
					<td class="px-3 py-2">
						<DeskSearchableSelect
							v-if="editable && row.trigger === 'stage'"
							:model-value="row.stage_key || ''"
							:options="stageOptions"
							allow-clear
							:placeholder="
								stageOptions.length
									? __('Pick a stage…')
									: __('Pick a project category first')
							"
							:search-placeholder="__('Search stages…')"
							@update:model-value="
								(value) => setRow(index, { stage_key: value || null })
							"
						/>
						<div
							v-else-if="editable && row.trigger === 'date'"
							class="flex items-center gap-2"
						>
							<input
								type="number"
								min="0"
								:value="row.days_after ?? ''"
								class="desk-input w-24"
								@change="
									(event) => setRow(index, { days_after: event.target.value })
								"
							/>
							<span class="text-xs text-ink-500 whitespace-nowrap">
								{{ __("days after project starts") }}
							</span>
						</div>
						<span
							v-else
							:class="
								row.trigger === 'stage' && !row.stage_key
									? 'text-warning-700'
									: 'text-ink-700'
							"
						>
							{{
								row.trigger === "stage"
									? stageLabel(row)
									: row.trigger === "date"
									? row.days_after == null
										? __("No date set")
										: __("{0} days after project starts", [row.days_after])
									: row.trigger === "running"
									? __("Billed as running bills on measured work")
									: __("When the contract is signed")
							}}
						</span>
					</td>
					<td class="px-3 py-2 text-right">
						<input
							v-if="editable"
							type="number"
							min="0"
							max="100"
							step="0.5"
							:value="row.percent"
							class="desk-input text-right"
							@change="(event) => setRow(index, { percent: event.target.value })"
						/>
						<span v-else class="tabular-nums text-ink-900">{{ row.percent }}%</span>
					</td>
					<td class="px-3 py-2 text-center">
						<input
							v-if="editable"
							type="checkbox"
							:checked="row.certify"
							class="accent-brand-600"
							:aria-label="
								__('Client sign-off for {0}', [
									row.milestone || __('this milestone'),
								])
							"
							@change="(event) => setRow(index, { certify: event.target.checked })"
						/>
						<span v-else class="text-xs text-ink-600">
							{{ row.certify ? __("Required") : "—" }}
						</span>
					</td>
					<td v-if="editable" class="px-2 py-2 text-center">
						<button
							type="button"
							class="text-ink-400 hover:text-danger-700 text-sm px-1"
							:aria-label="__('Remove {0}', [row.milestone || __('milestone')])"
							@click="removeRow(index)"
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
							v-if="editable"
							type="button"
							class="text-xs text-brand-700 hover:underline"
							@click="addRow"
						>
							{{ __("+ Add milestone") }}
						</button>
					</td>
					<td
						class="px-3 py-2 text-right tabular-nums font-semibold"
						:class="
							!rows.length || isTotalValid() ? 'text-ink-900' : 'text-danger-700'
						"
					>
						{{ +total().toFixed(2) }}%
					</td>
					<td :colspan="editable ? 2 : 1"></td>
				</tr>
			</tfoot>
		</table>
	</div>
</template>
