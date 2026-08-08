<script setup>
// The `members` child table on Crew. Daily rate is never an input — the child
// doctype fetches it from the worker's wage.

import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { fmtINR } from "@/utils/format";

const props = defineProps({
	rows: { type: Array, default: () => [] },
	editable: { type: Boolean, default: false },
});
const emit = defineEmits(["add", "remove"]);

const { workerOptions, workerName, workerDefaults } = useFieldEmployeeOptions();

// Prefill on pick so the rate isn't a dash until save; the server re-applies
// both, and `fetch_if_empty` on the role keeps a hand-edited value.
function onPickWorker(row, id) {
	row.field_employee = id;
	const { trade, wage } = workerDefaults(id);
	row.daily_rate = wage;
	if (!row.role_in_crew) row.role_in_crew = trade;
}

// Exclude workers already picked in the other rows — a worker can't be in the
// same crew twice. The row's own current value stays selectable.
function availableWorkers(row) {
	const taken = new Set(
		props.rows.filter((r) => r !== row && r.field_employee).map((r) => r.field_employee)
	);
	return workerOptions.value.filter((o) => !taken.has(o.value));
}

// A stable identity per row. Saved rows have `name`; unsaved ones get a lazily
// assigned client id. Index keys would make Vue patch the wrong row's inputs in
// place after a delete — the caret and picker state stay behind on the row that
// moved up.
const rowIds = new WeakMap();
let _seq = 0;
function rowKey(row, i) {
	if (row?.name) return row.name;
	if (!row) return i;
	if (!rowIds.has(row)) rowIds.set(row, `new-${++_seq}`);
	return rowIds.get(row);
}
</script>

<template>
	<section class="mt-6">
		<div class="flex items-center justify-between mb-2 gap-3">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
				Members
				<span v-if="!editable && rows.length" class="text-ink-400 font-normal normal-case">
					({{ rows.length }})
				</span>
			</h3>
			<button
				v-if="editable"
				type="button"
				class="text-xs text-brand-700 hover:underline"
				@click="emit('add')"
			>
				+ Add member
			</button>
		</div>

		<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
			<table class="w-full text-xs">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">Worker</th>
						<th class="text-left px-3 py-2">Role</th>
						<th class="text-right px-3 py-2">Daily rate</th>
						<th v-if="editable" class="w-8"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(row, i) in rows"
						:key="rowKey(row, i)"
						class="border-t border-ink-100"
					>
						<td class="px-3 py-2" :style="editable ? 'min-width:220px' : ''">
							<DeskSearchableSelect
								v-if="editable"
								:model-value="row.field_employee"
								:options="availableWorkers(row)"
								placeholder="Pick a worker…"
								search-placeholder="Search workers…"
								@update:model-value="(v) => onPickWorker(row, v)"
							/>
							<span v-else class="text-ink-900 font-medium">
								{{ row.employee_name || workerName(row.field_employee) }}
							</span>
						</td>

						<td class="px-3 py-2" :style="editable ? 'min-width:180px' : ''">
							<DeskLinkPicker
								v-if="editable"
								v-model="row.role_in_crew"
								doctype="Labour Trade"
								label-field="trade"
								:search-fields="['trade', 'name']"
								placeholder="From the worker's trade"
							/>
							<span v-else class="text-ink-600">{{ row.role_in_crew || "—" }}</span>
						</td>

						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ row.daily_rate ? fmtINR(row.daily_rate) : "—" }}
						</td>

						<td v-if="editable" class="px-2 py-2 text-center">
							<button
								type="button"
								class="text-ink-400 hover:text-danger-600"
								@click="emit('remove', i)"
							>
								✕
							</button>
						</td>
					</tr>

					<tr v-if="!rows.length">
						<td
							:colspan="editable ? 4 : 3"
							class="px-3 py-4 text-center text-ink-400 italic"
						>
							{{
								editable
									? "No members yet. Add workers to the crew."
									: "No members."
							}}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>
</template>
