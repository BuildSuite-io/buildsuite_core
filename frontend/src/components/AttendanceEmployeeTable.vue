<script setup>
// The `employee_list` child table on Field Attendance. Read-only by default;
// `editable` turns each row into inputs. Emp ID is the Employee docname.

import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";

defineProps({
	rows: { type: Array, default: () => [] },
	editable: { type: Boolean, default: false },
	statuses: { type: Array, default: () => [] },
	error: { type: String, default: "" },
});
const emit = defineEmits(["remove"]);

const { workerOptions, workerName } = useFieldEmployeeOptions();

function onPickEmployee(row, id) {
	row.employee = id;
	row.employee_name = workerName(id);
}

// An Absent worker never carries overtime — the controller rejects it.
function setRowStatus(row, v) {
	row.status = v;
	if (v === "Absent") row.overtime_hours = 0;
}

// Stable per-row identity, held outside the row so nothing synthetic reaches the
// save payload. Index keys would make Vue patch the wrong row's inputs in place
// after a delete — the caret and picker state stay on the row that moved up.
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
	<!-- Edit mode -->
	<section v-if="editable" class="mt-6">
		<div class="flex items-center justify-between mb-2 gap-3">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
				Employee List
			</h3>
			<slot name="actions" />
		</div>
		<p v-if="error" class="text-xs text-danger-700 mb-1">{{ error }}</p>
		<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 820px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-2 py-2 w-8">#</th>
						<th class="text-left px-2 py-2" style="min-width: 200px">Employee</th>
						<th class="text-left px-2 py-2">Emp ID</th>
						<th class="text-left px-2 py-2 w-36">Status</th>
						<th class="text-right px-2 py-2 w-16">OT hrs</th>
						<th class="text-left px-2 py-2">Comments</th>
						<th class="w-8"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(r, i) in rows"
						:key="rowKey(r, i)"
						class="border-t border-ink-100 align-top"
					>
						<td class="px-2 py-1.5 text-ink-500">{{ i + 1 }}</td>
						<td class="px-2 py-1.5">
							<DeskSearchableSelect
								:model-value="r.employee"
								:options="workerOptions"
								placeholder="Pick worker…"
								search-placeholder="Search…"
								@update:model-value="(v) => onPickEmployee(r, v)"
							/>
						</td>
						<td class="px-2 py-1.5 text-ink-500 font-mono text-[11px]">
							{{ r.employee || "—" }}
						</td>
						<td class="px-2 py-1.5">
							<DeskSelect
								:model-value="r.status"
								@update:model-value="(v) => setRowStatus(r, v)"
							>
								<option v-for="s in statuses" :key="s">{{ s }}</option>
							</DeskSelect>
						</td>
						<td class="px-2 py-1.5">
							<input
								v-model.number="r.overtime_hours"
								type="number"
								min="0"
								:disabled="r.status === 'Absent'"
								class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none disabled:text-ink-300 disabled:cursor-not-allowed"
							/>
						</td>
						<td class="px-2 py-1.5">
							<input
								v-model="r.comments"
								class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
								placeholder="—"
							/>
						</td>
						<td class="px-2 py-1.5 text-center">
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
						<td colspan="7" class="px-3 py-6 text-center text-ink-400 italic">
							No employees. Use <span class="font-medium">Bulk Select</span> to load
							a crew or the whole roster.
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</section>

	<!-- View mode -->
	<section v-else class="mb-6 bg-white border border-ink-200 rounded-lg overflow-hidden">
		<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
				Employee List
			</h3>
		</div>
		<table class="w-full text-xs">
			<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
				<tr>
					<th class="text-left px-3 py-2">Employee</th>
					<th class="text-left px-3 py-2">Emp ID</th>
					<th class="text-left px-3 py-2">Status</th>
					<th class="text-right px-3 py-2">OT hrs</th>
					<th class="text-left px-3 py-2">Comments</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(r, i) in rows" :key="rowKey(r, i)" class="border-t border-ink-100">
					<td class="px-3 py-2 text-ink-900 font-medium">
						{{ r.employee_name || workerName(r.employee) }}
					</td>
					<td class="px-3 py-2 text-ink-500 font-mono text-[11px]">{{ r.employee }}</td>
					<td class="px-3 py-2"><StatusBadge :status="r.status" /></td>
					<td class="px-3 py-2 text-right tabular-nums text-ink-700">
						{{ r.overtime_hours || 0 }}
					</td>
					<td class="px-3 py-2 text-ink-500">{{ r.comments || "—" }}</td>
				</tr>
				<tr v-if="!rows.length">
					<td colspan="5" class="px-3 py-6 text-center text-ink-400 italic">
						No employees.
					</td>
				</tr>
			</tbody>
		</table>
	</section>
</template>
