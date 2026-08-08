<script setup>
// The `custom_project_assigned` child table on Employee. Read-only rows carry
// `project_name` off the doc; editable rows are the form's `{ project }` array.

import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { useProjectOptions } from "@/composables/useProjectOptions";

const props = defineProps({
	rows: { type: Array, default: () => [] },
	editable: { type: Boolean, default: false },
});
const emit = defineEmits(["add", "remove"]);

const { projectOptions, projectLabel } = useProjectOptions();

// Exclude projects already picked in the other rows so a worker can't be
// allocated to the same project twice. The row's own value stays selectable.
function availableProjects(row) {
	const taken = new Set(props.rows.filter((r) => r !== row && r.project).map((r) => r.project));
	return projectOptions.value.filter((o) => !taken.has(o.value));
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
				Allocated projects
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
				+ Add project
			</button>
		</div>

		<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
			<table class="w-full text-xs">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2 w-8">#</th>
						<th class="text-left px-3 py-2">Project</th>
						<th v-if="editable" class="w-8"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(row, i) in rows"
						:key="rowKey(row, i)"
						class="border-t border-ink-100"
					>
						<td class="px-3 py-2 text-ink-500">{{ i + 1 }}</td>
						<td class="px-3 py-2">
							<!-- The panel sizes from the trigger; cap the only unsized
							     column so the dropdown doesn't span the page. -->
							<div v-if="editable" class="max-w-[420px]">
								<DeskSearchableSelect
									v-model="row.project"
									:options="availableProjects(row)"
									placeholder="Pick a project…"
									search-placeholder="Search projects…"
								/>
							</div>
							<DeskLink v-else :to="`/projects/${row.project}`">
								{{ row.project_name || projectLabel(row.project) }}
							</DeskLink>
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
							:colspan="editable ? 3 : 2"
							class="px-3 py-4 text-center text-ink-400 italic"
						>
							{{
								editable
									? "Not allocated to any project yet."
									: "Not allocated to any project."
							}}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<p v-if="editable" class="text-[11px] text-ink-400 mt-1.5">
			Field Attendance can import every worker allocated to a project in one click.
		</p>
	</section>
</template>
